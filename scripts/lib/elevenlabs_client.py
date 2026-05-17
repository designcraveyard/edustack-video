"""ElevenLabs direct client.

We don't go through fal because we want word-level timestamps from
`/with-timestamps`. That is the canonical input to `vo_timeline.json`,
which drives every later phase's timing.
"""
from __future__ import annotations
from pathlib import Path
import base64
import hashlib
import httpx


class ElevenLabsError(RuntimeError):
    pass


class ElevenLabsClient:
    BASE = "https://api.elevenlabs.io"

    def __init__(self, key: str, logger=None, run_id: str = ""):
        self.key = key
        self.logger = logger
        self.run_id = run_id

    def _headers(self) -> dict:
        return {"xi-api-key": self.key, "accept": "application/json"}

    def validate(self) -> dict | None:
        """GET /v1/user. Cheap. Returns subscription dict or None on failure."""
        try:
            r = httpx.get(f"{self.BASE}/v1/user", headers=self._headers(), timeout=10.0)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def list_voices(self) -> list[dict]:
        r = httpx.get(f"{self.BASE}/v1/voices", headers=self._headers(), timeout=15.0)
        r.raise_for_status()
        return r.json().get("voices", [])

    def tts_with_timestamps(
        self, voice_id: str, text: str,
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_192",
        voice_settings: dict | None = None,
    ) -> dict:
        """POST /v1/text-to-speech/{voice_id}/with-timestamps.

        Returns {'audio_mp3': bytes, 'alignment': {...}, 'normalized_alignment': {...}}.
        Raises ElevenLabsError on non-2xx.
        """
        url = f"{self.BASE}/v1/text-to-speech/{voice_id}/with-timestamps"
        payload: dict = {
            "text": text,
            "model_id": model_id,
            "output_format": output_format,
        }
        if voice_settings:
            payload["voice_settings"] = voice_settings
        prompt_sha = hashlib.sha256(text.encode()).hexdigest()[:16]

        from time import monotonic
        t0 = monotonic()
        try:
            r = httpx.post(
                url,
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
                timeout=180.0,
            )
            latency_ms = int((monotonic() - t0) * 1000)
            status_str = "ok" if r.is_success else f"http_{r.status_code}"
            self._log(prompt_sha, voice_id, model_id, status_str, latency_ms, len(text))
            if not r.is_success:
                raise ElevenLabsError(f"EL {r.status_code}: {r.text[:300]}")
            data = r.json()
        except httpx.HTTPError as e:
            raise ElevenLabsError(f"EL transport error: {e}") from e

        audio_b64 = data.get("audio_base64")
        if not audio_b64:
            raise ElevenLabsError("EL response missing audio_base64")
        return {
            "audio_mp3": base64.b64decode(audio_b64),
            "alignment": data.get("alignment") or {},
            "normalized_alignment": data.get("normalized_alignment") or {},
        }

    def save_audio(self, audio_mp3: bytes, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(audio_mp3)
        return dest

    def _log(self, prompt_sha: str, voice_id: str, model_id: str,
             status: str, latency_ms: int, prompt_chars: int) -> None:
        if not self.logger:
            return
        try:
            self.logger.prompt(
                run_id=self.run_id, phase="vo", kind="elevenlabs",
                endpoint=f"/v1/text-to-speech/{voice_id}/with-timestamps",
                prompt=f"[sha={prompt_sha}] chars={prompt_chars} model={model_id}",
                response_meta={"chars": prompt_chars},
                latency_ms=latency_ms, status=status,
            )
        except Exception:
            pass
