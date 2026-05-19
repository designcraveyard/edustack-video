---
name: book-standalone
description: Use when the user wants to create a children's book WITHOUT first generating a video — a video-less book run. Trigger phrases include "just make a book", "create a book", "book without video", "/create-book", or any book request that doesn't reference an existing video run. Walks the user through topic, source content (chapter text + reference images), templates, and book voice, then renders each page through the shared two-image-prompting layout renderer (fal-ai/gpt-image-2 at 2K with the template's layout reference image + the user's source content).
---

# Book (standalone, video-less)

This skill is the entry point for **book-only runs** — no video generation, no Phase 1–5. The user provides chapter text + optional reference images, picks templates, and gets A4P / A3L 300 DPI print-ready pages directly.

Three paths to a book exist now; pick the right one for the request:

| Path | When | Skill |
|---|---|---|
| Video → default Phase B1–B3 | User wants a video AND a book on the same topic, with fresh book illustrations | [book-plan](../book-plan/SKILL.md) + book-render + book-print-prep |
| Video → book from keyframes | User has a finished video and wants the book to reuse the same art | [book-from-keyframes](../book-from-keyframes/SKILL.md) |
| **Book only (no video)** | **This skill.** User wants a book directly, no video. | book-standalone |

## Inputs

- **Topic** — what the book is about (1–2 sentences from the user).
- **Class level** — 1–12, drives vocabulary ceiling and pacing.
- **Language** — English / Hindi / etc.
- **Style** — Pixar / 2D animated / watercolour / photoreal / etc. — copy from the user's intent.
- **Source content** — at least one of:
  - **Chapter text** — paste / file path / URL. Saved to `<run-dir>/source/chapter.txt`. Used to derive book voice copy per page.
  - **Reference images** — uploaded by the user, saved to `<run-dir>/sources/img-NN.png`. These are passed to gpt-image-2 as IMAGE 2 (content/style reference) for any page that uses them.
- **Page count** — 1–12.
- **Templates** — 2–4 picked from the 9. Show the user `seed/template-references/manifest.json` content classifications + the `best_ref` previews when they're undecided.

## Outputs

- `<run-dir>/brief.json` — mini brief with topic / class / language / style.
- `<run-dir>/source/chapter.txt` — chapter text persisted.
- `<run-dir>/sources/img-NN.png` — user-uploaded reference images.
- `<run-dir>/book/plan.json` — per-page assignment: template, content_refs[], character_refs[], scene_description, book_voice_copy. Reviewable, editable, re-runnable.
- `<run-dir>/book/pages/page-NN.png` — gpt-image-2 output at 1024×1456 (A4P) or 1456×1024 (A3L) RGBA, transparent BG.
- `<run-dir>/book/print/page-NN.png` — final 300 DPI canvases at A4P (2480×3508) or A3L (4961×3508).
- `<run-dir>/book/print/page-NN.txt` — sidecar with the book voice copy.

## Checklist (TodoWrite)

1. **Choose a run directory.** Pattern: `<output>/runs/YYYY-MM-DD-book-<topic-slug>-NN/`. If `<output>` is missing, halt and tell the user to run `/create-video-setup` first (the standalone book run still needs the same `.config/` keys).
2. **Mini-brief.** Ask the user for topic, class level, language, style. Write `<run-dir>/brief.json` with `{ topic, class_level, language, style, book_only: true }`. (Most video brief fields are skipped — character_mode, aspect, duration, etc. are not needed.)
3. **Collect source content.**
   - Ask if they have chapter text or reference material. Accept paste / file path / URL.
   - Save text to `<run-dir>/source/chapter.txt`.
   - For reference images, ask for file paths and copy each into `<run-dir>/sources/img-NN.png` (PNG-normalize via Pillow if needed).
   - At least one source (text OR images) is required. Both are recommended.
4. **Pick page count + templates.**
   - Ask "how many pages? (1–12)" — default to 6 if unclear.
   - Show the user the 9 templates with their content_type and best_ref preview path from [seed/template-references/manifest.json](../../seed/template-references/manifest.json). Help them pick by content type:
     - narrative scenes → full-bleed-with-text-zone, split-layout, illustrated-border
     - educational → scattered-spots, connected-infographic
     - character intros → vignette-on-page, character-text-pocket
   - Templates can repeat across pages — pick the BEST per page, not unique.
