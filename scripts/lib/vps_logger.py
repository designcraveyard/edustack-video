"""Best-effort observability sink. Falls back to local JSONL when VPS is unreachable."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, UTC
import json
import httpx


class VPSLogger:
    def __init__(self, vps_url: str | None, token: str | None, run_dir: Path):
        self.url = vps_url.rstrip("/") if vps_url else None
        self.token = token
        self.local_jsonl = run_dir / "logs" / "local.jsonl"
        self.local_jsonl.parent.mkdir(parents=True, exist_ok=True)

    def _post(self, path: str, payload: dict) -> None:
        payload.setdefault("ts", datetime.now(UTC).isoformat())
        line = json.dumps({"path": path, **payload}, default=str)
        if not self.url or not self.token:
            with self.local_jsonl.open("a") as f:
                f.write(line + "\n")
            return
        try:
            httpx.post(
                f"{self.url}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5.0,
            )
        except Exception:
            with self.local_jsonl.open("a") as f:
                f.write(line + "\n")

    def log(self, run_id: str, phase: str, level: str, msg: str) -> None:
        self._post("/logs", {"run_id": run_id, "phase": phase, "level": level, "msg": msg})

    def prompt(self, run_id: str, phase: str, kind: str, endpoint: str, prompt: str,
               response_meta: dict, latency_ms: int, status: str, cost_cents: float = 0.0) -> None:
        self._post("/prompts", {
            "run_id": run_id, "phase": phase, "kind": kind, "endpoint": endpoint,
            "prompt": prompt, "response_meta": response_meta,
            "latency_ms": latency_ms, "status": status, "cost_cents": cost_cents,
        })

    def analysis(self, run_id: str, target: str, target_id: str, analysis_json: dict) -> None:
        self._post("/analyses", {"run_id": run_id, "target": target,
                                 "target_id": target_id, "analysis_json": analysis_json})

    def gate(self, run_id: str, gate: str, decision: str, item_ref: str, comment: str) -> None:
        self._post("/gates", {"run_id": run_id, "gate": gate, "decision": decision,
                              "item_ref": item_ref, "comment": comment})

    def heartbeat(self, run_id: str, phase: str, status: str) -> None:
        self._post("/heartbeat", {"run_id": run_id, "phase": phase, "status": status})
