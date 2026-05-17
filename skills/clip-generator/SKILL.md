---
name: clip-generator
description: Use during Phase 4 of a video run. Generates one Seedance 1.5 Pro i2v clip per beat, seeded by its keyframe. Runs Gemini frame-by-frame analysis to produce clip_N_analysis.json which feeds the stitcher.
---

# Clip Generator (Phase 4)

## Inputs

- `<run-dir>/storyboard/storyboard.json` (post-Gate-3 approved)
- `<run-dir>/storyboard/keyframes/beat_*.png`
- `<run-dir>/audio/vo_timeline.json` (per-beat durations)
- `<run-dir>/characters/*` (sheet OR description_block)

## Outputs

- `<run-dir>/clips/clip_N.mp4` — one per beat, duration = `vo_timeline.beats[N].duration_ms`
- `<run-dir>/clips/clip_N_analysis.json` — frame-by-frame continuity report

## Checklist (TodoWrite)

1. **Author per-clip validation prompts FIRST.** For every beat that will produce a clip, write `<run-dir>/clips/clip_<NN>.validation.txt` (zero-padded, e.g. `clip_03.validation.txt`). This file is your frame-by-frame articulation of what the clip should contain and what to audit — see @references/clip-validation-prompts.md for the meta-template. The Python runner passes the file verbatim to the QA endpoint; if the file is missing, a generic fallback runs (lower quality). Always author before generation, even though you haven't seen the clip yet — the validation prompt is your *expectation*, not a reaction.

2. **Invoke `phase_clips.py` — do NOT call fal inline.** This is the canonical path. The script:
   - reads storyboard.json (incl. structured `anchors`)
   - uploads each keyframe via `fal_client.upload_file()` (NOT a stale CDN URL)
   - calls Seedance with `resolution: "1080p"` (NOT `aspect_ratio`)
   - runs the Claude-authored validation prompt through `fal-ai/openrouter/router/video`
   - retries up to 2× with corrective addenda
   - saves zero-padded `clip_NN.mp4` + `clip_NN_analysis.json`

   ```bash
   "$OUTPUT/.venv/bin/python" -m scripts.phase_clips --run-dir "$RUN_DIR"
   ```

   Inline `fal_client.subscribe` calls are forbidden — they skip retry logic, anchor injection, and validation-prompt loading, and produce non-zero-padded filenames that break the stitcher.

3. **Auto-correct** (handled inside `phase_clips.py`, max 2 retries per clip):
   - When analysis flags character drift, anatomy issues, or anchor swaps, the script appends a corrective addendum and regenerates.
   - You may rewrite `clips/clip_<NN>.validation.txt` between human-driven `/create-video-regen` calls to tighten checks; the script reads the latest version on each run.
   - If still flagged after 2 tries → `needs_review: true` lands in the summary and Gate 4 surfaces.

4. Surface for Gate 4.

## Analysis schema

See @references/clip-validation-prompts.md.

## References

- @references/clip-prompting.md
- @references/clip-validation-prompts.md
- @references/transitions.md (transition cues to plan ahead for stitcher)
