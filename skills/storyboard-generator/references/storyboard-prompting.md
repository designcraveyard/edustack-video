# Storyboard prompting

## Image aspect

**Always derived from `brief.aspect`** — never hardcode 16:9. Read sizes from `<output>/.config/models.yaml > aspect_sizes[brief.aspect]`. The full panel render and each sliced keyframe both inherit this aspect. Character sheets are the only exception (always 1:1, since they're a reference grid).

## Mode A — gpt-image-2 multi-panel sheet

A single prompt produces one PNG containing N panels (one per beat), then `extract_keyframes.py` slices it. The panel's outer aspect equals `brief.aspect`; the slicer computes rows × cols so each *cell* also matches `brief.aspect` (e.g. 9:16 → more rows than cols; 16:9 → more cols than rows).

```
Storyboard sheet, <N> panels in a <rows>x<cols> grid, each panel 16:9 with a thin white border.
Style: <brief.style>. Locked palette: <3-color hex list from characters/analysis.json>.

CHARACTERS (recurring across panels):
<characters/description_block.md OR a one-paragraph summary from characters/analysis.json>

PANELS:
1. <beat 1 narration> — <beat 1 visual hint>
2. <beat 2 narration> — <beat 2 visual hint>
...

Render: no text, no captions, no panel numbers. Each panel readable as a thumbnail. Aspect of the full sheet: <rows*9>:<cols*16>.
```

**Slicing:** `extract_keyframes.py` reads `panel.png` + the grid dimensions and outputs `beat_N.png` at 1920×1080 each.

## Mode B — Nano Banana 2 per keyframe

One call per beat. Use the character sheet as a `reference_image` if available.

```
Educational explainer keyframe. Style: <brief.style>. Aspect: <brief.aspect>.

CHARACTERS:
<characters/description_block.md OR character names + analysis description>

SHOT:
<beat narration in one sentence>. Visual: <beat visual hint>. Camera: <inferred camera, default "static medium">.
Composition: rule of thirds; reading direction left-to-right. Background: <inferred from style>.

Constraints: no text, no captions, no logos, no UI elements.
```

When `character_mode != none`, attach `characters/sheet.png` via `reference_image_urls` so Nano Banana conditions on character likeness.

## Locked palette rule

Always extract a 3-color hex palette from `characters/analysis.json` (or a synthesized one for `character_mode: none`) and force it into every prompt. Stops palette drift across beats.

## Anti-pattern checklist

- Do not request "cinematic lens flare" — it produces unreadable thumbnails.
- Do not put narration into the prompt verbatim; describe the **action**, not the words.
- Do not request multiple compositions in one beat ("then she turns and …") — that's two beats.
