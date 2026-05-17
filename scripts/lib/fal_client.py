"""Thin fal.ai wrapper: retries, logs every prompt/response to VPS, returns artifact URL or text."""
from __future__ import annotations
from typing import Any
from time import monotonic
import os


class FalClient:
    def __init__(self, key: str, logger=None, run_id: str = ""):
        os.environ["FAL_KEY"] = key
        self.logger = logger
        self.run_id = run_id

    def run(self, endpoint: str, payload: dict, phase: str = "?") -> Any:
        """Stub. Real implementation will use fal_client.subscribe(endpoint, arguments=payload)."""
        # TODO: import fal_client; result = fal_client.subscribe(endpoint, arguments=payload)
        t0 = monotonic()
        try:
            import fal_client  # type: ignore
            result = fal_client.subscribe(endpoint, arguments=payload)
            status = "ok"
        except Exception as e:
            result = {"error": str(e)}
            status = "error"
        latency_ms = int((monotonic() - t0) * 1000)
        if self.logger:
            self.logger.prompt(
                run_id=self.run_id, phase=phase, kind="fal",
                endpoint=endpoint, prompt=str(payload)[:4000],
                response_meta={"keys": list(result.keys()) if isinstance(result, dict) else None},
                latency_ms=latency_ms, status=status,
            )
        return result

    def any_llm(self, model: str, messages: list[dict], phase: str = "?") -> str:
        return self.run("fal-ai/any-llm", {
            "provider": "openrouter",
            "model": model,
            "messages": messages,
        }, phase=phase)
