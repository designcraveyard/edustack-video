---
name: storyboard-generator
description: Use during Phase 3b of a video run. Generates per-beat keyframe images either as a sliced multi-panel sheet (storyboard_panel mode) or one image per beat (per_keyframe mode). Runs Gemini analysis on every keyframe and feeds findings forward. Structured anchors[] authoring is MANDATORY for any beat with two or more labelled spatial elements.
---

# Storyboard Generator (Phase 3b)

## Inputs

- `<run-dir>/brief.json` — provides `image_mode`, `aspect`, `style`, `character_mode`
- `<run-dir>/script.md` — parsed by `script_io.load` (frontmatter + beats + Cast). The Scene Timeline rows tell you per-beat narration, intended keyframe, and transitions.
- `<run-dir>/audio/vo_timeline.json` — per-beat durations
- Either `<run-dir>/characters/sheet.png` + `descriptions.json` (modes `human` / `abstract` — `descriptions.json` carries the verbatim per-character paragraphs pasted identically into every keyframe prompt), OR `<run-dir>/characters/description_block.md` (mode `none`). Legacy `analysis.json.checks.characters_present` is a thin fallback only — use `descriptions.json` when present.

## Outputs

- `<run-dir>/storyboard/storyboard.json` — per-beat: `id`, `label`, `prompt`, `image_path`, `analysis_path`, `duration_ms`, **`anchors[]`** (when applicable, see below)
- `<run-dir>/storyboard/keyframes/beat_*.png`
- `<run-dir>/storyboard/analysis/beat_*.json`
- Mode A only: `<run-dir>/storyboard/panel.png` (raw gpt-image-2 multi-panel)

## HARD REQUIREMENT: structured anchors

For every beat whose visual hint or Scene Timeline keyframe describes **two or more named elements in a fixed spatial position** (left/right, top/bottom, foreground/background, before/after), you MUST author an `anchors[]` array in `storyboard.json` for that beat. The clip-generator reads anchors from `storyboard.json` and bakes spatial constraints into the i2v prompt. **Without anchors, image-to-video models reliably swap sides during clip generation** — the canonical HERBA/CARNI failure mode.

Anchor schema:

```json
"anchors": [
  { "element": "rabbit eating grass", "side": "left",  "label": "HERBIVORE" },
  { "element": "lion mid-pounce",     "side": "right", "label": "CARNIVORE" }
]
```

`side` ∈ `left` `right` `top` `bottom` `center` `foreground` `background`. Aspect-ratio rules:

- **16:9** → use `left` / `right` for split-screens (vertical divider).
- **9:16** → use `top` / `bottom` (horizontal divider). **NEVER** vertical for 9:16 — the elements end up paper-thin and unreadable.
- **1:1** → prefer `top` / `bottom`.

Trigger phrases that should always produce anchors:

- "X on the left, Y on the right" / "X above, Y below"
- "before vs after" / "compare A and B"
- "X stays in the foreground while Y is in the background"
- "split-screen / divided / two halves"
- Text labels next to specific elements

Single-subject beats do NOT need anchors. Don't author anchors just because you can — they constrain the camera and over-rigidify simple scenes.

Full authoring guide + good/bad examples: [references/anchor-authoring.md](./references/anchor-authoring.md). Read this reference whenever a beat has two or more named elements.

## Checklist (TodoWrite)

