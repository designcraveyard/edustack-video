"""Gemini 2.5 Pro via fal-ai/any-llm/vision. Two entry points:

- `analyse_keyframe(image_path, prompt_used, character_brief)` — for storyboard images
- `analyse_clip(clip_path, prompt_used, character_brief, sample_fps=1)` —
  samples frames via ffmpeg and asks Gemini for a frame-by-frame continuity report

Both gracefully degrade: if the vision endpoint is unreachable or returns
non-JSON, callers get an analysis dict with `regen_recommendation: None` so
the pipeline doesn't block. Quality is auto-improvement, not gating.
"""
from __future__ import annotations
from pathlib import Path
import base64
import json
import re
import subprocess
import tempfile


KEYFRAME_SCHEMA = {
    "beat_id": "int",
    "checks": {
        "characters_present": "list[str]",
        "characters_expected": "list[str]",
        "character_match": "bool",
        "palette_consistent_with_sheet": "bool",
        "background_neutral_unless_required": "bool",
        "action_matches_prompt": "bool",
        "no_text_artifacts": "bool",
        "composition_readable_at_thumbnail": "bool",

        # Anatomy + style-drift QA — same checks the character-sheet phase runs,
        # because a clean sheet can still be re-rendered with bad anatomy in
        # later beats. False-positive approvals are worse than false-negatives.
        "limb_count_correct": "bool — every character has exactly 4 limbs (or 0 for blob/abstract). Flag extras, hybrid quadruped/biped poses.",
        "anatomy_consistent_with_sheet": "bool — proportions, feature counts (eyes, ears, tails), and signature props match the character sheet.",
        "style_consistent_with_brief": "bool — adheres to the requested style; no flat/2D bleed when 3D is asked.",
        "split_screen_orientation_correct": "bool — if the scene is a split-screen, the divider is HORIZONTAL for 9:16 / VERTICAL for 16:9. true when N/A.",
    },
    "issues": "list[{severity: 'warn'|'error', code: str, detail: str}]",
    "regen_recommendation": "null | 'minor' | 'major'",
    "corrective_addendum": "null | str (1 sentence to append to the prompt on retry)",
}

CLIP_SCHEMA = {
    "clip_id": "int",
    "frames_inspected": "int",
    "motion_intensity": "'calm' | 'medium' | 'high'",
    "character_consistency": "'ok' | 'drift_minor' | 'drift_major'",
    "scene_change_ratio": "float 0..1",
    "issues": "list[{severity: 'warn'|'error', code: str, detail: str, t_seconds: float}]",
    "regen_recommendation": "null | 'minor' | 'major'",
    "corrective_addendum": "null | str",
}


# Character sheet QA. Goal: catch limb-count / anatomy / style-drift /
# missing-signature-prop issues BEFORE the user sees Gate 3. The analyser must
# describe AND audit — describing alone produced false-positive approvals.
CHARACTER_SHEET_SCHEMA = {
    "characters": (
        "list[{name: str, species: str, palette: list[str], "
        "signature_features: list[str], pose_count: int}]"
    ),

    "qa_checks": {
        "limb_count_correct": "bool — every character has exactly 4 limbs (or 0 for blob/abstract). Flag extra legs, hybrid quadruped/biped anatomy, or duplicated body parts.",
        "limb_count_detail": "str — describe any limb anomaly per character, e.g. 'Hiru shows 6 legs in the 3/4 view'.",
        "anatomy_consistent_across_poses": "bool — same proportions, same number of features (eyes, ears, tail, etc.) across every pose.",
        "anatomy_inconsistencies": "list[str] — concrete differences, e.g. 'spots present in side view, absent in front view'.",
        "palette_locked": "bool — each character uses the SAME palette across all poses (no shifted hues).",
        "signature_props_present": "bool — every character retains its signature prop / expression across poses (e.g. Hiru's leaf, Sher's fang).",
        "missing_props": "list[str] — props that disappeared in some poses.",
        "style_consistent_with_brief": "bool — adheres to the requested style (e.g. Pixar 3D, 2D Flat, watercolour). No flat/2D bleed when 3D is asked, no photorealism when stylised is asked.",
        "style_drift_detail": "str — describe drift if present.",
        "background_neutral": "bool — neutral white/light background; no environmental clutter that would interfere with later sheet-conditioned generations.",
        "characters_separable": "bool — when multiple characters are on the sheet, they remain visually distinct (no merged silhouettes, no swapped features).",
    },

    "verdict": "'APPROVED' | 'NEEDS_REGEN'",
    "regen_reason": "null | str — one-line summary, only set when verdict=NEEDS_REGEN.",
    "corrective_addendum": "null | str — 1-2 sentences to APPEND to the next prompt to fix the issue. Be concrete: 'Render exactly 4 legs per character. Quadrupeds stand on all fours; bipeds stand on two legs. No hybrid poses.'",
}


