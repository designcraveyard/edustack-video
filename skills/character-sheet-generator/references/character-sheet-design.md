# Character sheet design

## Human mode

A single PNG containing a **1- or 2-character pose/expression grid**. 3×3 cells:

| | Neutral | Happy | Surprised |
|---|---|---|---|
| Front | A | A | A |
| Side  | A | A | A |
| 3⁄4   | A | A | A |

For two characters, side-by-side 3×3 grids (one per character) or a 3×6 grid.

**Prompt skeleton:**
```
Character reference sheet, model sheet style, neutral white background, soft three-quarter lighting.
3x3 grid showing the same character: front view, side view, 3/4 view × neutral, happy, surprised expressions.
Character: <name>, <species/age>, <build>, <hair>, <eyes>, <signature outfit>.
Render style: <brief.style>. Aspect: 1:1. No text, no labels, no border.
```

## Abstract mode

For stylized non-human concepts (an animated water droplet, an anthropomorphic neuron, a friendly shape):

```
Style reference sheet, <brief.style>. Same character: 6 poses (idle, moving, pointing, surprised, sad, happy).
Single PNG, neutral background, consistent palette. Aspect 1:1, no text.
```

## Hard rules

- **Always neutral background.** Saves later sheet-conditioned generations from baking weird backdrops.
- **One sheet per run.** Re-runs are gate-driven, not automatic.
- **Always validate** with Gemini 2.5 Pro — produces `characters/analysis.json` describing what was actually drawn (counts, distinguishing features, palette). The clip-generator uses this analysis when prompting Seedance, NOT the prompt — because the sheet is what the i2v model sees.
