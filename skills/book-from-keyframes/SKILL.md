---
name: book-from-keyframes
description: Use when the user wants to build a print-ready picture book from an existing video run's storyboard keyframes — reusing the keyframes verbatim instead of generating new illustrations via gpt-image-2. Trigger phrases include "book from video frames", "book from keyframes", "book layout from my video", "reuse the storyboard for the book", or invoking /create-book-from-keyframes. Skips Phase B1 and B2 entirely.
---

# Book from Keyframes — standalone skill

This skill builds a print-ready picture book from an **existing video run's storyboard keyframes** — no fresh gpt-image-2 illustrations, no birefnet QA loop. The output is the same as the default book branch: transparent-BG RGBA PNGs at A4P (2480×3508) or A3L (4961×3508) @ 300 DPI, drop-in for InDesign / Affinity.

**When to use this vs the default `/create-video` book branch:**

| Scenario | Use |
|---|---|
| User wants a book illustrated identically to the video's keyframes (visual continuity) | this skill |
| User wants a book with NEW illustrations (different compositions, different beats, fresh art) | default Phase B1–B3 (`brief.book.page_count_target > 0` in the brief) |
| User wants a book AFTER a video run completed, without re-running the whole pipeline | this skill |
| User wants to mix: some pages from keyframes, some new | default Phase B1 — its planner can be told to source from existing keyframes for selected pages |

## Inputs

- An existing run directory under `<output>/runs/` with at least:
  - `storyboard/keyframes/beat_*.png` (the source illustrations)
  - `script.md` (optional but useful — provides Strategy, Cast, Sound, narration to derive book voice copy from)
- User intent: how many pages, which keyframes go to which page, which template per page, what voice copy goes on each sidecar.

## Outputs

- `<run-dir>/book/from_keyframes.config.json` — the assignment you composed in chat. Reviewable, re-runnable.
- `<run-dir>/book/pages/page-NN.png` — RGBA, transparent-BG cutouts at the keyframes' native resolution (after birefnet, when requested).
- `<run-dir>/book/plan.json` — same shape as Phase B1 output, consumed by `phase_book_print_prep`.
- `<run-dir>/book/print/page-NN.png` — final A4P (2480×3508) or A3L (4961×3508) @ 300 DPI canvases, ready for layout.
- `<run-dir>/book/print/page-NN.txt` — sidecar text file with the intended book voice copy.

## Checklist (TodoWrite)

1. **Pick the source run.** If the user is already inside a run-directory context, use that. Otherwise list `<output>/runs/*` and let them pick. Required: the chosen run must have `storyboard/keyframes/beat_*.png` files. Refuse and explain if not.

2. **Show available keyframes.** Use `ls` (or read the storyboard.json metadata) to list every `beat_NN.png` with its beat label and narration. Format as a numbered list the user can refer to:
   ```
   1. beat_01.png  hook        "Why does a plant droop in the dark?"
   2. beat_02.png  setup       "Leaves are tiny food factories..."
   ...
   ```

3. **Walk the user through page assignment.** For each book page they want, gather:
   - **Source keyframe** — which `beat_NN.png` to use. Same keyframe can be used on multiple pages with different templates. The user can also skip beats they don't want in the book.
   - **Template** — one of the nine: `full-bleed-with-text-zone`, `vignette-on-page`, `split-layout`, `scattered-spots`, `full-spread-no-text`, `illustrated-border`, `character-text-pocket`, `connected-infographic`, `spread-scene-plus-spots`. See [skills/book-plan/references/templates.md](../book-plan/references/templates.md) for the layout intent of each.
   - **Book voice copy** — the text that lives on the printed page beside / under the illustration. Drafted by you in the chosen `brief.book.voice` style (storybook_narrator / factual_calm / playful_rhyming). For each beat, you can adapt the script's narration into book voice (the video narration tends to be punchy and verbal; book voice is calmer and reads on the page). Show the user your draft per page; let them tweak in chat.
   - **Background removal** — default `true` (run fal-ai/birefnet/v2 to cut out the subject and leave a transparent background; cleanest for layout). User can opt out per-page (`false`) if the keyframe already has a clean background or they want to preserve scene context (e.g. for a `full-bleed-with-text-zone` template where the full scene is the point).

