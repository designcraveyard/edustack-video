---
name: book-print-prep
description: Phase B3 — upscale every book/pages/page-NN.png to A4P (2480×3508) or A3L (4961×3508) transparent canvas at 300 DPI using template-specific composition rules. Writes to book/print/. Use after book-render completes.
---

# Phase B3 — Book Print Prep

## Inputs
- `<run-dir>/book/pages/page-NN.png` (Phase B2 output, RGBA at gpt-image-2 native dims)
- `<run-dir>/book/plan.json` (for `template` per page)

## Output (per page)
- `<run-dir>/book/print/page-NN.png` — A4P or A3L RGBA at 300 DPI
- `<run-dir>/book/print/page-NN.txt` — `book_voice_copy` for designer reference

## Algorithm

For each `book/pages/page-NN.png`:
1. Look up `template` from `book/plan.json`.
2. Call `book_canvas.compose(img, template)` — applies Lanczos resize, auto-level + unsharp on RGB channels (alpha preserved), and pastes onto the right canvas at the rule's prescribed position.
3. Save with `info["dpi"] = (300, 300)`.
4. Write sidecar `.txt` with `book_voice_copy` from the plan.

Pure Pillow. No ImageMagick. No external network calls. Deterministic.

## Invocation
```
python3 -m scripts.phase_book_print_prep --run-dir <run-dir> [--only-page <N>]
```
