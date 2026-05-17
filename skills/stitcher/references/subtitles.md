# Subtitles

Generated from `vo_timeline.json` by `scripts/make_subtitles.py`.

## Language ↔ script policy

VO narration is rendered in **native script** (Devanagari, Tamil, Bengali) so ElevenLabs phonemizes correctly. Subtitles, however, are **transliterated to Latin** so learners and Hinglish viewers can read them. Transliteration happens per word inside the chunker (`scripts/make_subtitles.chunk_words`) so timing alignment to the audio is preserved.

| Language | VO narration | Subtitle text | Transliteration target |
|---|---|---|---|
| English | Latin | Latin | — (no change) |
| Hindi | Devanagari | Latin | ITRANS (e.g. "नमस्ते" → "namaste") |
| Hinglish | Devanagari + English | Latin | ITRANS per word; English words unchanged |
| Marathi | Devanagari | Latin | ITRANS |
| Tamil | Tamil script | Latin | IAST |
| Bengali | Bengali script | Latin | IAST |

Implementation: `scripts/lib/transliterate.to_latin(text, language)`. Uses the `indic-transliteration` package; falls back to a built-in Devanagari → ASCII table if the dep is missing.

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