1. From `vo_timeline.beats`, compute one keyframe per beat. From the Scene Timeline rows in `script.md`, pull the per-beat keyframe description and intended transition.
2. **Resolve image aspect/size from `brief.aspect`** via `scripts.lib.aspect.fal_image_size(aspect, model)`. Returns a preset name (`portrait_16_9` / `landscape_16_9` / `square_hd`) for nano-banana / flux / imagen (which 422 on arbitrary `{width, height}`), or explicit dimensions for gpt-image-2. Never hardcode 16:9.
3. **Author `anchors[]` for every beat that needs them.** Walk every beat's visual hint and Scene Timeline keyframe text. Apply the trigger-phrase rule above. For any beat that qualifies, write the `anchors[]` array following the schema. Read [references/anchor-authoring.md](./references/anchor-authoring.md) if uncertain. Anchors live in `storyboard.json` per beat; the clip-generator reads them automatically.
4. Branch on `image_mode`:
   - **Mode A** (`storyboard_panel`):
     - Build a panel prompt requesting an N-cell grid (N = number of beats), `brief.aspect` per cell, consistent palette. The CHARACTERS block in the prompt is built by `character_brief()` (precedence: `descriptions.json` verbatim → `description_block.md` → legacy `analysis.json` label).
     - Call `fal-ai/gpt-image-2`. Save `panel.png`.
     - Run `scripts/extract_keyframes.py` (PIL slicer) → `keyframes/beat_*.png`.
   - **Mode B** (`per_keyframe`):
     - For each beat, build a prompt per [references/storyboard-prompting.md](./references/storyboard-prompting.md).
     - If `character_mode != none`, attach `characters/sheet.png` as a reference image.
     - If `character_mode == none`, prepend `characters/description_block.md` verbatim.
     - Call `fal-ai/nano-banana-2` per beat. Save `keyframes/beat_N.png`.
5. For each keyframe, run Gemini 2.5 Pro via `fal-ai/any-llm`. Ask the questions in [references/visual-analysis-prompts.md](./references/visual-analysis-prompts.md). Save `analysis/beat_N.json`.
6. **Auto-correct loop** (max 2 retries per beat):
   - If Gemini reports a mismatch with the prompt (missing character, wrong palette, anchored element on wrong side, etc.), regenerate with a corrective addendum.
   - If still mismatched after 2 tries, mark `needs_review: true` in `storyboard.json` and let the gate handle it.
7. Write `storyboard.json` with all per-beat metadata including `anchors[]` where authored. Surface for Gate 3.

## Quality bar (self-check before exit)

- For every beat whose visual hint or Scene Timeline keyframe mentions two or more named elements in a fixed spatial position, `storyboard.json` has a non-empty `anchors[]` array for that beat.
- All anchor entries have `element` (concrete noun phrase, not "thing on left"), `side` (valid enum), and optionally `label`.
- 9:16 storyboards do NOT use `left` / `right` anchors (would produce paper-thin strips).
- `keyframes/beat_NN.png` exists for every beat in `script.beats`.
- For each keyframe, `analysis/beat_NN.json` is present; any `needs_review: true` is surfaced to Gate 3.

## Common failure modes (avoid)

- **Skipping anchor authoring for split-screen beats.** Produces HERBA/CARNI side-swap bugs in the final clips. The Gemini analysis on the keyframe might pass (the still frame is correct); the clip generation drifts because the i2v model has no spatial constraint.
- **Vague anchor `element` text.** "thing on left" gives the auditor nothing to verify. Be specific enough that a stranger could identify the element from the description.
- **Using `left` / `right` anchors in a 9:16 storyboard.** Each side becomes ~540 px wide × 1920 tall — unreadable. Use `top` / `bottom`.
- **Authoring anchors for single-subject beats.** Over-constrains the camera; no benefit.
- **Hardcoding 16:9 sizes.** Read from `brief.aspect` via the `scripts.lib.aspect` helper.
- **Treating the legacy `analysis.json.checks.characters_present` as primary.** It's a thin fallback. Always prefer `descriptions.json` (verbatim per-character paragraphs from Phase 3a).

## References

- [references/anchor-authoring.md](./references/anchor-authoring.md) — **the** reference for when and how to author anchors. Mandatory reading when a beat has two or more named elements.
- [references/storyboard-prompting.md](./references/storyboard-prompting.md) — Mode A (panel) and Mode B (per-keyframe) prompt templates.
- [references/visual-analysis-prompts.md](./references/visual-analysis-prompts.md) — Gemini per-keyframe QA schema and prompt template.
