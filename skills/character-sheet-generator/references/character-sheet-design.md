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
- **Auto-regen on QA failure.** The phase runs an explicit *describe → audit → verdict* pass and re-renders up to 2× before surfacing the gate. The human only sees a sheet that the auditor approved or that exhausted retries (and is flagged `needs_review`).
- **Always validate** with Gemini 2.5 Pro — produces `characters/analysis.json` containing the QA report AND `_qa_history` (per-attempt verdict + addendum). The clip-generator reads from this analysis when prompting Seedance, NOT the original prompt — because the sheet is what the i2v model sees.

## QA pattern (describe → audit → verdict)

The analyser prompt explicitly forbids documentation-only mode. It must:

1. **DESCRIBE** each character (features, palette, poses).
2. **AUDIT** with these concrete checks — flag every anomaly:
   - **Limb count ≠ 4** (extra legs, hybrid quadruped/biped anatomy, duplicated body parts).
   - **Asymmetric features across poses** (spots disappear in side view, eye shape changes, ear count differs).
   - **Missing signature props** (e.g. Hiru's leaf, Sher's fang) in any pose.
   - **Style drift** from the requested style (flat/2D bleed when 3D is asked, photorealism when stylised is asked).
   - **Palette drift** across poses.
   - **Background non-neutral** (environmental clutter that will interfere with later sheet-conditioned generations).
3. **VERDICT** — `APPROVED` or `NEEDS_REGEN`. On `NEEDS_REGEN`, return a one-line `regen_reason` and a concrete 1-2-sentence `corrective_addendum` (e.g. *"Render exactly 4 legs per character. Quadrupeds stand on all fours; bipeds stand on two legs. No hybrid poses."*).

When unsure about a check, the auditor sets the bool to `false` and writes the doubt into the corresponding `*_detail` string. **False-positive approvals are worse than false-negatives here** — the user will see the sheet at Gate 3 either way; the system should err on the side of regenerating.

See `scripts/lib/visual_analyzer.py CHARACTER_SHEET_SCHEMA` for the strict JSON shape.