# Book-page QA. Four binary checks, all of which must pass. Used by Phase B2
# (scripts/phase_book_render.py) to gate retries.
BOOK_PAGE_SCHEMA = {
    "page_no": "int",
    "checks": {
        "transparent_background": "bool — non-illustration pixels have alpha=0. False if any painted background (sky, paper, color wash).",
        "no_text_in_image": "bool — no letters, numerals, or text artifacts anywhere in the illustration.",
        "character_consistency_vs_refs": "bool — characters match the reference sheets in features, proportions, palette, and signature props.",
        "scene_matches_prompt": "bool — depicted action and setting match the page's scene_prompt.",
    },
    "issues": "list[{severity: 'warn'|'error', code: str, detail: str}]",
    "verdict": "'APPROVED' | 'NEEDS_REGEN'",
    "corrective_addendum": "null | str — 1 sentence to append on retry.",
}


def _img_data_url(p: Path) -> str:
    b = Path(p).read_bytes()
    ext = Path(p).suffix.lower().lstrip(".") or "png"
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{base64.b64encode(b).decode()}"


def _parse_json_lenient(text: str) -> dict:
    s = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
    if m:
        s = m.group(1)
    if not s.startswith("{"):
        a, b = s.find("{"), s.rfind("}")
        if a >= 0 and b > a:
            s = s[a:b + 1]
    return json.loads(s)


def _degraded(target: str, target_id: int, reason: str) -> dict:
    return {
        target: target_id,
        "regen_recommendation": None,
        "_degraded": True,
        "_reason": reason,
    }


