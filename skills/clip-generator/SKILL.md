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

1. **Author per-clip validation prompts FIRST.** For every beat that will produce a clip, write `<run-dir>/clips/clip_<N>.validation.txt`. This file is your frame-by-frame articulation of what the clip should contain and what to audit — see @references/clip-validation-prompts.md for the meta-template. The Python runner passes the file verbatim to the QA endpoint; if the file is missing, a generic fallback runs (lower quality). Always author before generation, even though you haven't seen the clip yet — the validation prompt is your *expectation*, not a reaction.
2. For each beat in storyboard.json:
   1. Build the clip generation prompt per @references/clip-prompting.md (second-level action descriptions, camera notes, expected character behavior).
   2. If `character_mode == none`, prepend `characters/description_block.md` verbatim.
   3. Call `fal-ai/bytedance/seedance/v1.5/pro/image-to-video` with `image_url = keyframes/beat_N.png` and `duration = ceil(beat.duration_ms / 1000)`.
   4. Download MP4 → `clips/clip_N.mp4`.
   5. Video-native QA via `fal-ai/openrouter/router/video` (Gemini 2.5 Pro) using the Claude-authored `clip_N.validation.txt`. Saves `clip_N_analysis.json`. On router failure, contact-sheet fallback runs automatically.
3. **Auto-correct** (max 2 retries per clip):
   - If analysis flags character drift, anatomy issues, or motion mismatch, regen with corrective addendum.
   - On regen, you may also rewrite the per-clip `validation.txt` to tighten checks for the next attempt.
   - If still flagged after 2 tries → mark `needs_review: true` and let Gate 4 handle.
4. Surface for Gate 4.

## Analysis schema

See @references/clip-validation-prompts.md.

## References

- @references/clip-prompting.md
- @references/clip-validation-prompts.md
- @references/transitions.md (transition cues to plan ahead for stitcher)
