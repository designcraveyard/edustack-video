"""Thin fal.ai wrapper with retries, prompt logging to VPS, and synchronous
`run` + async-safe `submit` paths. Used by every phase that touches fal.

Design notes
------------
- We use the official `fal_client` SDK. It blocks via subscribe(); long jobs
  (video) are polled by the SDK with its own backoff.
- Every call is logged to VPS `/prompts` with prompt sha + endpoint + latency
  + status. The artifact bytes are NEVER shipped — only metadata.
- Retries are bounded (3 attempts, exponential backoff) for transient errors;
  permanent errors (4xx other than 429) are raised immediately.
"""
from __future__ import annotations
from time import monotonic, sleep
from typing import Any, Callable
import hashlib
import json
import os
import random


class FalError(RuntimeError):
    pass


def _classify(exc: Exception) -> str:
    """Decide if an exception is transient (retry) or permanent (raise)."""
    msg = str(exc).lower()
    if any(s in msg for s in ("timeout", "timed out", "connection", "temporar", "rate limit", "429", "502", "503", "504")):
        return "transient"
    return "permanent"


class FalClient:
    def __init__(self, key: str, logger=None, run_id: str = "",
                 max_retries: int = 3, base_backoff: float = 1.0):
        os.environ["FAL_KEY"] = key
        self.logger = logger
        self.run_id = run_id
        self.max_retries = max_retries
        self.base_backoff = base_backoff

    # ---------- low-level retry harness ----------
    def _with_retries(self, fn: Callable[[], Any], *, phase: str, endpoint: str,
                      prompt: str) -> Any:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            t0 = monotonic()
            try:
                result = fn()
                latency_ms = int((monotonic() - t0) * 1000)
                self._log("ok", phase, endpoint, prompt, result, latency_ms)
                return result
            except Exception as e:  # noqa: BLE001
                latency_ms = int((monotonic() - t0) * 1000)
                kind = _classify(e)
                self._log(kind, phase, endpoint, prompt, {"error": str(e)[:500]}, latency_ms)
                last_exc = e
                if kind == "permanent" or attempt >= self.max_retries:
                    break
                sleep(self.base_backoff * (2 ** (attempt - 1)) + random.random() * 0.25)
        raise FalError(f"{endpoint} failed after {attempt} attempts: {last_exc}") from last_exc

    def _log(self, status: str, phase: str, endpoint: str, prompt: str,
             response_meta: Any, latency_ms: int) -> None:
        if not self.logger:
            return
        prompt_sha = hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()[:16]
        meta = response_meta if isinstance(response_meta, dict) else {"result_type": type(response_meta).__name__}
        # Strip large fields before shipping
        if isinstance(meta, dict):
            meta = {k: (v if not isinstance(v, (bytes, bytearray)) else f"<{len(v)} bytes>")
                    for k, v in meta.items() if k not in ("audio_base64",)}
        try:
            self.logger.prompt(
                run_id=self.run_id, phase=phase, kind="fal",
                endpoint=endpoint,
                prompt=prompt[:4000] + (f"\n[sha={prompt_sha}]" if len(prompt) > 4000 else ""),
                response_meta=meta,
                latency_ms=latency_ms, status=status,
            )
        except Exception:
            pass

    # ---------- public API ----------
    def run(self, endpoint: str, payload: dict, phase: str = "?") -> dict:
        import fal_client  # imported lazily so the module loads without fal-client installed
        prompt = json.dumps(payload, default=str, sort_keys=True)
        return self._with_retries(
            lambda: fal_client.subscribe(endpoint, arguments=payload),
            phase=phase, endpoint=endpoint, prompt=prompt,
        )

    def any_llm(self, model: str, prompt: str, system_prompt: str | None = None,
                phase: str = "?", **extra) -> dict:
        """fal-ai/any-llm uses a flat {prompt, system_prompt, model} schema —
        NOT OpenAI-style messages. For multimodal vision use `any_llm_vision`.
        """
        payload: dict = {"model": model, "prompt": prompt, **extra}
        if system_prompt:
            payload["system_prompt"] = system_prompt
        return self.run("fal-ai/any-llm", payload, phase=phase)

    def any_llm_vision(self, model: str, prompt: str, image_urls: list[str],
                       system_prompt: str | None = None, phase: str = "?", **extra) -> dict:
        """Vision-capable LLM call. Tries fal-ai/any-llm/vision first; if the
        endpoint doesn't exist or fails, returns a degraded result so callers
        can keep moving (vision is quality-improvement, not pipeline-critical).
        """
        payload: dict = {"model": model, "prompt": prompt,
                         "image_urls": image_urls, **extra}
        if system_prompt:
            payload["system_prompt"] = system_prompt
        try:
            return self.run("fal-ai/any-llm/vision", payload, phase=phase)
        except FalError as e:
            if self.logger:
                try:
                    self.logger.log(self.run_id, phase, "warn",
                                    f"vision analysis unavailable: {str(e)[:200]}")
                except Exception:
                    pass
            return {"_vision_unavailable": True, "error": str(e)[:300]}

    def download(self, url: str, dest: str) -> str:
        """Download a fal-hosted artifact (image/video) to disk."""
        import httpx
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
        return dest
