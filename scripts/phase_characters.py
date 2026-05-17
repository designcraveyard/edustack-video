"""Phase 3a — Characters.

Three branches driven by brief.character_mode:
  - human    : Nano Banana 2 1–2-character pose/expression sheet + Gemini analysis.
  - abstract : Nano Banana 2 stylized reference sheet + Gemini analysis.
  - none     : write characters/description_block.md only; no image; Phase 3a otherwise skipped.

In `none` mode the description block is what later phases prepend to every
storyboard/clip prompt so generators see the same character description every
call (eliminates drift without conditioning on an image).
"""
from __future__ import annotations
import argparse
import json
import sys
import textwrap
from pathlib import Path

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.vps_logger import VPSLogger
from scripts.lib.paths import RunPaths
from scripts.lib.fal_client import FalClient
from scripts.lib.visual_analyzer import VisualAnalyzer
from scripts.lib import script_io


HUMAN_PROMPT_TMPL = textwrap.dedent("""\
    Character reference sheet, model-sheet style, neutral white background,
    soft three-quarter lighting. {grid_spec} of the SAME character(s):
    front view, side view, and three-quarter view × neutral, happy, surprised
    expressions. Render style: {style}. Aspect: 1:1. No text, no labels, no border.

    CHARACTERS:
    {char_paragraph}

    Hard rules: neutral background only; identical proportions across all cells;
    consistent palette; readable at thumbnail size.""")


ABSTRACT_PROMPT_TMPL = textwrap.dedent("""\
    Style reference sheet for an animated explainer. Style: {style}.
    Show the SAME stylized character (non-human / abstract) in 6 poses:
    idle, moving, pointing, surprised, sad, happy. Neutral background,
    consistent palette. Aspect: 1:1. No text, no labels.

    CHARACTER CONCEPT:
    {char_paragraph}""")


DESC_BLOCK_SYSTEM = textwrap.dedent("""\
    You are a continuity supervisor for an explainer video. Given the script's
    topic and any character notes, write a structured 'character description block'
    that will be prepended to every storyboard and clip prompt to keep characters
    consistent across the whole video.

    Return STRICT markdown matching:
      ## Characters
      - **<role>**: <species/age> · <build/height> · <hair> · <eyes> · <skin/coat> · <outfit> · <signature prop/expression>.
      - ...

      ## Crowd / extras
      - <collective character description, if relevant>

      ## Consistency notes
      - <2-3 bullet rules: relative heights, lighting, palette locks>

    Be concrete and visual. No adjectives that don't translate to motion.""")


def char_paragraph_from_script(script: script_io.Script, notes: str) -> str:
    """Cheap heuristic: combine title + first beat + notes into a paragraph for
    the sheet prompt. Gemini-based summarization for human/abstract sheets is
    overkill; the storyboard phase will do the real character grounding."""
    head = script.beats[0].narration_plain if script.beats else script.title
    return f"{script.title}. {head[:240]} {notes}".strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    rp = RunPaths(Path(args.run_dir))
    rp.ensure_dirs()
    cfg = load_config(rp.dir.parent.parent)
    state = RunState.load_or_init(rp.dir)
    log = VPSLogger(cfg.vps_url, cfg.vps_token, rp.dir)
    log.heartbeat(state.run_id, "characters", "started")

    brief = json.loads(rp.brief.read_text())
    mode = brief.get("character_mode", "abstract")
    style = brief.get("style", "2D Flat")
    notes = brief.get("notes", "") or ""
    script = script_io.load(rp.script)

    fal = FalClient(cfg.fal_key, logger=log, run_id=state.run_id)

    if mode == "none":
        # Generate the description block via Gemini.
        user = (
            f"TOPIC: {script.title}\n"
            f"STYLE: {style}\nLANGUAGE: {script.language}\n"
            f"NOTES: {notes or '(none)'}\n\n"
            f"FIRST BEAT (for context):\n{script.beats[0].narration_plain if script.beats else ''}"
        )
        out = fal.any_llm(
            "google/gemini-2.5-pro",
            prompt=user, system_prompt=DESC_BLOCK_SYSTEM, phase="characters",
        )
        text = (out or {}).get("output") or (out or {}).get("text") or ""
        if not text and isinstance(out, dict):
            ch = (out.get("choices") or [{}])[0]
            text = ((ch.get("message") or {}).get("content")) or ""
        text = text.strip() or "## Characters\n- (none defined; rely on per-beat hints)\n"
        rp.description_block.write_text(text)
        log.log(state.run_id, "characters", "info",
                f"mode=none wrote {rp.description_block} bytes={len(text)}")
        state.mark_phase("characters", "complete")  # no gate for description block
        log.heartbeat(state.run_id, "characters", "complete")
        print(f"[characters] mode=none → {rp.description_block}", file=sys.stderr)
        return 0

    # human / abstract: generate a sheet
    char_para = char_paragraph_from_script(script, notes)
    model = (cfg.models.get("character_sheet") or {}).get("model") or "fal-ai/nano-banana-2"
    size = (cfg.models.get("character_sheet") or {}).get("size") or "1024x1024"
    w, h = (int(x) for x in size.lower().split("x", 1))

    if mode == "human":
        prompt = HUMAN_PROMPT_TMPL.format(
            grid_spec="A 3x3 grid", style=style, char_paragraph=char_para)
    else:  # abstract
        prompt = ABSTRACT_PROMPT_TMPL.format(style=style, char_paragraph=char_para)

    payload = {"prompt": prompt, "image_size": {"width": w, "height": h}}
    result = fal.run(model, payload, phase="characters")
    img_url = ((result.get("images") or [{}])[0]).get("url") or result.get("image", {}).get("url")
    if not img_url:
        raise SystemExit(f"character sheet response missing image url: {list(result.keys())}")

    fal.download(img_url, str(rp.character_sheet))

    # Vision pass: describe what was actually drawn.
    va = VisualAnalyzer(fal, logger=log, run_id=state.run_id)
    analysis = va.analyse_keyframe(
        rp.character_sheet, prompt_used=prompt,
        character_brief=char_para, beat_id=0, phase="characters",
    )
    rp.character_analysis.write_text(json.dumps(analysis, indent=2))

    log.log(state.run_id, "characters", "info",
            f"mode={mode} wrote {rp.character_sheet.name} + analysis.json")
    state.mark_phase("characters", "pending_review")
    log.heartbeat(state.run_id, "characters", "complete")
    print(f"[characters] mode={mode} → {rp.character_sheet}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
