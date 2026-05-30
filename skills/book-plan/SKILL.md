---
name: book-plan
description: Phase B1 — curate the book page list. Reads script + characters + keyframes + brief.book. Produces book/plan.json with one entry per page (template, scene_prompt, book_voice_copy, refs). Surfaces Gate B1 in chat for user approval. Use when the orchestrator is at the post-video book branch and the brief has book.page_count_target > 0.
---

# Phase B1 — Book Plan

## Inputs
- `<run-dir>/brief.json` (must have `book.page_count_target > 0`)
- `<run-dir>/script.md` (Phase 1 — `Script` with `beats: list[Beat]`)
- `<run-dir>/characters/sheet.png` + `characters/description_block.md` + `characters/analysis.json` (Phase 3)
- `<run-dir>/storyboard/keyframes/beat_NN.png` (Phase 4)

## Output
`<run-dir>/book/plan.json`:

```json
{
  "pages": [
    {
      "page_no": 1,
      "scene_source": "beat_3" | "book_only",
      "keyframe_ref": "storyboard/keyframes/beat_03.png" | null,
      "character_refs": ["characters/sheet.png"],
      "template": "split-layout",
      "canvas": "A3L",
      "scene_prompt": "Mowgli sleeping with wolves under a banyan tree, dawn light",
      "book_voice_copy": "When the moon dipped low, Mowgli curled up beside his wolf brothers.",
      "text_zone_hint": "left third, top-aligned, 3 lines",
      "prompt_params": {
        "text_zone_side": "RIGHT",
        "text_zone_percent": "35",
        "art_style_description": "soft watercolour with ink outlines"
      }
    }
  ]
}
```

## Logic

1. Read all inputs. Build `character_brief` text from `characters/description_block.md`.
2. Read `brief.book.templates` (2–4 templates) and `brief.book.page_count_target`. These were chosen in the brief form's visual template gallery. If `brief.book.templates` is missing/empty, or the user asks to re-pick the layouts before planning, open the standalone [book-template-picker](../book-template-picker/SKILL.md) (`node ${CLAUDE_PLUGIN_ROOT}/skills/book-template-picker/server/server.mjs --run-dir "$RUN_DIR" --min 2 --max 4`), wait for `PICKER_OK`, and read the shortlist from `<run-dir>/book/template-selection.json`.
3. Decide page composition: ~60% reused video scenes + ~40% book-only scenes. Total = exactly `page_count_target`.
4. For each page, assign a template using this content-type → template map (pick the FIRST in the user's shortlist that matches):
   - narrative scene → `full-bleed-with-text-zone`, `split-layout`, or `illustrated-border`
   - educational scene → `scattered-spots`, `connected-infographic`, or `split-layout`
   - character-intro scene → `vignette-on-page`, `character-text-pocket`, or `split-layout`
   - dramatic moment → `full-spread-no-text`, `spread-scene-plus-spots`, or `full-bleed-with-text-zone`

   If none in the shortlist matches a category, fall back to the first template in the shortlist.
5. Rewrite each scene's narration into `book_voice_copy` using the chosen `brief.book.voice`:
   - `storybook_narrator`: lyrical, past tense, sensory detail
   - `factual_calm`: present tense, clear and concrete
   - `playful_rhyming`: short AABB rhymes
   Constraint: ≤4 lines per page.
6. For each page, fill template-specific `prompt_params` (see `references/templates.md`).
7. Write `book/plan.json`. Print a chat-friendly Markdown summary with:
   - page count, template distribution, voice
   - per-page: page_no, template, scene_prompt (truncated 80 chars), book_voice_copy
   - clickable file:// links to each `keyframe_ref` and `character_refs`
8. Wait for user reply at Gate B1: `approve` or `regen page N: <comment>` or `regen all`.

## Invocation

```
python3 -m scripts.phase_book_plan --run-dir <run-dir>
```

The script provides a deterministic fallback page list when invoked without an
LLM pass. The skill's chat-side authoring lets Claude propose better
placeholder values and book-voice copy; the script then serializes.

## References
- @references/templates.md — prompt patterns per template
- @references/prompts-log.md — empirical placeholder values
