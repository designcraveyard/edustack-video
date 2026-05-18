"""Observability self-test — invoked by /test-logs.

Verifies the entire telemetry pipeline is wired correctly after install:

  1. Emits ONE synthetic event per stream via `SupabaseSink`:
       logs, prompts, analyses, gates, heartbeat, chat
     Then SELECTs each back to prove the row actually landed (a successful
     POST is not enough — RLS or schema drift can silently swallow rows).
  2. End-to-end test of `hooks/ship-chat.sh` — creates a synthetic active
     run + transcript, pipes Claude-Code-shaped hook JSON into the script,
     waits, then SELECTs the resulting `stream=chat` row from Supabase.

Outputs a per-stream PASS/FAIL table with HTTP details. Cleans up the
synthetic test run dir on exit (the synthetic Supabase rows stay — they're
namespaced by `user_id` + `run_id` and discoverable in the admin viewer).

Run:
    uv run python -m scripts.test_logs --output <output-root>

Exit codes:
    0 = all checks passed
    1 = at least one check failed (details printed)
    2 = setup precondition missing (no .config/ — run /create-video-setup)
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from scripts.lib.config import load as load_config
from scripts.lib.supabase_sink import SupabaseSink, DEFAULT_TABLE


# ── Helpers ────────────────────────────────────────────────────────────────

class C:
    """ANSI colours — tolerable on most terminals, harmless on dumb ones."""
    G = "\033[32m"  # green
    R = "\033[31m"  # red
    Y = "\033[33m"  # yellow
    B = "\033[34m"  # blue
    DIM = "\033[2m"
    BOLD = "\033[1m"
    END = "\033[0m"


def pass_(label: str, detail: str = "") -> None:
    print(f"  {C.G}✓{C.END} {label:<32} {C.DIM}{detail}{C.END}")


def fail_(label: str, detail: str = "") -> None:
    print(f"  {C.R}✗{C.END} {label:<32} {C.R}{detail}{C.END}")


def info_(label: str, detail: str = "") -> None:
    print(f"  {C.B}•{C.END} {label:<32} {C.DIM}{detail}{C.END}")


def section(title: str) -> None:
    print()
    print(f"{C.BOLD}{title}{C.END}")


def select_rows(url: str, anon: str, table: str, *, user_id: str, run_id: str,
                stream: str | None = None, limit: int = 5,
                timeout_s: float = 6.0) -> tuple[int, list[dict] | str]:
    """SELECT eduplugin_events filtered by user_id + run_id (+ optional stream).
    Returns (http_status, rows or error_body)."""
    params = {
        "user_id": f"eq.{user_id}",
        "run_id": f"eq.{run_id}",
        "select": "id,ts,stream,phase,payload",
        "order": "ts.desc",
        "limit": str(limit),
    }
    if stream:
        params["stream"] = f"eq.{stream}"
    endpoint = f"{url.rstrip('/')}/rest/v1/{table}"
    try:
        r = httpx.get(endpoint, params=params, headers={
            "apikey": anon,
            "Authorization": f"Bearer {anon}",
            "Accept": "application/json",
        }, timeout=timeout_s)
    except Exception as e:
        return -1, f"transport error: {e}"
    if not r.is_success:
        return r.status_code, r.text[:400]
    return r.status_code, r.json()


# ── Stream tests ───────────────────────────────────────────────────────────

# Each entry: stream → (callable that fires the synthetic write, dict shape we
# expect to find in payload). All payloads include a "test_marker" so the
# admin viewer can filter them out of real-run analytics.
def stream_writers(sink: SupabaseSink, run_id: str) -> list[tuple[str, callable, dict]]:
    marker = {"test_marker": True, "source": "scripts/test_logs.py"}

    def write_logs():
        sink.log(run_id, "test", "info", "self-test: logs stream")

    def write_prompts():
        sink.prompt(
            run_id, phase="test", kind="fal",
            endpoint="fal-ai/test-endpoint",
            prompt="self-test prompt body (would be a real fal.ai call body in production)",
            response_meta={"status": "ok", "size": 1024, **marker},
            latency_ms=42, status="ok", cost_cents=0.0,
        )

    def write_analyses():
        sink.analysis(
            run_id, target="keyframe", target_id="beat_test",
            analysis_json={"verdict": "APPROVED", "score": 0.95, **marker},
        )

    def write_gates():
        sink.gate(run_id, gate="test_gate", decision="approve",
                  item_ref="self-test:item", comment="self-test gate comment")

    def write_heartbeat():
        sink.heartbeat(run_id, phase="test", status="started")

    def write_chat():
        # Synthetic chat delta — same shape the real hook emits.
        sink.chat(run_id, session_id="self-test-session", delta=[
            {"role": "user", "content": "self-test user line", **marker},
            {"role": "assistant", "content": "self-test assistant line", **marker},
        ])

    return [
        ("logs",      write_logs,      {"level": "info"}),
        ("prompts",   write_prompts,   {"kind": "fal", "endpoint": "fal-ai/test-endpoint"}),
        ("analyses",  write_analyses,  {"target_id": "beat_test"}),
        ("gates",     write_gates,     {"decision": "approve"}),
        ("heartbeat", write_heartbeat, {"status": "started"}),
        ("chat",      write_chat,      {"session_id": "self-test-session"}),
    ]


def run_stream_tests(cfg, sink: SupabaseSink, run_id: str,
                     verify_delay_s: float = 1.5) -> int:
    section("1. Per-stream write + read-back (6 streams)")
    failed = 0

    # Write all six streams in sequence (sink is sync; each waits for HTTP).
    writers = stream_writers(sink, run_id)
    for stream, write_fn, _expected_keys in writers:
        try:
            write_fn()
            info_(f"emit {stream}", "POST sent")
        except Exception as e:
            fail_(f"emit {stream}", f"writer raised: {e}")
            failed += 1

    # Give PostgREST replication a moment — Supabase is usually instant but
    # we've seen 100–500 ms lag during cold path-of-least-resistance writes.
    time.sleep(verify_delay_s)

    # Read each stream back.
    for stream, _, expected_keys in writers:
        status, body = select_rows(
            cfg.supabase_url, cfg.supabase_anon, DEFAULT_TABLE,
            user_id=cfg.user_id, run_id=run_id, stream=stream, limit=1,
        )
        if status != 200:
            fail_(f"verify {stream}", f"GET {status} — {body!r}")
            failed += 1
            continue
        rows = body if isinstance(body, list) else []
        if not rows:
            # Check the local fallback so we can tell the user where it went.
            fallback = _peek_fallback(sink.local_jsonl, stream)
            detail = f"no row (fallback: {fallback})" if fallback else "no row + no fallback (lost)"
            fail_(f"verify {stream}", detail)
            failed += 1
            continue
        row = rows[0]
        # Light shape check.
        payload = row.get("payload") or {}
        missing = [k for k in expected_keys if k not in payload]
        if missing:
            fail_(f"verify {stream}", f"row missing payload keys: {missing}")
            failed += 1
            continue
        pass_(f"verify {stream}", f"id={row.get('id')[:8]}… ts={row.get('ts')}")

    return failed


def _peek_fallback(local_jsonl: Path, stream: str) -> str | None:
    """Look at <run-dir>/logs/local.jsonl and report whether the test event
    fell back there — so the user knows where to look if Supabase rejected it.
    """
    try:
        if not local_jsonl.is_file():
            return None
        for line in reversed(local_jsonl.read_text(encoding="utf-8").splitlines()):
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("stream") == stream:
                return f"{local_jsonl}#{d.get('ts', '?')}"
    except Exception:
        pass
    return None


# ── Hook end-to-end test ───────────────────────────────────────────────────

def find_hook_script() -> Path | None:
    """Locate `hooks/ship-chat.sh` next to this script (in the plugin tree)."""
    here = Path(__file__).resolve().parent.parent  # scripts/.. = plugin root
    p = here / "hooks" / "ship-chat.sh"
    return p if p.is_file() else None


def run_hook_test(cfg, sink: SupabaseSink, verify_delay_s: float = 2.0) -> int:
    section("2. Hook end-to-end (synthetic transcript → ship-chat.sh → Supabase)")

    hook = find_hook_script()
    if not hook:
        fail_("hook script located", f"not found at hooks/ship-chat.sh")
        return 1
    if not os.access(hook, os.X_OK):
        fail_("hook script executable", f"{hook} is not executable (chmod +x)")
        return 1
    pass_("hook script located", str(hook))

    # The hook walks up from cwd looking for .config/chat_capture. We point
    # it at the user's real output root (so config + Supabase creds are real)
    # but create a SYNTHETIC active run dir under tmp/runs to avoid touching
    # any real run.
    output_root = cfg.output_root
    chat_cap = output_root / ".config" / "chat_capture"
    original_chat_capture = chat_cap.read_text(encoding="utf-8").strip() if chat_cap.is_file() else "off"
    chat_cap_restored = False

    # Synthetic run id is unique so we can SELECT it back unambiguously.
    test_id = f"test-logs-hook-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    runs_dir = output_root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    fake_run = runs_dir / test_id
    fake_run.mkdir(parents=True, exist_ok=True)
    (fake_run / "logs").mkdir(exist_ok=True)
    (fake_run / "run.json").write_text(json.dumps({
        "run_id": test_id, "status": "running", "phase": "test",
    }))

    # Synthetic transcript JSONL — one user line + one assistant line.
    transcript = fake_run / ".test_transcript.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"content": "hook-test user line"}}) + "\n" +
        json.dumps({"type": "assistant", "message": {"content": "hook-test assistant line"}}) + "\n"
    )

    cleanup_paths = [fake_run]

    try:
        # Force chat_capture on for the duration of this test.
        if original_chat_capture != "on":
            chat_cap.write_text("on")
            chat_cap_restored = True
            info_("chat_capture", f"forced on (was '{original_chat_capture}'); will restore")
        else:
            info_("chat_capture", "already on")

        # Build the stdin JSON Claude Code passes to hooks.
        hook_stdin = json.dumps({
            "transcript_path": str(transcript),
            "session_id": f"self-test-{test_id}",
            "cwd": str(output_root),
            "hook_event_name": "PostToolUse",
        })

        # Invoke the hook. It backgrounds its Python work, so the bash script
        # itself returns near-instantly. We then poll Supabase.
        proc = subprocess.run(
            ["bash", str(hook)],
            input=hook_stdin,
            capture_output=True,
            text=True,
            timeout=12,
            cwd=str(output_root),
        )
        if proc.returncode != 0:
            fail_("hook returned cleanly", f"rc={proc.returncode} stderr={proc.stderr[:300]}")
            return 1
        pass_("hook returned cleanly", "rc=0")

        # The hook backgrounds the Supabase POST. Give it a beat.
        info_("waiting for Supabase write", f"{verify_delay_s}s")
        time.sleep(verify_delay_s)

        status, body = select_rows(
            cfg.supabase_url, cfg.supabase_anon, DEFAULT_TABLE,
            user_id=cfg.user_id, run_id=test_id, stream="chat", limit=1,
        )
        if status != 200:
            fail_("hook → Supabase row", f"GET {status} — {body!r}")
            return 1
        rows = body if isinstance(body, list) else []
        if not rows:
            # Maybe the hook fell back to local JSONL — surface that path.
            local_jsonl = fake_run / "logs" / "local.jsonl"
            detail = ("hook ran but no row appeared; local fallback at "
                      + str(local_jsonl)) if local_jsonl.exists() else "no row, no fallback"
            fail_("hook → Supabase row", detail)
            return 1
        pass_("hook → Supabase row", f"id={rows[0].get('id')[:8]}…")
        return 0
    finally:
        if chat_cap_restored:
            chat_cap.write_text(original_chat_capture)
            info_("chat_capture restored", f"= '{original_chat_capture}'")
        for p in cleanup_paths:
            shutil.rmtree(p, ignore_errors=True)
            info_("cleanup", str(p))


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        prog="test-logs",
        description="Verify Supabase observability is wired correctly.",
    )
    ap.add_argument("--output", help="Output root (defaults to $EDUSTACK_VIDEO_OUTPUT or $PWD)")
    ap.add_argument("--keep-rows", action="store_true",
                    help="Don't print the cleanup hint; useful for CI.")
    ap.add_argument("--verify-delay", type=float, default=1.5,
                    help="Seconds to wait between POST and SELECT (default 1.5)")
    args = ap.parse_args()

    try:
        cfg = load_config(args.output)
    except SystemExit as e:
        print(f"{C.R}✗{C.END} {e}", file=sys.stderr)
        return 2

    print(f"{C.BOLD}edustack-video — observability self-test{C.END}\n")

    # Preamble: config snapshot.
    section("Config")
    info_("output root", str(cfg.output_root))
    info_("user_id", cfg.user_id)
    info_("supabase url", cfg.supabase_url)
    if cfg.supabase_anon:
        info_("supabase anon", f"{cfg.supabase_anon[:20]}… ({len(cfg.supabase_anon)} chars)")
    else:
        fail_("supabase anon", "MISSING — events will only land in local.jsonl. Run /create-video-setup.")
        return 1
    info_("chat_capture", "on" if cfg.chat_capture else "off")

    run_id = f"test-logs-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    print(f"  {C.B}•{C.END} {'test run id':<32} {C.DIM}{run_id}{C.END}")

    # SupabaseSink writes go to a tmp run-dir so local-fallback JSONL (if any)
    # lands in a place we can inspect & clean up without touching real runs.
    tmp_run_dir = Path(tempfile.mkdtemp(prefix=f"test-logs-{run_id}-"))
    sink = SupabaseSink(
        url=cfg.supabase_url, anon_key=cfg.supabase_anon,
        user_id=cfg.user_id, run_dir=tmp_run_dir,
    )

    try:
        fails = 0
        fails += run_stream_tests(cfg, sink, run_id, verify_delay_s=args.verify_delay)
        fails += run_hook_test(cfg, sink, verify_delay_s=args.verify_delay + 0.5)

        section("Summary")
        if fails == 0:
            print(f"  {C.G}{C.BOLD}All checks passed.{C.END}")
            print(f"\n  View this run's rows:")
            print(f"    {C.DIM}https://supabase.com/dashboard/project/ulyzimrayfzhbltpxbaj/editor — filter user_id={cfg.user_id} run_id={run_id}{C.END}")
            print(f"\n  Or via the EduStack admin viewer (when deployed):")
            print(f"    {C.DIM}<edustack-web>/admin/eduplugin/runs/{run_id}{C.END}")
            if not args.keep_rows:
                print(f"\n  {C.DIM}(Synthetic rows stay in Supabase — filter by test_marker=true to exclude from analytics.){C.END}")
            return 0
        else:
            print(f"  {C.R}{C.BOLD}{fails} check(s) failed.{C.END} See details above.")
            print(f"\n  Common causes:")
            print(f"    • supabase.anon key invalid or rotated → re-run /create-video-setup")
            print(f"    • Row Level Security blocked the insert/select → check Supabase project settings")
            print(f"    • Table `eduplugin_events` schema drift → verify columns: id,ts,user_id,run_id,stream,phase,payload")
            print(f"    • Local fallback JSONL written: {tmp_run_dir}/logs/local.jsonl")
            return 1
    finally:
        # Tmp run dir cleanup (local fallback JSONL might have content if Supabase failed —
        # we leave the dir for inspection on failure, remove it on success).
        try:
            jsonl = tmp_run_dir / "logs" / "local.jsonl"
            if jsonl.exists() and jsonl.stat().st_size > 0:
                # Leave the dir; user may want to inspect.
                print(f"\n  {C.DIM}Local fallback events recorded at {jsonl}{C.END}")
            else:
                shutil.rmtree(tmp_run_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
