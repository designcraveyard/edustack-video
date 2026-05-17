# vo_timeline.json spec

The single source of truth for VO timing. Drives storyboard beat duration, clip target lengths, subtitle cues, and stitcher cut points.

```jsonc
{
  "total_duration_ms": 58_240,
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "language": "English",
  "words": [
    { "text": "Photosynthesis", "start_ms": 230, "end_ms": 1180 },
    { "text": "is",             "start_ms": 1200, "end_ms": 1310 }
  ],
  "beats": [
    { "id": 1, "label": "hook",  "start_ms": 0,     "end_ms": 5_120, "word_range": [0, 12] },
    { "id": 2, "label": "concept", "start_ms": 5_120, "end_ms": 18_400, "word_range": [12, 56] }
  ]
}
```

## Beat boundaries

Computed from `[BEAT N]` headers in `script.md`. Each beat's `start_ms` = first word's `start_ms`; `end_ms` = last word's `end_ms` of the beat.

## Subtitles

Generated from `words[]` by `scripts/make_subtitles.py` — chunk by punctuation, max 7 words / 3 seconds per line.
