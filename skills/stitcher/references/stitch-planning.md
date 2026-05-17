# Stitch planning

The stitcher reads `clip_*_analysis.json` (not the raw clips) to compute cut points and transitions. Output is `stitch_plan.json`.

## stitch_plan.json shape

```jsonc
{
  "total_duration_ms": 58_240,
  "clips": [
    {
      "clip_id": 1,
      "src": "clips/clip_01.mp4",
      "in_ms": 0,
      "out_ms": 5_120,
      "target_ms": 5_120,
      "retime_factor": 1.0,
      "transition_in": { "kind": "cut" },
      "transition_out": { "kind": "dissolve", "duration_ms": 240 }
    }
  ],
  "audio": {
    "vo": { "src": "audio/full-vo.mp3", "level_lufs": -16 },
    "ambient": { "src": "ambient/calm.mp3", "level_lufs": -24, "duck_to_lufs": -30, "duck_during_vo": true }
  },
  "subtitles": {
    "enabled": true,
    "srt": "audio/subtitles.srt",
    "burn_in": true,
    "style": { "font": "Inter Bold", "size_px": 48, "stroke_px": 3 }
  }
}
```

## Transition rules (derived from clip analyses)

| Clip analysis says | Transition_out |
|---|---|
| `motion_intensity: high` and next clip also high | `cut` |
| `motion_intensity: calm` or `recap` beat | `dissolve` (240ms) |
| Scene change > 50% | `whip_pan` (180ms, direction inferred from analysis) |
| Same characters, different position | `match_cut` |

## Retiming

If `out_ms - in_ms != target_ms` and the delta is within ±15%, MoviePy `speedx` to fit. If delta > 15%, regenerate the clip (escalate to gate).

## VO-driven cut points

For each beat, the cut happens on the last word's `end_ms` from `vo_timeline.json`, not the clip's natural end. This is the single most important rule — it guarantees voice/visual sync regardless of clip retiming.
