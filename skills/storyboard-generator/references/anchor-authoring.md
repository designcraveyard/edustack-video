# Anchor authoring — split-screen and two-element scenes

## Why anchors exist

Image-to-video models (Seedance, Wan 2.7, etc.) reliably swap sides during clip generation when a beat has two named elements with a spatial relationship — left vs right, top vs bottom, before vs after. The canonical failure: a "herbivore on the LEFT, carnivore on the RIGHT" comparison beat where the keyframe is correct but the i2v clip ends with carnivore on the left. The anchor system locks the spatial constraint by passing structured metadata from the storyboard's `anchors[]` into the clip-generator's prompt at generation time.

**No anchors → spatial drift in clips.** This is not "best practice" — it's the difference between a comparison scene working and not working.

## When does a beat need anchors?

A beat needs anchors when its visual hint mentions **two or more named elements** in a fixed spatial position. Flowchart:

```
Does the beat's visual hint name 2+ specific elements?
├── No → no anchors needed
└── Yes
    │
    Does at least one element have a position word
    (left, right, top, bottom, foreground, background, before, after, center)?
    ├── No → no anchors needed (camera will compose freely)
    └── Yes → AUTHOR ANCHORS for every positioned element.
```

Trigger phrases that should always produce anchors:

- "X on the left, Y on the right"
- "before vs after"
- "compare A and B"
- "the {object} sits between them"
- "X stays in the foreground while Y is in the background"
- "X above, Y below"
- "split-screen / divided / two halves"
- Labels next to specific elements: `"HERBIVORE"` next to one animal, `"CARNIVORE"` next to another

## Anchor schema

In `storyboard.json`, each beat may carry an optional `anchors[]` array:

```jsonc
{
  "beats": [
    {
      "id": 3,
      "label": "comparison",
      "anchors": [
        {
          "element": "rabbit eating grass",
          "side": "left",
          "label": "HERBIVORE"
        },
        {
          "element": "lion mid-pounce",
          "side": "right",
          "label": "CARNIVORE"
        }
      ]
    }
  ]
}
```

Fields:

| Field | Type | Notes |
|---|---|---|
| `element` | string | What the element IS — concrete noun phrase. Don't write "thing on left"; write "rabbit eating grass". |
| `side` | enum | One of: `left` `right` `top` `bottom` `center` `foreground` `background`. Lower-case. |
| `label` | string (optional) | The text label that should appear WITH the element. Empty string if no label. The label is locked to the element — labels don't detach. |

Aspect-ratio rules:

- `16:9` (horizontal canvas) — split VERTICALLY into `left | right`. Never use `top` / `bottom` for split-screens in 16:9.
- `9:16` (vertical canvas) — split HORIZONTALLY into `top` / `bottom`. **Never split a 9:16 frame down the middle vertically** — the elements end up paper-thin and unreadable.
- `1:1` — prefer `top` / `bottom`.
- `foreground` / `background` work for all aspects (Z-axis, not X/Y).

## Good vs bad examples

### ✅ Good — herbivore/carnivore comparison (16:9)

Visual hint: *"A green field divides the frame down the middle. LEFT side: rabbit eating grass, labeled HERBIVORE. RIGHT side: lion mid-pounce, labeled CARNIVORE."*

```json
"anchors": [
  { "element": "rabbit eating grass", "side": "left", "label": "HERBIVORE" },
  { "element": "lion mid-pounce", "side": "right", "label": "CARNIVORE" }
]
```

The clip-generator bakes this into the i2v prompt as:

```
ANCHORS (lock these in place for the full clip):
  - rabbit eating grass on the LEFT side (label: "HERBIVORE")
  - lion mid-pounce on the RIGHT side (label: "CARNIVORE")
```

— and the QA pass flags any frame where the elements have swapped sides.

### ✅ Good — before/after (9:16)

Visual hint: *"Top half: wilted plant. Bottom half: same plant healthy and green."*

```json
"anchors": [
  { "element": "wilted plant", "side": "top", "label": "BEFORE" },
  { "element": "healthy green plant", "side": "bottom", "label": "AFTER" }
]
```

### ✅ Good — foreground/background

Visual hint: *"A telescope sits in the foreground, the moon glows in the background."*

```json
"anchors": [
  { "element": "brass telescope", "side": "foreground" },
  { "element": "full moon glowing", "side": "background" }
]
```

(No labels needed when the scene has no text overlays.)

### ❌ Bad — vague elements

```json
"anchors": [
  { "element": "thing on left", "side": "left" },
  { "element": "the other one", "side": "right" }
]
```

The model can't lock identity on "thing." Be specific.

### ❌ Bad — 9:16 vertical split

```json
"anchors": [
  { "element": "rabbit", "side": "left" },
  { "element": "lion", "side": "right" }
]
```

In a 9:16 (1080×1920) canvas, a vertical left/right split gives each element a strip ~540 px wide × 1920 tall — paper-thin, unreadable on phones. Use `top` / `bottom` for 9:16.

### ❌ Bad — anchors without trigger

Beat visual hint: *"A child looks at a tree growing in the sunlight."*

This is a single subject, no spatial relationship between named elements. No anchors needed. Don't author anchors just because you can — they constrain the model and can over-rigidify the camera.

## What the clip-generator does with anchors

[scripts/phase_clips.py:`_anchors_block()`](../../../scripts/phase_clips.py) reads `storyboard.json` and, for any beat with an `anchors[]` entry, injects an ANCHORS block into the i2v prompt verbatim. The Claude-authored `clip_NN.validation.txt` should also reference these anchors in its QA checks (check 7 in the meta-template) so the auditor flags any frame where the anchored element has drifted off its named side.

## Authoring during phase_storyboard

The Python runner ([scripts/phase_storyboard.py](../../../scripts/phase_storyboard.py)) does **not** infer anchors from the visual hint — Claude must author them and write them into `storyboard.json` either before the runner is invoked, or as part of the runner's per-beat output (the storyboard skill writes the beat metadata). If you skip authoring, anchors won't appear and the clip-generator will run without spatial constraints.

## Anti-patterns

- Skipping anchors for split-screen beats because "the keyframe already shows the layout." The keyframe is one frame; the i2v model has 30+ frames to drift across.
- Authoring anchors for single-subject beats. They constrain the model unnecessarily.
- Vague `element` text. Be specific enough that a stranger could identify it from the description alone.
- Using `left`/`right` in 9:16 split-screens.
- Forgetting to mirror anchors in the matching `clip_NN.validation.txt`. Anchors only help if the auditor checks them.
