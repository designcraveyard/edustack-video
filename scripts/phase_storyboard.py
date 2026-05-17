"""Phase 3b — Storyboard / keyframes.

Two image_modes:
  - storyboard_panel : single gpt-image-2 multi-panel sheet, sliced via PIL.
  - per_keyframe     : one Nano Banana 2 image per beat, character-sheet
                       conditioned (or description-block conditioned in
                       character_mode=none).

After every keyframe we ask Gemini 2.5 Pro for a continuity report. Up to 2
auto-corrective regens before escalating to Gate 3.
"""
from __future__ import annotations
import argparse
import json
import sys
import textwrap
from pathlib import Path
from typing import Any

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.vps_logger import VPSLogger
from scripts.lib.paths import RunPaths
from scripts.lib.fal_client import FalClient
from scripts.lib.visual_analyzer import VisualAnalyzer
from scripts.lib.aspect import size_for, grid_for_beats, fal_image_size
from scripts.lib import script_io


AUTO_RETRY_BUDGET = 2


def character_brief(rp: RunPaths, mode: str) -> str:
    """Return the character description text used by both prompting + analysis."""
    if mode == "none" and rp.description_block.is_file():
        return rp.description_block.read_text(encoding="utf-8").strip()
    if rp.character_analysis.is_file():
        try:
            analysis = json.loads(rp.character_analysis.read_text())
        except Exception:
            analysis = {}
        chars = analysis.get("checks", {}).get("characters_present") or []
        if chars:
            return "Characters present in reference sheet: " + ", ".join(chars)
    return "(no character reference)"


KEYFRAME_PROMPT = textwrap.dedent("""\
    Educational explainer keyframe. Style: {style}. Aspect: {aspect}.

    CHARACTERS:
    {chars}

    SHOT (beat {beat_id} — {label}):
    {narration}
    Visual hint: {visual}
    Camera: static medium. Composition: rule of thirds; reading direction L-to-R.
    Background: appropriate to the style; uncluttered.

    SPLIT-SCREEN / SIDE-BY-SIDE RULE (only if the scene calls for comparison):
    - 16:9 (horizontal canvas): split VERTICALLY into left | right halves.
    - 9:16 (vertical canvas)  : split HORIZONTALLY into top / bottom halves.
                                NEVER split a 9:16 frame down the middle vertically.
    - 1:1                    : prefer top/bottom; left/right is acceptable.

    Constraints: no text, no captions, no logos, no UI elements.
""")


PANEL_PROMPT = textwrap.dedent("""\
    Storyboard sheet, {rows}x{cols} panels in a single image with a thin white
    border between cells. Each panel aspect {aspect}, full sheet aspect chosen
    to match. Style: {style}. Locked palette across all panels.

    CHARACTERS (recurring):
    {chars}

    PANELS:
    {panel_list}

    Render: no text, no captions, no panel numbers. Each panel readable as a
    thumbnail. Locked palette, consistent character proportions.
""")


def per_keyframe_call(fal: FalClient, model: str, prompt: str, image_size,
                      ref_image: str | None) -> dict:
    payload: dict[str, Any] = {"prompt": prompt, "image_size": image_size}
    if ref_image:
        payload["image_url"] = ref_image  # nano-banana-2 accepts image_url or image_urls
    return fal.run(model, payload, phase="storyboard")


def panel_call(fal: FalClient, model: str, prompt: str, image_size) -> dict:
    return fal.run(model, {"prompt": prompt, "image_size": image_size},
                   phase="storyboard")


