---
name: vo-generator
description: Use during Phase 2 of a video run. Generates the full voiceover from script.md via ElevenLabs (direct API, not via fal) and produces vo_timeline.json with word-level timestamps for the stitcher.
---

# Voiceover Generator (Phase 2)

## Inputs

- `<run-dir>/script.md`
- `<run-dir>/brief.json` (for `voice_id`, `language`, `ambient_category`)

## Outputs

- `<run-dir>/audio/full-vo.mp3` (mp3_44100_192)
- `<run-dir>/audio/vo_timeline.json` — see @references/timeline-spec.md

## Checklist (TodoWrite)

1. Strip frontmatter and visual-hint comments from `script.md`; keep narration only.
2. Insert SSML / audio tags only where they materially help (laugh, sigh, pause-2s). See @references/elevenlabs-best-practices.md.
3. Call `POST /v1/text-to-speech/{voice_id}` with `output_format=mp3_44100_192` and `with_timestamps=true`.
4. Save MP3. Parse the alignment payload into `vo_timeline.json` with: `words[]`, `beats[]` (computed from beat boundaries in the original script), `total_duration_ms`.
5. Validate: every beat from `script.md` is represented in `beats[]`. If word count drift > 5%, flag.
6. Log to VPS `/prompts`. POST the prompt + alignment summary.

## Word_to_word note

In `script_mode: word_to_word`, the `duration_seconds` in brief is overridden by the VO's actual length. Subsequent phases (storyboard, clips) read `vo_timeline.total_duration_ms` for timing.

## References

- @references/elevenlabs-best-practices.md
- @references/timeline-spec.md
