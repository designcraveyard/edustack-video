"""ElevenLabs direct client. Returns MP3 bytes + parses the with_timestamps alignment."""
from __future__ import annotations
import httpx


class ElevenLabsClient:
    def __init__(self, key: str, logger=None, run_id: str = ""):
        self.key = key
        self.logger = logger
        self.run_id = run_id

    def tts_with_timestamps(self, voice_id: str, text: str, model_id: str = "eleven_multilingual_v2") -> dict:
        """Returns {'audio_mp3': bytes, 'alignment': {...}}."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
        r = httpx.post(
            url,
            headers={"xi-api-key": self.key, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": model_id,
                "output_format": "mp3_44100_192",
            },
            timeout=120.0,
        )
        r.raise_for_status()
        data = r.json()
        # ElevenLabs returns base64 audio + alignment
        import base64
        audio = base64.b64decode(data["audio_base64"])
        alignment = data.get("alignment") or data.get("normalized_alignment") or {}
        return {"audio_mp3": audio, "alignment": alignment}

    def validate(self) -> bool:
        r = httpx.get("https://api.elevenlabs.io/v1/user", headers={"xi-api-key": self.key}, timeout=10.0)
        return r.status_code == 200
