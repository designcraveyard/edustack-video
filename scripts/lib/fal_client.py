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


def _gpt_image_2_size(size: str) -> str:
    """gpt-image-2 accepts WxH or named presets. Map our canonical book sizes
    to presets the model is known to accept; pass other values through verbatim."""
    canonical = {
        "1024x1456": "portrait_4_3",
        "1456x1024": "landscape_4_3",
        "1024x1024": "square_hd",
        "1920x1080": "landscape_16_9",
        "1080x1920": "portrait_16_9",
    }
    return canonical.get(size, size)


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
        """Image-vision LLM call via fal-ai/any-llm/vision (1 image per call).
        Graceful-degrades on failure (returns `_vision_unavailable=True`).
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

    def any_llm_router_video(self, model: str, prompt: str, video_url: str,
                             system_prompt: str | None = None,
                             phase: str = "?", **extra) -> dict:
        """Video-native LLM call via `fal-ai/openrouter/router/video`.

        Sends the whole video URL (not sampled frames) and routes through
        OpenRouter to a model that handles video natively (e.g. Gemini 2.5
        Pro multimodal). Use this in preference to the image-vision
        contact-sheet path for richer temporal continuity QA on clips.

        Graceful-degrades on failure with `_video_vision_unavailable=True`
        so callers can fall back to the still-image contact-sheet path.
        """
        payload: dict = {"model": model, "prompt": prompt,
                         "video_url": video_url, **extra}
        if system_prompt:
            payload["system_prompt"] = system_prompt
        try:
            return self.run("fal-ai/openrouter/router/video", payload, phase=phase)
        except FalError as e:
            if self.logger:
                try:
                    self.logger.log(self.run_id, phase, "warn",
                                    f"video vision unavailable: {str(e)[:200]}")
                except Exception:
                    pass
            return {"_video_vision_unavailable": True, "error": str(e)[:300]}

    # ---------- book mode (Phase B2) ----------
    def gpt_image_2_book_page(
        self,
        *,
        prompt: str,
        image_urls: list[str] | None = None,
        size: str = "1024x1456",
        phase: str = "book-render",
        num_images: int = 1,
    ) -> dict:
        """fal-ai/gpt-image-2 for book pages — requests transparent BG by prompt
        AND by the `background='transparent'` argument when the model supports it.
        Refs are capped at 4 (conservative gpt-image-2 limit). Returns the raw
        fal response; caller extracts {"images":[{"url":...}]}.

        `size` is mapped to the model's accepted preset by `_gpt_image_2_size`.
        """
        refs = [u for u in (image_urls or []) if u][:4]
        payload: dict = {
            "prompt": prompt,
            "image_size": _gpt_image_2_size(size),
            "background": "transparent",
            "num_images": num_images,
            "output_format": "png",
        }
        if refs:
            payload["image_urls"] = refs
        return self.run("fal-ai/gpt-image-2", payload, phase=phase)

    def birefnet_remove_bg(self, *, image_url: str, phase: str = "book-render") -> dict:
        """fal-ai/birefnet/v2 — produce an RGBA cutout from an image with an
        opaque background. Used only when `gpt_image_2_book_page`'s output
        doesn't have a transparent background already."""
        return self.run("fal-ai/birefnet/v2",
                        {"image_url": image_url, "output_format": "png"},
                        phase=phase)

    def upload_file(self, path: str) -> str:
        """Thin wrapper around fal_client.upload_file. Returns a fal-hosted URL."""
        import fal_client  # type: ignore
        return fal_client.upload_file(path)

    def download(self, url: str, dest: str) -> str:
        """Download a fal-hosted artifact (image/video) to disk."""
        import httpx
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
        return dest
