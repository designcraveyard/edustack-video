---
name: storyboard-generator
description: Use during Phase 3b of a video run. Generates per-beat keyframe images either as a sliced multi-panel sheet (storyboard_panel mode) or one image per beat (per_keyframe mode). Runs Gemini analysis on every keyframe and feeds findings forward.
---

# Storyboard Generator (Phase 3b)

## Inputs

- `<run-dir>/brief.json` (must have `image_mode`)
- `<run-dir>/script.md`, `<run-dir>/audio/vo_timeline.json`
- Either `<run-dir>/characters/sheet.png` + `descriptions.json` (modes human/abstract — `descriptions.json` carries the verbatim per-character paragraphs we paste identically into every keyframe prompt) OR `<run-dir>/characters/description_block.md` (mode none). Legacy `analysis.json.checks.characters_present` is a thin fallback only — use `descriptions.json` when present.

## Outputs

Common:
- `<run-dir>/storyboard/storyboard.json` — per-beat: id, label, prompt, image_path, analysis_path, duration_ms
- `<run-dir>/storyboard/keyframes/beat_*.png`
- `<run-dir>/storyboard/analysis/beat_*.json`

Mode A (`storyboard_panel`):
- `<run-dir>/storyboard/panel.png` (raw gpt-image-2 multi-panel)

## Checklist (TodoWrite)

1. From `vo_timeline.beats`, compute one keyframe per beat.
2. **Resolve image aspect/size from `brief.aspect`** via `scripts.lib.aspect.fal_image_size(aspect, model)`. Returns a preset name (`portrait_16_9` / `landscape_16_9` / `square_hd`) for nano-banana / flux / imagen (which 422 on arbitrary `{width,height}`), or explicit dimensions for gpt-image-2. Never hardcode 16:9.
3. **Author structured `anchors`** for any beat with two or more labelled elements in a fixed spatial relationship (split-screen, A-vs-B, top/bottom). The clip-generator reads these from `storyboard.json` and bakes spatial constraints into the clip prompt — without anchors, i2v models reliably swap sides (HERBA/CARNI class of bug). See @references/storyboard-prompting.md ▸ "Structured anchors".
3. Branch on `image_mode`:
   - **Mode A** (`storyboard_panel`):
     - Build a panel prompt requesting an N-cell grid (N = number of beats), 16:9 panel layout, consistent palette. The CHARACTERS block in the prompt is built by `character_brief()` (precedence: `descriptions.json` verbatim → `description_block.md` → legacy `analysis.json` label).
     - Call `fal-ai/gpt-image-2`. Save `panel.png`.
     - Run `scripts/extract_keyframes.py` (PIL slicer) → `keyframes/beat_*.png`.
   - **Mode B** (`per_keyframe`):
     - For each beat, build a prompt per @references/storyboard-prompting.md.
     - If `character_mode != none`, attach `characters/sheet.png` as a reference image.
     - If `character_mode == none`, prepend `characters/description_block.md` verbatim.
     - Call `fal-ai/nano-banana-2` per beat. Save `keyframes/beat_N.png`.
3. For each keyframe, run Gemini 2.5 Pro via `fal-ai/any-llm`. Ask the questions in @references/visual-analysis-prompts.md. Save `analysis/beat_N.json`.
4. **Auto-correct loop** (max 2 retries per beat):
   - If Gemini reports a mismatch with the prompt (missing character, wrong palette, etc.), regenerate that beat with a corrective addendum.
   - If still mismatched after 2 tries, mark `needs_review: true` in `storyboard.json` and let the gate handle it.
5. Write `storyboard.json`. Surface for Gate 3.

## References

- @references/storyboard-prompting.md
- @references/visual-analysis-prompts.md
