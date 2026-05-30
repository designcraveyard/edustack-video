---
name: book-template-picker
description: Use whenever a book run needs the user to choose layout templates — the in-video book branch (Phase B1), /create-book (standalone), and /create-book-from-keyframes all call this. Opens a polished localhost gallery in the browser (the 9 book layouts with real reference images, descriptions, wireframes, and an orientation toggle), lets the user select 2–4, and writes the choice to a handshake JSON. Trigger phrases include "pick a template", "choose layout", "open the template picker", "which book layout", or any book path reaching its template-selection step.
---

# Book Template Picker (localhost gallery)

This skill opens a **localhost web gallery** so the user can browse and select book layout templates visually — instead of picking blind from text. It mirrors the layout-templates-web showcase: every template shows its real reference images (click to zoom), a description, a meta grid (text position / wrapping / background / aspect), a frequency bar, tags, and a wireframe that reframes with an orientation toggle.

It is the **single template-selection entry point** for every book path:

| Caller | Why it calls the picker |
|---|---|
| Phase B1 ([book-plan](../book-plan/SKILL.md)) — in-video book | Replaces / supplements the brief's template shortlist |
| [book-standalone](../book-standalone/SKILL.md) — `/create-book` | The standalone book run's template-selection step |
| [book-from-keyframes](../book-from-keyframes/SKILL.md) — `/create-book-from-keyframes` | The shortlist the user assigns keyframes against |

## How it works

The server is **zero-dependency Node stdlib** (same pattern as the brief-collector server). It binds `127.0.0.1:0` (random free port), opens the browser, serves the gallery, and **exits cleanly** once the user confirms — writing the selection to a handshake JSON file.

Reference thumbnails are served straight from the canonical `seed/template-references/` (no duplicated copy). Display metadata lives in [server/public/templates.json](server/public/templates.json) — the picker's display source of truth, kept in sync with the renderer's `seed/template-references/manifest.json` (template ids are identical across both).

## Launching it

```bash
node "${CLAUDE_PLUGIN_ROOT}/skills/book-template-picker/server/server.mjs" \
    --run-dir "$RUN_DIR" \
    --min 2 --max 4 \
    --page-count "$PAGE_COUNT" \
    --title "Pick layouts for your book"
```

- `--run-dir <path>` — default output becomes `<run-dir>/book/template-selection.json`.
- `--out <path>` — override the handshake path explicitly (use this if there's no run dir yet).
- `--min` / `--max` — selection bounds (default 2 / 4).
- `--page-count <n>` — prefill the page-count input (the user can change it).
- `--title <str>` — heading shown in the UI.

Run it and **wait for the line `PICKER_OK` on stdout**. Then read the handshake JSON:

```jsonc
// <run-dir>/book/template-selection.json
{
  "templates": ["split-layout", "scattered-spots", "vignette-on-page"],
  "page_count": 6,
  "mode": "shortlist",
  "ts": "2026-05-26T…"
}
```

Use `selection.templates` wherever a book path needs `book.templates` (the brief's shortlist, or to seed per-page assignment). Use `selection.page_count` if the user set it here rather than earlier.

## Checklist (TodoWrite)

1. **Decide the handshake path.** If you have a run dir, pass `--run-dir`; the file lands at `<run-dir>/book/template-selection.json`. Otherwise pass `--out`.
2. **Launch the server** (command above). It opens the browser automatically.
3. **Tell the user** in chat: "I've opened the layout picker in your browser — select 2–4 templates and hit Confirm." Include the `http://127.0.0.1:PORT/` line the server printed, in case the tab didn't auto-open.
4. **Wait for `PICKER_OK`.** The server exits on its own after writing the file.
5. **Read the handshake JSON** and carry `templates` (+ `page_count`) into the calling path's plan.
6. **Validate**: every returned id is one of the nine valid templates; count is within `[min, max]`. If the file is missing or empty (user closed the tab without confirming), fall back to the chat-based selection described in the calling skill.

## Fallback (no browser / headless)

If Node is unavailable, the user is on a headless box, or the picker is closed without confirming, fall back to **chat-driven selection**: present the nine templates with their `best_ref` preview paths from `seed/template-references/manifest.json` and let the user name them. The downstream contract (`templates` shortlist) is identical either way.

## The nine templates

`full-bleed-with-text-zone` · `vignette-on-page` · `split-layout` · `scattered-spots` · `full-spread-no-text` · `illustrated-border` · `character-text-pocket` · `connected-infographic` · `spread-scene-plus-spots`

Canvas, content-type, and best-ref for each are in [seed/template-references/manifest.json](../../seed/template-references/manifest.json); the human-facing descriptions and full reference-image lists are in [server/public/templates.json](server/public/templates.json).

## Common failure modes

- **Not waiting for `PICKER_OK`.** Reading the handshake JSON before the user confirms gets a stale or missing file. Always block on the stdout line.
- **Duplicating the reference images.** Don't copy `seed/template-references/` into this skill — the server serves them via `/refs/<path>`. The 5 MB lives in exactly one place.
- **Drifting template ids.** If you add or rename a template, update BOTH `seed/template-references/manifest.json` (renderer) AND `server/public/templates.json` (picker) — the ids must match.

## References

- [seed/template-references/manifest.json](../../seed/template-references/manifest.json) — renderer's canonical template metadata (canvas, content-type, best-ref).
- [server/public/templates.json](server/public/templates.json) — picker's display metadata (descriptions, tags, full ref lists, wireframes).
- [scripts/lib/book_layout_renderer.py](../../scripts/lib/book_layout_renderer.py) — where the chosen template's layout reference becomes IMAGE 1 in the two-image prompt.
