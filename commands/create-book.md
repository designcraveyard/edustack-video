---
description: Create a print-ready children's picture book without making a video first — chapter text + reference images go straight to layout-faithful book pages at A4P/A3L 300 DPI.
---

# /create-book

Standalone video-less book run. Use when the user wants a book directly — no Phase 1–5, no video output. The book skill walks them through a mini-brief (topic, class, language, style), source content collection (chapter text + reference images), template picking from the 9 layouts, and per-page planning. Then the shared two-image-prompting renderer produces each page via fal-ai/gpt-image-2 at native A4P (1024×1456) or A3L (1456×1024), and the Pillow composer upscales to the final 300 DPI canvases (A4P 2480×3508 or A3L 4961×3508).

**Invoke the `book-standalone` skill immediately.** It will:

1. Verify `<output>/.config/` exists — halt and direct to `/create-video-setup` otherwise (the standalone book run shares the same keys).
2. Pick a fresh run directory (pattern: `<output>/runs/YYYY-MM-DD-book-<topic-slug>-NN/`).
3. Collect mini-brief (topic, class, language, style) → `brief.json`.
4. Collect source content: chapter text saved to `source/chapter.txt`, reference images copied into `sources/`.
5. Pick page count, then open the **localhost template picker** (`book-template-picker`) — a browser gallery of the 9 layouts with real reference images, descriptions, and wireframes — and select 2–4. Falls back to chat-based picking if no browser is available.
6. Plan each page in chat — template, scene description, book voice copy, which content refs to use.
7. Run `scripts.phase_book_standalone` with `--run-print-prep` to render every page and produce the final 300 DPI canvases.
8. Surface clickable paths to `book/print/page-NN.png` + sidecar `.txt` for designer handoff.

For users who DO want a video first AND a book afterwards, direct them to `/create-video` with `brief.book.page_count_target > 0` instead. For users who already have a finished video and want the book to reuse the keyframes, direct them to `/create-book-from-keyframes`.
