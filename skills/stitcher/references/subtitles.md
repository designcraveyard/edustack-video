# Subtitles

Generated from `vo_timeline.json` by `scripts/make_subtitles.py`.

## Chunking rules

- Max 7 words OR 3 seconds per line, whichever comes first.
- Always break at punctuation (`.`, `?`, `!`, `,`).
- Never split a multi-word proper noun across lines.
- Minimum line duration: 800ms (re-merge tiny dangling words backward).

## SRT format

```
1
00:00:00,230 --> 00:00:02,180
How do leaves eat sunlight?

2
00:00:05,120 --> 00:00:07,440
Leaves are tiny food factories.
```

## Burn-in style

Default style applied in MoviePy (`final_subtitled.mp4`):

| Property | Value |
|---|---|
| Font | Inter Bold (or first Devanagari font found, for Hindi) |
| Size | 48 px @ 1080p, 64 px @ 1440p |
| Color | `#FFFFFF` |
| Stroke | 3 px `#000000` |
| Position | Bottom-center, 8% margin |
| Background | None (rely on stroke for legibility) |

For Hindi: use `Mukta-Bold` or `NotoSansDevanagari-Bold` (bundled in `vps/app/fonts/` and copied to `<run-dir>/.fonts/` at first run).

## Off-mode

If `brief.subtitles_enabled == false`, skip subtitle rendering entirely — only `final.mp4` is produced.
