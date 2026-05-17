---
name: create-book-regen
description: Regenerate one specific book page after Phase B3 completes. Useful when QA missed drift or the user wants a different template assignment.
argument-hint: <page-NN> [--template <template-id>] [--scene "<new scene prompt>"]
allowed-tools: Bash, Read, Edit, Glob, Grep
---

Regenerate a single book page.

**Arguments:**
- `<page-NN>` (required): the page number to regen, e.g. `page-04` or `4`.
- `--template <id>` (optional): override the template assignment for this page. One of:
  `full-bleed-with-text-zone`, `vignette-on-page`, `split-layout`, `scattered-spots`,
  `full-spread-no-text`, `illustrated-border`, `character-text-pocket`,
  `connected-infographic`, `spread-scene-plus-spots`.
- `--scene "<text>"` (optional): replace the page's `scene_prompt`.
- `--copy "<text>"` (optional): replace the page's `book_voice_copy`.

**Behavior:**

1. Resolve the current run-dir (active run from session state, or the user's `--run-dir`).
2. Read `<run-dir>/book/plan.json`. Parse `<page-NN>` to an integer N (strip `page-` prefix and leading zeros).
3. If `--template`, `--scene`, or `--copy` are given, edit the matching entry in `plan.json` (update `template`, `canvas` via book_canvas.canvas_for, `scene_prompt`, `book_voice_copy`).
4. Run `python3 -m scripts.phase_book_render --run-dir <run-dir> --only-page <N>`.
5. Run `python3 -m scripts.phase_book_print_prep --run-dir <run-dir> --only-page <N>`.
6. Report the new file paths: `<run-dir>/book/print/page-NN.png` and the QA verdict from `<run-dir>/book/pages/page-NN.qa.json`.

**Examples:**

```
/create-book-regen page-04
/create-book-regen 4 --template vignette-on-page
/create-book-regen page-07 --scene "The hare watching the tortoise plod past, autumn leaves drifting"
/create-book-regen 02 --copy "And the small green helpers worked, hour by hour."
```

**Notes:**
- Template change auto-updates the page's `canvas` (A4P for 3:4 templates, A3L for 16:9). Done by reading `RULES[template].canvas` from `scripts/lib/book_canvas.py`.
- The print-prep step is fast (Pillow only). The expensive step is `phase_book_render.py`'s gpt-image-2 call + QA loop (~$0.05–0.15 + 30–60s per page).
