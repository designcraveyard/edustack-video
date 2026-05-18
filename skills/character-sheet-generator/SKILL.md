---
name: character-sheet-generator
description: Use during Phase 3a of a video run. Generates a rich character reference sheet (gpt-image-2, 16:9, title + hero pose + expressions row + turnaround + palette + details) for `character_mode: human` or `abstract`. For `character_mode: none`, writes a reusable description block instead and skips the sheet.
---

# Character Sheet Generator (Phase 3a)

The character sheet locks the **visual identity contract** for the rest of the pipeline. Phase 3b (keyframes) reads the sheet as an image reference; Phase 4 (clips) reads the verbatim per-character description text. One source of truth, applied everywhere.

## Inputs

- `<run-dir>/brief.json` — provides `character_mode`, `style`, `notes`.
- `<run-dir>/script.md` — provides the `## Cast` block (one `### Name` per character with Role / Personality / Voice and tone / Looks bullets).

## Outputs

| `character_mode` | Files written | Notes |
|---|---|---|
| `human` | `characters/sheet.png`, `characters/sheet_prompt.md`, `characters/analysis.json`, `characters/descriptions.json` | gpt-image-2, rich template, 16:9. 1–2 characters per sheet. |
| `abstract` | same four files | Same template; aesthetic bullets nudge mascot-readability (non-human / stylised). |
| `none` | `characters/description_block.md` only | No sheet PNG. Gemini 2.5 Pro composes the continuity block from script topic + notes. |

`descriptions.json` is the most important output for downstream phases — it carries the verbatim per-character paragraphs that storyboard + clip prompts paste IDENTICALLY into their CHARACTERS section.

## Checklist (TodoWrite)

1. **Branch on `character_mode`.**
2. **human / abstract:**
   - Load the script and extract the `## Cast` block (`script_io.parse_cast`).
   - Pick the cast for the sheet: keep the script's order, cap at 2.
   - Compose the prompt using the canonical template — see [`references/prompt-template.md`](./references/prompt-template.md). The renderer fills in style descriptor, aesthetic bullets, hero pose, verbatim character descriptions, expression rows, palette swatches, details, and finish bullets.
   - Call `fal-ai/gpt-image-2` (configured in `seed/models.yaml > character_sheet`) with `image_size: landscape_16_9` and `quality: high`.
   - Save the PNG to `characters/sheet.png`.
   - Run the QA pass (`VisualAnalyzer.analyse_character_sheet`) → describe → audit → verdict. Auto-regen up to 2× when the verdict is `NEEDS_REGEN`, threading `corrective_addendum` into the next attempt.
   - Persist `sheet_prompt.md` (full prompt sent + style descriptor + verbatim descriptions), `analysis.json` (QA report + `_qa_history`), and `descriptions.json` (the verbatim per-character paragraphs downstream phases consume).
3. **none:**
   - Call Gemini 2.5 Pro with the description-block system prompt.
   - Write the result to `characters/description_block.md`.
   - No image. No QA loop. Skip Gate 3 review for this phase.

## How downstream phases consume the output

| Phase | What it reads | How |
|---|---|---|
| 3b — Storyboard | `descriptions.json` (preferred) → `description_block.md` (none mode) → `analysis.json` (legacy fallback) | Pastes verbatim descriptions into every keyframe prompt's CHARACTERS section. Image-mode `per_keyframe` also uses `sheet.png` as a reference image. |
| 4 — Clip generation | Same precedence as Phase 3b | Embeds verbatim descriptions in every Seedance prompt so character identity holds across all clips. |
| Book mode (Phase B*) | `description_block.md` → `analysis.json` | Reads the continuity block for character grounding on book illustrations. |

## References

- [`references/prompt-template.md`](./references/prompt-template.md) — canonical prompt structure with two end-to-end examples (Pixar / Watercolour).
- [`references/character-sheet-design.md`](./references/character-sheet-design.md) — layout rules + QA pattern + outputs contract.
- [`references/model-selection.md`](./references/model-selection.md) — why gpt-image-2 (vs Nano Banana 2 / Flux / Imagen) + override knobs.
- [`references/description-block-template.md`](./references/description-block-template.md) — text-contract shapes for both `descriptions.json` and `description_block.md`.

## Quick run

```bash
uv run python -m scripts.phase_characters --run-dir <output>/runs/<run-code>
```

Reads `brief.json` and `script.md` from the run dir; writes outputs to `characters/`. Idempotent — re-running overwrites the sheet + prompt + analysis + descriptions in place (Phase 3a doesn't snapshot history except via `analysis.json._qa_history`).
