---
name: character-sheet-generator
description: Use during Phase 3a of a video run. Generates a character reference sheet for human or abstract character modes. For character_mode none, writes a reusable description block instead — Phase 3a is otherwise skipped.
---

# Character Sheet Generator (Phase 3a)

## Inputs

- `<run-dir>/brief.json` (must have `character_mode`)
- `<run-dir>/script.md` (for narrative cues about characters)

## Outputs (mode-dependent)

| `character_mode` | Outputs |
|---|---|
| `human` | `characters/sheet.png` (Nano Banana 2, 1–2 character grid: front / side / 3⁄4) + `characters/analysis.json` |
| `abstract` | `characters/sheet.png` (Nano Banana 2, stylized reference) + `characters/analysis.json` |
| `none` | `characters/description_block.md` only (no image) |

## Checklist (TodoWrite)

1. Branch on `character_mode`.
2. **human / abstract**:
   - Build a prompt per @references/character-sheet-design.md and @references/model-selection.md.
   - Call `fal-ai/nano-banana-2` via `scripts/lib/fal_client.py`.
   - Save PNG.
   - Run visual analysis (`fal-ai/any-llm` → `google/gemini-2.5-pro`) describing characters and saving `analysis.json` (names, traits, recognizable features).
3. **none**:
   - Generate a structured "character description block" per @references/description-block-template.md.
   - Write to `<run-dir>/characters/description_block.md`. This file is prepended verbatim to every Phase 3b / Phase 4 prompt.
   - Do NOT generate any image. Skip Gate 3 image review for this phase.

## References

- @references/character-sheet-design.md
- @references/description-block-template.md
- @references/model-selection.md