4. **Compose `book/from_keyframes.config.json`** and show it to the user before invoking the script. Schema:
   ```jsonc
   {
     "title": "Photosynthesis",
     "voice": "storybook_narrator",
     "pages": [
       {
         "page_no": 1,
         "source_keyframe": "storyboard/keyframes/beat_01.png",
         "template": "full-bleed-with-text-zone",
         "book_voice_copy": "The little plant in the dark room began to droop. It wondered: where had the sun gone?",
         "remove_background": false
       },
       {
         "page_no": 2,
         "source_keyframe": "storyboard/keyframes/beat_03.png",
         "template": "vignette-on-page",
         "book_voice_copy": "Inside every leaf, there is a secret pigment that loves sunlight. Its name is chlorophyll.",
         "remove_background": true
       }
     ]
   }
   ```

5. **Run the script** — this is the only Python invocation. It handles birefnet for any page with `remove_background: true`, writes `book/plan.json`, and (with `--run-print-prep`) auto-composes the A4P / A3L canvases at 300 DPI.
   ```bash
   "$OUTPUT/.venv/bin/python" -m scripts.phase_book_from_keyframes \
       --run-dir "$RUN_DIR" --run-print-prep
   ```

6. **Surface the outputs.** Walk the user through `book/print/page-NN.png` files (clickable paths). For each page, also show the sidecar `.txt` so they can verify the voice copy.

7. **On feedback** — if the user wants to change a page (different template, different keyframe, edited voice copy), edit `book/from_keyframes.config.json` and re-run the script. It overwrites the affected `book/pages/page-NN.png` and `book/print/page-NN.png` in place.

## Background-removal guidance

When in doubt about `remove_background`:

| Template | Recommended default |
|---|---|
| `full-bleed-with-text-zone` | `false` — the full scene goes edge-to-edge; transparent BG would leave a checkered hole. |
| `full-spread-no-text` | `false` — same reason. |
| `spread-scene-plus-spots` | `false` for the main spread, `true` for the spot illustrations. |
| `vignette-on-page` | `true` — the illustration is meant to sit on white page space, transparent BG is the whole point. |
| `split-layout` | `true` — illustration on one half, copy on the other. Transparent BG keeps the white half clean. |
| `scattered-spots` | `true` — small cutout illustrations dotted across the page. |
| `illustrated-border` | `true` — characters / props forming a border, white page in the middle. |
| `character-text-pocket` | `true` — a character sits next to a text block on the page. |
| `connected-infographic` | `true` — labeled diagrams need clean cut-outs. |

Override these defaults when the user explicitly wants the scene context preserved.

## Common failure modes (avoid)

- **Running the script with no `from_keyframes.config.json`.** It exits with code 2 and a clear error. Always compose and save the config first.
- **Pointing `source_keyframe` at a file that doesn't exist.** The script logs and skips that page. Always validate paths from `storyboard/keyframes/` before writing the config.
- **Mixing this skill with the default `brief.book.page_count_target > 0` book branch on the same run.** They both write to `<run-dir>/book/plan.json` and `<run-dir>/book/print/` — running both clobbers each other's output. Pick one path per run.
- **Forgetting the sidecar `.txt`.** The book pages are RGBA with NO text burned in — the printed copy lives ONLY in the sidecar `.txt` file. Make sure the user knows to use it during InDesign layout.

## Quality bar (self-check before exit)

- `book/from_keyframes.config.json` exists, has at least one page, every page entry has all required fields (`page_no`, `source_keyframe`, `template`, `book_voice_copy`, `remove_background`).
- Every referenced `source_keyframe` file exists under `<run-dir>/storyboard/keyframes/`.
- Every `template` is one of the nine valid template ids.
- Every `book_voice_copy` is written in the chosen voice (not the video narration verbatim — those are different registers).
- After the script runs, `book/print/page-NN.png` exists for every page in the config, and each is exactly A4P or A3L dimensions (2480×3508 or 4961×3508).
- The page count matches what the user asked for.

## References

- [skills/book-plan/references/templates.md](../book-plan/references/templates.md) — the nine layout templates with descriptions and wireframes.
- [scripts/lib/book_canvas.py](../../scripts/lib/book_canvas.py) — the per-template positioning rules (used by `phase_book_print_prep`).
- [skills/book-plan/SKILL.md](../book-plan/SKILL.md) — the default book-planning flow this skill is an alternative to.
