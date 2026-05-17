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

## Split-screen / side-by-side compositions

Split-screen scenes (before/after, A vs B, then vs now, contrast pairs) follow a strict orientation rule keyed to the canvas aspect. The rule is embedded in `KEYFRAME_PROMPT` and `CLIP_PROMPT` and must stay consistent across keyframe → clip → re-prompts.

| Canvas | Split direction | Reasoning |
|---|---|---|
| **16:9** (horizontal) | Vertical line down the middle — **left ⎮ right** halves | Wide canvas wastes space if stacked; eye scans L→R naturally |
| **9:16** (vertical) | Horizontal line across the middle — **top ▬ bottom** halves | NEVER split a 9:16 frame vertically — it produces two unreadably narrow strips. Mobile users hold the phone upright; top/bottom reads naturally. |
| **1:1** | Prefer top/bottom; left/right acceptable | Either works; consistency within the run matters more than which one |

The same rule applies to clip generation — a beat that's a "still keyframe with subtle motion" must inherit the keyframe's split orientation. The auto-corrective Gemini analysis flags violations as `regen_recommendation: minor` with addendum like *"reorient split to horizontal for 9:16 aspect"*.

## Structured anchors (storyboard.json → clip prompts)

When a scene has multiple labelled elements with a fixed spatial relationship (e.g. *HERBA / leaf-icon on the left, CARNI / meat-icon on the right*), free-form prose in the `visual` hint is not enough — i2v models reliably swap them. Storyboard entries should carry an explicit `anchors` array that `phase_clips.py` reads and bakes into the clip generation prompt.

### Schema

```jsonc
{
  "id": 4,
  "label": "comparison",
  "prompt": "…",
  "image_path": "…/beat_04.png",
  "analysis_path": "…/beat_04.json",
  "anchors": [
    {"element": "leaf-icon",         "side": "left",  "label": "HERBA"},
    {"element": "meat-cut icon",     "side": "right", "label": "CARNI"}
  ]
}
```

- `element` — short concrete description (what the asset is)
- `side` — one of `left | right | top | bottom | center`
- `label` — the on-screen text/word that goes WITH that element (optional)

### When to author anchors

- Any beat with two or more nameable elements that share a spatial axis.
- Any before/after or A-vs-B comparison.
- Any beat where the visual hint says "X on the left, Y on the right" (even just in prose — promote it to anchors).

### What the runner does with them

`phase_clips.py` builds an `ANCHORS` block prepended to the clip prompt:

```
ANCHORS (lock these in place for the full clip):
  - leaf-icon on the LEFT side (label: "HERBA")
  - meat-cut icon on the RIGHT side (label: "CARNI")
```

The clip prompt's *SPATIAL ANCHORING* rule forbids swapping sides or detaching labels for the full clip duration. The structured anchors also flow into the validation prompt template so the per-clip QA pass checks for swaps.

## Anti-pattern checklist

- Do not request "cinematic lens flare" — it produces unreadable thumbnails.
- Do not put narration into the prompt verbatim; describe the **action**, not the words.
- Do not request multiple compositions in one beat ("then she turns and …") — that's two beats.
