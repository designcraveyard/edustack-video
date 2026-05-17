"""Gemini 2.5 Pro via fal-ai/any-llm. Used for keyframe + clip analysis."""
from __future__ import annotations
from pathlib import Path
import base64
import json


class VisualAnalyzer:
    def __init__(self, fal_client, logger=None, run_id: str = "",
                 model: str = "google/gemini-2.5-pro"):
        self.fal = fal_client
        self.model = model
        self.logger = logger
        self.run_id = run_id

    @staticmethod
    def _img_data_url(p: Path) -> str:
        b = p.read_bytes()
        ext = p.suffix.lower().lstrip(".") or "png"
        return f"data:image/{ext};base64,{base64.b64encode(b).decode()}"

    def analyse_keyframe(self, image_path: Path, prompt_used: str, character_brief: str,
                         schema_hint: str, phase: str = "storyboard") -> dict:
        sys = (
            "You are a continuity supervisor for an educational explainer video. "
            "Reply with STRICT JSON only, matching the schema."
        )
        user = [
            {"type": "text", "text": f"PROMPT USED:\n{prompt_used}\n\n"
                                     f"CHARACTERS:\n{character_brief}\n\n"
                                     f"SCHEMA:\n{schema_hint}"},
            {"type": "image_url", "image_url": {"url": self._img_data_url(image_path)}},
        ]
        out = self.fal.any_llm(self.model, [
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
        ], phase=phase)
        text = out.get("output") if isinstance(out, dict) else str(out)
        try:
            return json.loads(text)
        except Exception:
            return {"raw": text, "parse_error": True}
