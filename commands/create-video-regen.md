---
description: Targeted regeneration. Usage — /create-video-regen clip 3, /create-video-regen storyboard beats 5-7, /create-video-regen script.
---

# /create-video-regen

Parse the user's argument into a regeneration target:

- `script` → re-run `script-writer`
- `vo` → re-run `vo-generator`
- `characters` → re-run `character-sheet-generator`
- `storyboard` (optional `beats N-M`) → re-run `storyboard-generator` for the specified beats (or all)
- `clip N` or `clips N-M` → re-run `clip-generator` for the specified clips
- `stitch` → re-run `stitcher` only

Always:
1. Append a `gate_review_comments`-shaped entry to `run.json` capturing the user's feedback text.
2. POST the entry to VPS `/gates`.
3. Pass the comment text as a corrective prompt addendum to the relevant skill.
4. After regen, surface artifact paths in chat and wait for `approve` / further `regen`.
