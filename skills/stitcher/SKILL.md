---
name: stitcher
description: Use during Phase 5 of a video run. Composes final.mp4 and final_subtitled.mp4 from clips, full-vo.mp3, ambient audio, and clip analyses using MoviePy. VO-driven cut points. Transitions must be picked per-beat from clip analyses — uniform hard cuts are unacceptable output.
---

# Stitcher (Phase 5)

## Inputs

- `<run-dir>/clips/clip_*.mp4` + `clip_*_analysis.json` (motion intensity, scene change flags, drift findings)
- `<run-dir>/audio/full-vo.mp3` + `vo_timeline.json` (word-level alignment; VO-driven cuts read from `words[].end_ms` at beat boundaries)
- `<run-dir>/audio/ambient/*.mp3` (per `brief.ambient_category`)
- `<run-dir>/brief.json` — `aspect`, `subtitles_enabled`, `ambient_category`
- `<run-dir>/storyboard/storyboard.json` — transition cues from beat metadata
- `<run-dir>/script.md` — Scene Timeline rows specify intended Transition In / Transition Out per scene (use as planning input; clip analyses can override)

## Outputs

- `<run-dir>/stitch_plan.json` — the plan computed in step 1 (per-clip transitions, retiming, audio mix)
- `<run-dir>/final.mp4`
- `<run-dir>/final_subtitled.mp4` (when `brief.subtitles_enabled`)

## HARD REQUIREMENT: per-beat transition reasoning

Stitching is not concatenation. Every cut between clips must be a deliberate transition pick driven by:

1. The intended transition from `script.md` Scene Timeline (`Transition In` / `Transition Out` columns).
2. The actual `motion_intensity` and `scene_change` flags from `clip_NN_analysis.json`.

Picking "cut" for every clip is the lazy default and produces choppy output — the dominant pre-0.4.1 stitcher failure. Apply the transition rules table:

| Outgoing clip says... | Incoming clip says... | Pick |
|---|---|---|
| `motion_intensity: high` | `motion_intensity: high` | `cut` (preserve momentum) |
| `motion_intensity: high` | `motion_intensity: calm` | `dissolve` 240–360ms (release tension) |
| `motion_intensity: calm` | `motion_intensity: high` | `whip_pan` or fast `cut` (energy launch) |
| `motion_intensity: calm` | `motion_intensity: calm` | `dissolve` 240ms (gentle transition) |
| Scene change > 50% (per analysis) | — | `dissolve` or `whip_pan`, never raw cut |
| Same characters, different position | — | `match_cut` |
| Recap or final beat | — | `dissolve` 360ms in, `fade_to_black` out |

When `script.md`'s Scene Timeline names a transition explicitly (e.g. `[0:22] Cross-dissolve → Scene 3`), use it — the script author had a reason. Override only when the clip analysis contradicts (e.g. analysis says high-motion outgoing but script says dissolve — flag and ask).

**Plan diversity check**: in the final `stitch_plan.json`, if more than 60% of transitions are `cut`, the plan is too uniform. Revisit — likely you didn't read the clip analyses.

## Checklist (TodoWrite)

1. **Plan first, render second.** Build `stitch_plan.json` BEFORE invoking MoviePy. The plan is reviewable; bad renders are not. Each entry needs:
   - `clip_id`, `src`, `in_ms`, `out_ms`, `target_ms` (from `vo_timeline.beats[N].end_ms - start_ms`)
   - `retime_factor` when `clip != target` (±15% allowed; outside that range, escalate to Gate 4 — DON'T silently speed-shift)
   - `transition_in` and `transition_out` picked per the table above. Document the reasoning in a `transition_reasoning` field (one sentence — "outgoing calm, incoming high, whip pan").
2. **VO-driven cut points.** For each beat, the clip's `out_ms` = the last word's `end_ms` from `vo_timeline.json`, NOT the clip's natural end. This single rule keeps voice/visual sync regardless of clip retiming.
3. **Audio mix plan.** VO at –16 LUFS, ambient at –24 LUFS, duck ambient to –30 LUFS during VO speech (detect via `vo_timeline.words` gap analysis). Ambient track per `brief.ambient_category` from `<run-dir>/audio/ambient/`.
4. **Subtitles plan.** When `brief.subtitles_enabled`, generate SRT from `vo_timeline.words` via `scripts/make_subtitles.py`. For non-Latin scripts, see [references/subtitles.md](./references/subtitles.md) for font + style rules.
5. **Compose** with MoviePy per [references/transitions-implementation.md](./references/transitions-implementation.md). Apply transitions exactly as planned. Letterbox/pillarbox to `brief.aspect` if needed.
6. Export `final.mp4` (h264, AAC, `+faststart`).
7. If `brief.subtitles_enabled`, render burned-in subtitles → `final_subtitled.mp4`.
8. **Validate**: `ffprobe` duration vs `vo_timeline.total_duration_ms` (±200ms). Audio peak < –1 dBFS. Subtitle frame coverage check (every spoken word has at least one frame of subtitle visible).
9. Log to Supabase `eduplugin_events` stream `stitch`. Mark run complete in `run.json`.

## Quality bar (self-check before exit)

- `stitch_plan.json` exists and was written BEFORE the render — not after as a post-hoc record.
- Every plan entry has `transition_in`, `transition_out`, AND `transition_reasoning`.
- No more than 60% of transitions are `cut`. If higher, the plan is too uniform — revisit.
- For each plan entry, `transition_reasoning` cites either the script's Scene Timeline value or the clip's `motion_intensity` / `scene_change` from its analysis.
- VO-driven cuts: every beat boundary in the plan matches a word boundary in `vo_timeline.json` (±20 ms tolerance for whisper alignment).
- Audio mix: VO at –16 LUFS ±1, ambient at –24 LUFS ±1, ducked during VO.
- `final.mp4` duration matches `vo_timeline.total_duration_ms` ±200 ms.
- If `subtitles_enabled`, `final_subtitled.mp4` exists and every word in `vo_timeline.words` is covered by at least one subtitle frame.

## Common failure modes (avoid)

- **Uniform hard cuts across the whole video.** Choppy, robotic. The transition-rules table exists to prevent this — use it.
- **Rendering before planning.** Means you can't review the plan. `stitch_plan.json` must be written and reviewable before MoviePy runs.
- **Clip-end-based cuts instead of VO-end-based cuts.** Breaks lip-sync / narration alignment. Always cut on `vo_timeline.words[N].end_ms`.
- **Silent retiming beyond ±15%.** Looks unnatural. Escalate to Gate 4 instead — the user can decide between regenerating the clip or accepting the retime.
- **Not ducking ambient during VO.** VO becomes muddy. Auto-duck per `vo_timeline.words` gap analysis.

## References

- [references/stitch-planning.md](./references/stitch-planning.md) — `stitch_plan.json` schema, transition rules table, retiming rules, VO-driven cut explanation.
- [references/transitions-implementation.md](./references/transitions-implementation.md) — MoviePy specifics for each transition kind.
- [references/subtitles.md](./references/subtitles.md) — SRT generation, burn-in styling, multilingual font selection.
