---
name: orchestrator
description: Use when starting or resuming an educational-video run (/create-video, /create-video-resume). Owns the 5-phase pipeline, the 4 review gates, and per-run state. Routes to per-phase skills.
---

# Orchestrator

The single owner of an `edustack-video` run. Reads + writes `<run-dir>/run.json`. Never generates content itself — always routes to a per-phase skill.

## When to use

- `/create-video` (new run)
- `/create-video-resume` (resume after interruption)
- `/create-video-regen <target>` (selective regen)

## Pre-flight checklist (TodoWrite)

1. Verify `<output>/.config/` exists. If not → halt; tell user to run `/create-video-setup`.
2. Compute or pick the run directory. Pattern: `<output>/runs/YYYY-MM-DD-<topic-slug>-NN`.
3. If `<run-dir>/run.json` missing → create empty state. If present → load.
4. If `<run-dir>/brief.json` missing → invoke `brief-collector` skill.
5. From `run.json.next_phase`, invoke the corresponding skill.
6. After each phase: write `phase_completed` to `run.json`, surface artifact paths in chat, and (unless this is a no-gate phase) **stop** and wait for the user.
7. Parse user reply: `approve` → advance; `regen ...` → invoke `/create-video-regen` flow; anything else → ask for clarification.

## Phase routing

| Brief field check | Skill invoked |
|---|---|
| no `script.md` | `script-writer` |
| no `audio/full-vo.mp3` | `vo-generator` |
| `character_mode != none` and no `characters/sheet.png` (or missing `characters/descriptions.json`) | `character-sheet-generator` (gpt-image-2 rich sheet + descriptions.json) |
| `character_mode == none` and no `characters/description_block.md` | `character-sheet-generator` (writes block, exits) |
| no `storyboard/storyboard.json` | `storyboard-generator` |
| any `clips/clip_*.mp4` missing | `clip-generator` |
| no `final.mp4` | `stitcher` |

## State shape — `run.json`

```json
{
  "run_id": "2026-05-17-photosynthesis-01",
  "status": "running",
  "next_phase": "storyboard",
  "phases": {
    "script": { "status": "approved", "completed_at": "...", "gate_comments": [] },
    "vo": { "status": "approved", "completed_at": "...", "gate_comments": [] }
  },
  "items": {
    "clips": [{ "id": 1, "status": "complete" }, { "id": 2, "status": "regen_requested", "comment": "motion too fast" }]
  }
}
```

## Gate UX

Each gate message in chat **must include**:
- Bullet list of file paths (one per line, no prose around them — Claude Code linkifies paths).
- The exact reply forms accepted: `approve`, `regen <target>: <comment>`.
- A pointer to `/create-video-regen` if the user wants to invoke regen via slash command.

## Book branch (post-video, optional)

If `brief.book.page_count_target > 0`, after Phase 6 (stitch) completes, run three additional phases serially:

1. **Phase B1 — book-plan** (`scripts/phase_book_plan.py`). Invoke the `book-plan` skill to author the page list and book-voice copy, then run the script to serialize. Surface **Gate B1** in chat with a Markdown summary of `book/plan.json`. Accept `approve` / `regen page N: <comment>` / `regen all`.
2. **Phase B2 — book-render** (`scripts/phase_book_render.py`). Invoke the `book-render` skill. fal-ai/gpt-image-2 with transparent BG, birefnet/v2 fallback, Gemini visual QA via fal-ai/any-llm/vision. Up to 2 retries per page. Failed pages don't block the rest.
3. **Phase B3 — book-print-prep** (`scripts/phase_book_print_prep.py`). Pure Pillow, no LLM. Composes per-template onto A4P (2480×3508) or A3L (4961×3508) transparent canvas at 300 DPI.

See `@references/book-routing.md` for the full gate contract and per-page regen path (`/create-book-regen`).

## What this skill does NOT do

- Does not call fal.ai / ElevenLabs / Gemini. That's the per-phase skill's job.
- Does not parse the brief schema. That's `brief-collector`.
- Does not render UI. Chat-only.