5. **Plan each page (chat-driven).** For each page, gather:
   - Template id.
   - Scene description (you draft from chapter text + page intent; user tweaks).
   - Book voice copy (the text that will be printed on the page, drafted in the chosen voice style — storybook narrator, factual calm, playful rhyming).
   - Content refs (which uploaded reference image(s) to send to gpt-image-2 as IMAGE 2 — usually 1 per page).
   - Character refs (optional — if the user uploaded a character sheet, attach it for consistency).
6. **Compose `<run-dir>/book/plan.json`** and surface it to the user before invoking the renderer. Schema:
   ```jsonc
   {
     "title": "Photosynthesis",
     "art_style": "watercolour",
     "voice": "storybook_narrator",
     "character_refs": ["sources/character-sheet.png"],   // optional, applies to every page
     "pages": [
       {
         "page_no": 1,
         "template": "full-bleed-with-text-zone",
         "scene_description": "A child stares at a wilted plant in a dark room, late afternoon light barely reaching the windowsill.",
         "book_voice_copy": "The little plant began to droop. It wondered: where had the sun gone?",
         "content_refs": ["sources/img-01.png"],
         "character_refs": []                              // optional per-page additions
       },
       ...
     ]
   }
   ```
7. **Render** with the standalone runner. It calls the shared two-image-prompting renderer for every page; auto-invokes print-prep with `--run-print-prep`:
   ```bash
   "$OUTPUT/.venv/bin/python" -m scripts.phase_book_standalone \
       --run-dir "$RUN_DIR" --run-print-prep
   ```
8. **Surface outputs.** Walk through `book/print/page-NN.png` files (clickable paths) and the sidecar `.txt` files.
9. **On feedback** — edit `book/plan.json` in place and re-run the runner. It overwrites `book/pages/page-NN.png` and `book/print/page-NN.png` per page.

## Reference templates (preview before picking)

The 9 templates and their best-ref images are in [seed/template-references/manifest.json](../../seed/template-references/manifest.json). When asking the user to pick templates, show them the `best_ref` file path for each so they can preview the layout exemplar in their file browser:

```
1. full-bleed-with-text-zone   seed/template-references/full-bleed-with-text-zone/ref_06_jungle-boy-text-left.jpg
2. vignette-on-page             seed/template-references/vignette-on-page/ref_01_lucy-mouse-soft-vignette.jpg
... etc ...
```

## Quality bar

- Every page in plan.json has `template`, `scene_description`, `book_voice_copy`, and at least one `content_refs` entry (the user uploaded at least one reference image, OR the chapter text is rich enough that the planner can defer to it — in which case the scene_description must be especially detailed because there's no IMAGE 2 visual anchor).
- Every `template` is one of the nine valid ids.
- `book_voice_copy` is in the chosen voice (storybook narrator / factual calm / playful rhyming), not the chapter text verbatim.
- After the runner completes, `book/print/page-NN.png` exists for every page at the correct canvas dimensions (A4P 2480×3508 or A3L 4961×3508).

## Common failure modes

- **Skipping the source-content collection step.** gpt-image-2 will hallucinate without reference images or strong chapter grounding. Always require at least one source.
- **Picking templates that don't match content type.** Educational topics in `full-spread-no-text` produce text-zoneless pages with no place for explanations. Use the content_type guidance from the manifest.
- **Mixing this skill with the video book branches on the same run.** Don't. Pick one entry point per run.
- **Using `book-only: false` accidentally.** Standalone runs MUST have `brief.book_only: true` so the orchestrator (if invoked) doesn't try to enter video phases.

## References

- [seed/template-references/manifest.json](../../seed/template-references/manifest.json) — template metadata + best-ref paths + content-type → templates mapping.
- [skills/book-plan/references/templates.md](../book-plan/references/templates.md) — per-template prompt patterns (now consumed by the shared renderer in scripts/lib/book_layout_renderer.py).
- [scripts/lib/book_layout_renderer.py](../../scripts/lib/book_layout_renderer.py) — the shared renderer used by every book path.
