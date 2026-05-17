---
name: brief-collector
description: Use when a run is missing brief.json. Spins up a localhost HTML form server on a random port, opens the browser, waits for submit, then exits cleanly.
---

# Brief Collector

Loads the form options seeded from Edustack (72 dropdown values across topic / style / language / voice combos) and collects a structured `brief.json` matching the Edustack `runs.brief` shape (so we can later cross-port projects between platforms).

## Checklist (TodoWrite)

1. Determine `<run-dir>` (passed by orchestrator).
2. If `<run-dir>/brief.json` already exists → skip; tell orchestrator to continue.
3. Spawn the Node server: `node ${CLAUDE_PLUGIN_ROOT}/skills/brief-collector/server/server.mjs --run-dir <run-dir>`.
4. Server binds `127.0.0.1:0`, prints `http://127.0.0.1:PORT`, opens browser (`open` / `xdg-open`).
5. User fills + submits form. Server writes `<run-dir>/brief.json`. For `script_mode: word_to_word`, server also saves the uploaded chapter to `<run-dir>/source/chapter.<ext>`.
6. Server prints `BRIEF_OK` to stdout and exits 0.
7. Return control to orchestrator.

## Form fields

See @references/brief-schema.md for the full schema. Headline fields:

- `topic`, `class_level`, `language`, `style`, `aspect`
- `script_mode` (standard / word_to_word) — toggles `chapter_source` (file/text/url) vs `duration_seconds`
- `character_mode` (human / abstract / none) — controls whether Phase 3a runs
- `image_mode` (storyboard_panel / per_keyframe) — controls Phase 3b backend
- `ambient_category`, `subtitles_enabled`, `annotations_enabled`, `voice_id`, `notes`

## Failure modes

- Port bind fails → retry with another random port (3 tries) then error out.
- User closes browser without submit → server keeps listening; orchestrator prints a hint to re-open the URL.
- Chapter upload too big (>20 MB) → 413 from server; UI shows error.
