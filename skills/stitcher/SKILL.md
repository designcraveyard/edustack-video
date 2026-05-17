---
name: stitcher
description: Use during Phase 5 of a video run. Composes final.mp4 and final_subtitled.mp4 from clips, full-vo.mp3, ambient audio, and clip analyses using MoviePy. VO-driven cut points.
---

# Stitcher (Phase 5)

## Inputs

- `<run-dir>/clips/clip_*.mp4` + `clip_*_analysis.json`
- `<run-dir>/audio/full-vo.mp3` + `vo_timeline.json`
- `<run-dir>/brief.json` (ambient_category, subtitles_enabled, aspect)
- `<run-dir>/storyboard/storyboard.json`

## Outputs

- `<run-dir>/stitch_plan.json` — the plan you computed (durations, cuts, transitions, audio mix)
- `<run-dir>/final.mp4`
- `<run-dir>/final_subtitled.mp4`

## Checklist (TodoWrite)

1. **Plan**: build `stitch_plan.json` from `vo_timeline.beats` × `clips`. Each entry: clip_id, in/out times, transition_in, transition_out, target_duration, retime_factor (if clip != target). Use clip analyses to pick transitions (cuts on motion boundaries, dissolves on calm sections). See @references/stitch-planning.md.
2. **Compose** with MoviePy per @references/transitions-implementation.md:
   - Concatenate clips with planned transitions.
   - Mix VO + ambient (ambient at –24 LUFS, VO at –16 LUFS).
   - Letterbox/pillarbox to `brief.aspect` if needed.
3. Export `final.mp4` (h264, AAC, +faststart).
4. If `brief.subtitles_enabled`, render burned-in subtitles via `scripts/make_subtitles.py` → export `final_subtitled.mp4`. See @references/subtitles.md.
5. Validate: ffprobe duration vs `vo_timeline.total_duration_ms` (±200ms). Audio peak < –1 dBFS.
6. POST `/heartbeat` `{status: "complete"}` to VPS. Mark run complete in `run.json`.

## References

- @references/stitch-planning.md
- @references/transitions-implementation.md
- @references/subtitles.md