class VisualAnalyzer:
    def __init__(self, fal_client, logger=None, run_id: str = "",
                 model: str = "google/gemini-2.5-pro"):
        self.fal = fal_client
        self.model = model
        self.logger = logger
        self.run_id = run_id

    # ---------- character sheets ----------
    def analyse_character_sheet(
        self, image_path: Path, prompt_used: str, character_brief: str,
        style: str, phase: str = "characters",
    ) -> dict:
        """Three-step QA pass — describe → audit → verdict.

        Returns the parsed dict. Callers gate on `verdict == 'NEEDS_REGEN'` and
        thread `corrective_addendum` back into the next generation attempt.
        """
        prompt = (
            f"You are auditing a character reference sheet for a {style or '2D Flat'}-style "
            "educational explainer video. Do NOT just describe — also AUDIT.\n\n"
            f"REQUESTED STYLE: {style}\n\n"
            f"PROMPT USED:\n{prompt_used}\n\n"
            f"CHARACTERS BRIEF:\n{character_brief}\n\n"
            "Run the following 3 steps in order:\n"
            "  Step 1 — DESCRIBE each character (features, palette, poses).\n"
            "  Step 2 — QA CHECK against the schema below. Flag every anomaly:\n"
            "    - limb count (extra legs, hybrid quadruped/biped anatomy)\n"
            "    - asymmetric features across poses (spots disappear, eye shape changes, etc.)\n"
            "    - missing signature props / expressions\n"
            f"    - style drift from the requested style ({style})\n"
            "    - palette drift across poses\n"
            "    - non-neutral background\n"
            "    - layout incompleteness — the rich 16:9 sheet template REQUIRES all of:\n"
            "      title at top-left, LEFT hero pose, CENTER TOP per-character close-up row +\n"
            "      turnaround, RIGHT TOP (only when there are 2 characters), BOTTOM CENTER\n"
            "      color palette, BOTTOM MIDDLE expressions grid, BOTTOM RIGHT detail callouts.\n"
            "      A missing or empty region counts as a regen-worthy defect.\n"
            "  Step 3 — VERDICT: 'APPROVED' if no errors; otherwise 'NEEDS_REGEN' with a "
            "one-line regen_reason and a concrete 1-2 sentence corrective_addendum.\n\n"
            "If you're unsure about a check, set the bool to false and write the doubt "
            "into the corresponding *_detail string — false-positive approvals are worse "
            "than false-negatives here.\n\n"
            f"SCHEMA (return STRICT JSON only, no prose, no fences):\n"
            f"{json.dumps(CHARACTER_SHEET_SCHEMA, indent=2)}"
        )
        system = (
            "You are a character-design QA auditor. STRICT JSON only — start with '{' "
            "and end with '}'. No markdown, no headings."
        )
        try:
            out = self.fal.any_llm_vision(
                self.model, prompt=prompt, system_prompt=system,
                image_urls=[_img_data_url(image_path)], phase=phase,
            )
        except Exception as e:  # noqa: BLE001
            return _degraded("characters", 0, f"vision call raised: {e}")
        if isinstance(out, dict) and out.get("_vision_unavailable"):
            return _degraded("characters", 0, out.get("error", "unavailable"))
        result = self._extract_json(out, default_key="characters", default_id=0)
        # Ensure a verdict field exists so callers can branch safely.
        if "verdict" not in result and not result.get("_degraded"):
            result["verdict"] = "APPROVED"  # missing → assume APPROVED (no QA fields => Gemini didn't flag)
        return result

    # ---------- keyframes ----------
    def analyse_keyframe(self, image_path: Path, prompt_used: str,
                         character_brief: str, beat_id: int,
                         phase: str = "storyboard") -> dict:
        prompt = (
            f"BEAT_ID: {beat_id}\n\n"
            f"PROMPT USED:\n{prompt_used}\n\n"
            f"CHARACTERS:\n{character_brief}\n\n"
            f"INSPECT THE ATTACHED IMAGE.\n"
            f"Return STRICT JSON only — no prose, no markdown fences — matching this schema:\n"
            f"{json.dumps(KEYFRAME_SCHEMA, indent=2)}"
        )
        system = (
            "You are a continuity supervisor for an educational explainer video. "
            "Output MUST be a single valid JSON object — no headings, no markdown, "
            "no prose, no code fences. Start with '{' and end with '}'."
        )
        try:
            out = self.fal.any_llm_vision(
                self.model, prompt=prompt, system_prompt=system,
                image_urls=[_img_data_url(image_path)], phase=phase,
            )
        except Exception as e:  # noqa: BLE001
            return _degraded("beat_id", beat_id, f"vision call raised: {e}")
        if isinstance(out, dict) and out.get("_vision_unavailable"):
            return _degraded("beat_id", beat_id, out.get("error", "unavailable"))
        return self._extract_json(out, default_key="beat_id", default_id=beat_id)

    # ---------- book pages ----------
    def analyse_book_page(
        self, image_path: Path, prompt_used: str, character_brief: str,
        page_no: int, scene_prompt: str, phase: str = "book-render",
    ) -> dict:
        """Four binary checks: transparent BG, no text, character consistency,
        scene match. All four must pass; otherwise verdict=NEEDS_REGEN with a
        corrective_addendum to thread into the next gpt-image-2 attempt."""
        prompt = (
            f"PAGE_NO: {page_no}\n\n"
            f"PROMPT USED:\n{prompt_used}\n\n"
            f"SCENE PROMPT:\n{scene_prompt}\n\n"
            f"CHARACTERS:\n{character_brief}\n\n"
            "INSPECT THE ATTACHED IMAGE. This is a book page intended to be sized "
            "to A4 Portrait or A3 Landscape with a TRANSPARENT BACKGROUND, no text "
            "burnt in. Audit four binary checks, ALL of which must pass.\n\n"
            "If you see ANY painted background (sky, paper texture, color wash), set "
            "transparent_background=false. If you see ANY letters or numerals, set "
            "no_text_in_image=false.\n\n"
            f"Return STRICT JSON only matching this schema:\n{json.dumps(BOOK_PAGE_SCHEMA, indent=2)}"
        )
        system = (
            "You are an illustration QA auditor for a children's book. STRICT JSON only — "
            "start with '{' and end with '}'. No prose, no markdown."
        )
        try:
            out = self.fal.any_llm_vision(
                self.model, prompt=prompt, system_prompt=system,
                image_urls=[_img_data_url(image_path)], phase=phase,
            )
        except Exception as e:  # noqa: BLE001
            return _degraded("page_no", page_no, f"vision call raised: {e}")
        if isinstance(out, dict) and out.get("_vision_unavailable"):
            return _degraded("page_no", page_no, out.get("error", "unavailable"))
        result = self._extract_json(out, default_key="page_no", default_id=page_no)
        if "verdict" not in result and not result.get("_degraded"):
            result["verdict"] = "APPROVED"
        return result

    # ---------- clips ----------
    def sample_frames(self, clip_path: Path, out_dir: Path,
                      fps: float = 1.0, max_frames: int = 12) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        pattern = str(out_dir / "f_%03d.jpg")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(clip_path),
            "-vf", f"fps={fps}",
            "-frames:v", str(max_frames),
            "-q:v", "4", pattern,
        ]
        subprocess.run(cmd, check=True)
        return sorted(out_dir.glob("f_*.jpg"))

    def _contact_sheet(self, frames: list[Path], out_path: Path,
                       cols: int = 4) -> Path:
        """Compose frames into a single contact-sheet image so we stay within
        the vision endpoint's 1-image-per-call limit."""
        from PIL import Image
        if not frames:
            raise ValueError("contact_sheet: empty frames list")
        thumbs = [Image.open(f).convert("RGB") for f in frames]
        # Resize each to a reasonable thumbnail (max 480 wide)
        tw = 480
        sized = []
        for t in thumbs:
            ratio = tw / t.width
            sized.append(t.resize((tw, int(t.height * ratio))))
        cols = max(1, min(cols, len(sized)))
        rows = (len(sized) + cols - 1) // cols
        cell_w = max(s.width for s in sized)
        cell_h = max(s.height for s in sized)
        canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), (240, 240, 240))
        for i, im in enumerate(sized):
            r, c = divmod(i, cols)
            canvas.paste(im, (c * cell_w, r * cell_h))
        canvas.save(out_path, "JPEG", quality=82)
        return out_path

    def _default_clip_prompt(self, clip_id: int, prompt_used: str,
                             character_brief: str) -> str:
        """Fallback template when Claude has NOT pre-authored a validation
        prompt for this clip. Generic; the Claude-authored variant should
        be a frame-by-frame articulation of the intended action and
        explicit per-tick checks. See clip-validation-prompts.md."""
        return (
            f"CLIP_ID: {clip_id}\n\n"
            f"PROMPT USED FOR GENERATION:\n{prompt_used}\n\n"
            f"CHARACTERS:\n{character_brief}\n\n"
            "Watch the attached video end-to-end. Frame by frame, articulate "
            "what actually happens, then audit it for continuity.\n"
            "Flag every issue you spot:\n"
            "  - limb count anomalies (extra legs, hybrid quadruped/biped poses)\n"
            "  - character drift (palette shift, feature changes, identity swaps)\n"
            "  - style drift (flat/2D bleed when 3D is asked, photorealism when stylised)\n"
            "  - jarring scene changes mid-clip\n"
            "  - missing signature props that were present at clip start\n"
            "  - text/caption/logo artifacts the prompt forbade\n\n"
            "Return STRICT JSON only matching:\n"
            f"{json.dumps(CLIP_SCHEMA, indent=2)}"
        )

    def analyse_clip(self, clip_path: Path, prompt_used: str,
                     character_brief: str, clip_id: int,
                     fps: float = 1.0, max_frames: int = 8,
                     validation_prompt: str | None = None) -> dict:
        """Video-native QA via fal-ai/openrouter/router/video.

        - `validation_prompt`, when supplied, is used verbatim. This is the
          Claude-authored, per-clip frame-by-frame articulation produced by
          the clip-generator skill (the recommended path).
        - When `validation_prompt` is None, a generic fallback template runs.
          Quality is lower because the auditor doesn't know the per-beat
          intent at the tick level — useful only when the orchestrator
          couldn't author one.

        Uploads the clip to fal once (so the router can stream the actual
        video, not sampled frames), then asks Gemini 2.5 Pro to audit. Falls
        back to a still-image contact-sheet path on any router failure so
        the pipeline never blocks on QA.
        """
        prompt = (validation_prompt or "").strip() or self._default_clip_prompt(
            clip_id, prompt_used, character_brief,
        )
        if validation_prompt and "STRICT JSON" not in prompt and "schema" not in prompt.lower():
            # Claude wrote the body — make sure the strict-JSON tail is present.
            prompt = prompt.rstrip() + "\n\nReturn STRICT JSON only matching:\n" + json.dumps(CLIP_SCHEMA, indent=2)
        system = (
            "You audit short animated video clips for continuity. "
            "Output MUST be a single valid JSON object — no headings, no markdown, "
            "no prose, no code fences. Start with '{' and end with '}'."
        )

        # Primary path: upload + router/video
        try:
            video_url = self.fal.upload_file(str(clip_path))
        except Exception as e:  # noqa: BLE001
            return self._analyse_clip_via_contact_sheet(
                clip_path, prompt, system, clip_id, fps, max_frames,
                fallback_reason=f"upload failed: {e}",
            )

        try:
            out = self.fal.any_llm_router_video(
                self.model, prompt=prompt, system_prompt=system,
                video_url=video_url, phase="clips",
            )
        except Exception as e:  # noqa: BLE001
            return self._analyse_clip_via_contact_sheet(
                clip_path, prompt, system, clip_id, fps, max_frames,
                fallback_reason=f"router/video raised: {e}",
            )

        if isinstance(out, dict) and out.get("_video_vision_unavailable"):
            return self._analyse_clip_via_contact_sheet(
                clip_path, prompt, system, clip_id, fps, max_frames,
                fallback_reason=out.get("error", "router_video_unavailable"),
            )

        parsed = self._extract_json(out, default_key="clip_id", default_id=clip_id)
        parsed.setdefault("_analyser", "fal-ai/openrouter/router/video")
        return parsed

    def _analyse_clip_via_contact_sheet(
        self, clip_path: Path, prompt: str, system: str,
        clip_id: int, fps: float, max_frames: int,
        fallback_reason: str,
    ) -> dict:
        """Fallback used only when the router/video path errors. Samples
        ffmpeg frames into a single contact-sheet image (still picture) and
        calls any-llm/vision. Quality is lower but the pipeline keeps moving.
        """
        with tempfile.TemporaryDirectory() as td:
            try:
                frames = self.sample_frames(clip_path, Path(td), fps=fps, max_frames=max_frames)
            except Exception as e:  # noqa: BLE001
                return _degraded("clip_id", clip_id,
                                 f"ffmpeg sample failed (after {fallback_reason}): {e}")
            if not frames:
                return _degraded("clip_id", clip_id,
                                 f"no_frames_sampled (after {fallback_reason})")
            sheet = self._contact_sheet(frames, Path(td) / "sheet.jpg")
            extended_prompt = (
                f"{prompt}\n\nNOTE: the attached image is a CONTACT SHEET "
                f"({len(frames)} frames sampled at {fps} fps, top-to-bottom, "
                f"left-to-right) because the router/video path was unavailable."
            )
            try:
                out = self.fal.any_llm_vision(
                    self.model, prompt=extended_prompt, system_prompt=system,
                    image_urls=[_img_data_url(sheet)], phase="clips",
                )
            except Exception as e:  # noqa: BLE001
                return _degraded("clip_id", clip_id,
                                 f"contact-sheet vision raised: {e}")
        if isinstance(out, dict) and out.get("_vision_unavailable"):
            return _degraded("clip_id", clip_id,
                             out.get("error", "vision_unavailable"))
        parsed = self._extract_json(out, default_key="clip_id", default_id=clip_id)
        parsed["_analyser"] = "fal-ai/any-llm/vision (contact-sheet fallback)"
        parsed["_fallback_reason"] = fallback_reason
        return parsed

    # ---------- internal ----------
    def _extract_json(self, fal_output: dict, default_key: str, default_id: int) -> dict:
        text = ""
        if isinstance(fal_output, dict):
            text = fal_output.get("output") or fal_output.get("text") or ""
            if not text and isinstance(fal_output.get("choices"), list):
                ch = fal_output["choices"][0]
                text = ((ch.get("message") or {}).get("content")) or ""
        try:
            return _parse_json_lenient(text)
        except Exception:
            return {default_key: default_id, "raw": text[:500], "parse_error": True,
                    "regen_recommendation": None}
