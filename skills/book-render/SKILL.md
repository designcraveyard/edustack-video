---
name: book-render
description: Phase B2 — render every page in book/plan.json via fal-ai/gpt-image-2 with transparent BG. Falls back to fal-ai/birefnet/v2 if the model returns an opaque background. Runs Gemini visual QA via fal-ai/any-llm/vision and retries up to 2 times per page on drift. Use when Gate B1 has been approved and book/plan.json exists.
---

# Phase B2 — Book Render

## Inputs
- `<run-dir>/book/plan.json` (Phase B1)
- `<run-dir>/storyboard/keyframes/beat_NN.png` (referenced by some plan entries)
- `<run-dir>/characters/sheet.png` and any other `characters/*.png` (referenced by every plan entry)

## Output (per page)
- `<run-dir>/book/pages/page-NN.png` — RGBA at gpt-image-2 native dims (e.g. 1024×1456 or 1456×1024)
- `<run-dir>/book/pages/page-NN.qa.json` — verdict + checks + attempt count + status

## Algorithm

For each page in `plan.json`:

1. Load the template prompt pattern from `skills/book-plan/references/templates.md`. Substitute `prompt_params` and `scene_prompt`. Append:
   ```
   Transparent background. Illustration only. The {text_zone_hint} region must
   be left fully transparent — no painted background, no parchment, no light
   wash. No text, no letters, no numbers anywhere in the image.
   ```
2. Build `image_urls` list (data-URIs, cap 4):
   - `<run-dir>/<keyframe_ref>` if present
   - up to 3 entries from `character_refs[]`
3. Call `FalClient.gpt_image_2_book_page(prompt, image_urls, size)` where `size` is `1024x1456` for A4P canvases, `1456x1024` for A3L canvases.
4. Download the result. Check transparency via border-alpha heuristic: if >2% of sampled border pixels are opaque, call `FalClient.birefnet_remove_bg(image_url=url)` and use that.
5. Save `book/pages/page-NN.png` (RGBA).
6. Call `VisualAnalyzer.analyse_book_page()`. If `verdict == NEEDS_REGEN` and retry count < 2, append the `corrective_addendum` to the prompt and re-render. After 2 failed retries, write `qa.json` with `status: failed` and continue (do not block the rest of the book).
7. Save the final QA result as `book/pages/page-NN.qa.json`.

No chat gate here. Failed pages surface in the run summary; users can regen via `/create-book-regen page-NN`.

## Invocation
```
python3 -m scripts.phase_book_render --run-dir <run-dir> [--only-page <N>]
```

## References
- @references/qa-prompt.md — the QA prompt fields and verdict logic
