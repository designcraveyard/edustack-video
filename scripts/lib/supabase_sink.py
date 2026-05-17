"""Observability sink — writes events to the Edustack Supabase project.

Replaces the previous FastAPI/VPS approach. One table (`eduplugin_events`)
holds all streams (logs, prompts, analyses, gates, heartbeat, chat).
Authentication is the Supabase anon key — public-readable, public-writable
per the table's RLS policies.

When Supabase is unreachable (offline, rate-limited, anon key rotated),
falls back to `<run-dir>/logs/local.jsonl` — pipeline never blocks on the
sink. Same contract as the old VPSLogger so callers don't change.
"""
from __future__ import annotations
from datetime import datetime, UTC
from pathlib import Path
import json
import httpx


DEFAULT_SUPABASE_URL = "https://ulyzimrayfzhbltpxbaj.supabase.co"
DEFAULT_TABLE = "eduplugin_events"


class SupabaseSink:
    def __init__(self, url: str | None, anon_key: str | None, user_id: str,
                 run_dir: Path, table: str = DEFAULT_TABLE,
                 timeout_s: float = 5.0):
        self.url = (url or DEFAULT_SUPABASE_URL).rstrip("/")
        self.anon_key = anon_key
        self.user_id = user_id or "anon"
        self.table = table
        self.timeout_s = timeout_s
        self.local_jsonl = run_dir / "logs" / "local.jsonl"
        self.local_jsonl.parent.mkdir(parents=True, exist_ok=True)
        self._endpoint = f"{self.url}/rest/v1/{self.table}"

    # ---------- writers (same shape as old VPSLogger) ----------
    def log(self, run_id: str, phase: str, level: str, msg: str) -> None:
        self._insert(run_id, "logs", phase, {"level": level, "msg": msg})

    def prompt(self, run_id: str, phase: str, kind: str, endpoint: str, prompt: str,
               response_meta: dict, latency_ms: int, status: str,
               cost_cents: float = 0.0) -> None:
        self._insert(run_id, "prompts", phase, {
            "kind": kind, "endpoint": endpoint, "prompt": prompt[:8000],
            "response_meta": response_meta, "latency_ms": latency_ms,
            "status": status, "cost_cents": cost_cents,
        })

    def analysis(self, run_id: str, target: str, target_id: str,
                 analysis_json: dict) -> None:
        self._insert(run_id, "analyses", target, {
            "target_id": target_id, "analysis_json": analysis_json,
        })

    def gate(self, run_id: str, gate: str, decision: str, item_ref: str,
             comment: str) -> None:
        self._insert(run_id, "gates", gate, {
            "decision": decision, "item_ref": item_ref, "comment": comment,
        })

    def heartbeat(self, run_id: str, phase: str, status: str) -> None:
        self._insert(run_id, "heartbeat", phase, {"status": status})

    def chat(self, run_id: str, session_id: str, delta: list[dict]) -> None:
        self._insert(run_id, "chat", None, {
            "session_id": session_id, "delta": delta,
        })

    # ---------- internal ----------
    def _insert(self, run_id: str, stream: str, phase: str | None,
                payload: dict) -> None:
        row = {
            "ts": datetime.now(UTC).isoformat(),
            "user_id": self.user_id,
            "run_id": run_id,
            "stream": stream,
            "phase": phase,
            "payload": payload,
        }
        # No anon key? Fall back to local-only immediately.
        if not self.anon_key:
            self._fallback(row)
            return
        try:
            r = httpx.post(
                self._endpoint,
                json=row,
                headers={
                    "apikey": self.anon_key,
                    "Authorization": f"Bearer {self.anon_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                timeout=self.timeout_s,
            )
            if not r.is_success:
                self._fallback(row, http_status=r.status_code, body=r.text[:300])
        except Exception as e:  # noqa: BLE001
            self._fallback(row, transport_error=str(e)[:200])

    def _fallback(self, row: dict, **extra) -> None:
        record = {**row, **({"_fallback": extra} if extra else {"_fallback": True})}
        try:
            with self.local_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            pass


# Back-compat alias — old code imports `VPSLogger` and we keep working.
VPSLogger = SupabaseSink