def slice_panel(panel_path: Path, rows: int, cols: int, out_dir: Path,
                beat_ids: list[int]) -> list[Path]:
    from PIL import Image
    img = Image.open(panel_path)
    w, h = img.size
    cw, ch = w // cols, h // rows
    out_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []
    i = 0
    for r in range(rows):
        for c in range(cols):
            if i >= len(beat_ids):
                break
            box = (c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)
            crop = img.crop(box)
            p = out_dir / f"beat_{beat_ids[i]:02d}.png"
            crop.save(p)
            out_paths.append(p)
            i += 1
    return out_paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--auto-retries", type=int, default=AUTO_RETRY_BUDGET)
    args = ap.parse_args()
    rp = RunPaths(Path(args.run_dir))
    rp.ensure_dirs()
    cfg = load_config(rp.dir.parent.parent)
    state = RunState.load_or_init(rp.dir)
    log = VPSLogger(cfg.supabase_url, cfg.supabase_anon, cfg.user_id, rp.dir)
    log.heartbeat(state.run_id, "storyboard", "started")

    brief = json.loads(rp.brief.read_text())
    script = script_io.load(rp.script)
    aspect = brief.get("aspect", "16:9")
    style = brief.get("style", "2D Flat")
    image_mode = brief.get("image_mode", "per_keyframe")
    character_mode = brief.get("character_mode", "abstract")

    chars = character_brief(rp, character_mode)
    char_ref = str(rp.character_sheet) if (character_mode != "none" and rp.character_sheet.is_file()) else None

    fal = FalClient(cfg.fal_key, logger=log, run_id=state.run_id)
    va = VisualAnalyzer(fal, logger=log, run_id=state.run_id)

    storyboard_entries: list[dict] = []

    if image_mode == "storyboard_panel":
        rows, cols = grid_for_beats(aspect, len(script.beats))
        panel_list = "\n".join(
            f"{b.id}. {b.label}: {b.narration_plain[:240]}"
            f"{(' — ' + b.visual) if b.visual else ''}"
            for b in script.beats
        )
        prompt = PANEL_PROMPT.format(rows=rows, cols=cols, aspect=aspect,
                                     style=style, chars=chars, panel_list=panel_list)
        model = (cfg.models.get("storyboard_panel") or {}).get("model") or "fal-ai/gpt-image-2"
        image_size = fal_image_size(aspect, model)
        result = panel_call(fal, model, prompt, image_size)
        img_url = ((result.get("images") or [{}])[0]).get("url") or result.get("image", {}).get("url")
        if not img_url:
            raise SystemExit(f"panel response missing image url: {list(result.keys())}")
        fal.download(img_url, str(rp.panel_png))
        beat_ids = [b.id for b in script.beats]
        slice_panel(rp.panel_png, rows, cols, rp.keyframes_dir, beat_ids)
        for b in script.beats:
            kf = rp.keyframe(b.id)
            ana = va.analyse_keyframe(kf, prompt_used=prompt, character_brief=chars, beat_id=b.id)
            rp.keyframe_analysis(b.id).write_text(json.dumps(ana, indent=2))
            storyboard_entries.append({
                "id": b.id, "label": b.label,
                "prompt": prompt, "image_path": str(kf),
                "analysis_path": str(rp.keyframe_analysis(b.id)),
                "needs_review": bool(ana.get("regen_recommendation")),
            })

    else:  # per_keyframe
        model = (cfg.models.get("per_keyframe") or {}).get("model") or "fal-ai/nano-banana-2"
        image_size = fal_image_size(aspect, model)
        for b in script.beats:
            prompt = KEYFRAME_PROMPT.format(
                style=style, aspect=aspect, chars=chars,
                beat_id=b.id, label=b.label,
                narration=b.narration_plain,
                visual=(b.visual or "(none)"),
            )
            # auto-correct loop
            attempt = 0
            addendum = ""
            kf_url: str | None = None
            ana: dict = {}
            while attempt <= args.auto_retries:
                full_prompt = prompt + (f"\n\nADDITIONAL GUIDANCE (regen):\n{addendum}" if addendum else "")
                result = per_keyframe_call(fal, model, full_prompt, image_size, char_ref)
                kf_url = ((result.get("images") or [{}])[0]).get("url") or result.get("image", {}).get("url")
                if not kf_url:
                    raise SystemExit(f"per_keyframe response missing image url: {list(result.keys())}")
                fal.download(kf_url, str(rp.keyframe(b.id)))
                ana = va.analyse_keyframe(rp.keyframe(b.id),
                                          prompt_used=full_prompt,
                                          character_brief=chars, beat_id=b.id)
                if ana.get("regen_recommendation") in (None, "minor"):
                    break
                addendum = ana.get("corrective_addendum") or "Improve character consistency and palette."
                log.log(state.run_id, "storyboard", "warn",
                        f"beat {b.id} auto-regen attempt {attempt+1}: {addendum}")
                attempt += 1
            rp.keyframe_analysis(b.id).write_text(json.dumps(ana, indent=2))
            storyboard_entries.append({
                "id": b.id, "label": b.label,
                "prompt": prompt, "image_path": str(rp.keyframe(b.id)),
                "analysis_path": str(rp.keyframe_analysis(b.id)),
                "needs_review": ana.get("regen_recommendation") == "major",
            })

    storyboard = {
        "aspect": aspect, "image_mode": image_mode,
        "beats": storyboard_entries,
    }
    rp.storyboard_json.write_text(json.dumps(storyboard, indent=2))
    needs_review = sum(1 for e in storyboard_entries if e.get("needs_review"))
    log.log(state.run_id, "storyboard", "info",
            f"mode={image_mode} beats={len(storyboard_entries)} needs_review={needs_review}")
    state.mark_phase("storyboard", "pending_review")
    log.heartbeat(state.run_id, "storyboard", "complete")
    print(f"[storyboard] mode={image_mode} → {rp.storyboard_json}  beats={len(storyboard_entries)}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
