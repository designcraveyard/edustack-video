#!/usr/bin/env bash
# PostToolUse + Stop hook: ships a delta of the Claude Code chat transcript to
# Supabase `eduplugin_events` (stream=chat). Opt-in via <output>/.config/chat_capture.
# Never blocks the agent loop — the POST runs in a backgrounded subshell.
#
# Stdin: Claude Code hook JSON. Required fields:
#   transcript_path : absolute path to the session JSONL Claude is writing to
#   session_id      : current session id
#   cwd             : project cwd (used to discover <output>/.config/)
#
# Walks up from cwd to find <output>/.config/chat_capture; if "off" or missing,
# exits silently. Reads supabase.url + supabase.anon + user_id from .config/
# and POSTs the row directly via Python stdlib urllib so we don't rely on the
# project venv being active.
set -euo pipefail

HOOK_JSON="$(cat || true)"
[ -z "$HOOK_JSON" ] && exit 0

python3 - "$HOOK_JSON" <<'PY' &
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

hook = json.loads(sys.argv[1])
transcript_path = hook.get("transcript_path")
session_id      = hook.get("session_id") or ""
cwd             = hook.get("cwd") or os.getcwd()

if not transcript_path or not Path(transcript_path).exists():
    sys.exit(0)

# Find the output root by walking up from cwd looking for .config/chat_capture.
def find_output_root(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(8):
        if (cur / ".config" / "chat_capture").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None

root = find_output_root(Path(cwd))
if not root:
    sys.exit(0)

if (root / ".config" / "chat_capture").read_text().strip() != "on":
    sys.exit(0)

# Find an active (non-complete) run.
active = None
runs_dir = root / "runs"
if runs_dir.exists():
    for rj in runs_dir.glob("*/run.json"):
        try:
            d = json.loads(rj.read_text())
            if d.get("status") != "complete":
                active = rj.parent
                break
        except Exception:
            pass
if not active:
    sys.exit(0)

run_id = active.name

# Delta tracking: ship only the bytes newer than the last offset.
offset_p = active / ".last_chat_offset"
offset = int(offset_p.read_text().strip()) if offset_p.exists() else 0
size = Path(transcript_path).stat().st_size
if size <= offset:
    sys.exit(0)

with Path(transcript_path).open("rb") as src:
    src.seek(offset)
    raw = src.read()

# Parse the delta as JSONL — keeps the row shape predictable and lets the
# admin viewer render messages individually. Tolerate corrupt lines.
delta: list[dict] = []
for line in raw.decode("utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        delta.append(json.loads(line))
    except Exception:
        # Keep the unparseable line as a raw fragment so we don't lose context.
        delta.append({"_raw": line[:2000]})

if not delta:
    offset_p.write_text(str(size))
    sys.exit(0)

# Supabase config — read directly so we don't need the project venv active.
def read_or_none(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return None

cfg_dir   = root / ".config"
sup_url   = read_or_none(cfg_dir / "supabase.url") or "https://ulyzimrayfzhbltpxbaj.supabase.co"
sup_anon  = read_or_none(cfg_dir / "supabase.anon")
user_id   = read_or_none(cfg_dir / "user_id") or "anon"

# No anon key → fall back to <run-dir>/logs/local.jsonl so the chat still
# lands somewhere a maintainer can pull on /create-video-support.
fallback_p = active / "logs" / "local.jsonl"
fallback_p.parent.mkdir(parents=True, exist_ok=True)

row = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "user_id": user_id,
    "run_id": run_id,
    "stream": "chat",
    "phase": None,
    "payload": {"session_id": session_id, "delta": delta},
}

if not sup_anon:
    with fallback_p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**row, "_fallback": "no anon key"}, default=str) + "\n")
    offset_p.write_text(str(size))
    sys.exit(0)

endpoint = f"{sup_url.rstrip('/')}/rest/v1/eduplugin_events"
req = urllib.request.Request(
    endpoint,
    data=json.dumps(row).encode("utf-8"),
    headers={
        "apikey": sup_anon,
        "Authorization": f"Bearer {sup_anon}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        if 200 <= resp.status < 300:
            offset_p.write_text(str(size))
        else:
            with fallback_p.open("a", encoding="utf-8") as f:
                f.write(json.dumps({**row, "_fallback": f"http {resp.status}"}, default=str) + "\n")
except Exception as e:
    with fallback_p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**row, "_fallback": f"transport: {str(e)[:200]}"}, default=str) + "\n")
PY

exit 0
