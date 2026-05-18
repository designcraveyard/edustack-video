# Character sheet design

The character sheet is the **visual identity contract** for the whole video. Every keyframe (Phase 3b) and every clip (Phase 4) reads from it — either as an image reference (sheet PNG) or as a verbatim text paragraph (`descriptions.json` → CHARACTERS block). Treat it as the only place where character look/feel is allowed to drift; everything downstream is supposed to be a copy.

## Layout (rich template)

One image, 16:9 landscape, white studio background, generous whitespace, handwritten sketchbook typography labels. Eight named regions:

| Region          | Contents |
|-----------------|----------|
| TOP-LEFT        | Title (`{Char1}` or `{Char1} & {Char2}`) + subtitle `"CHARACTER SHEET"` |
| LEFT SECTION    | Full-body **hero pose** of the character(s) interacting in-character. The verbatim description block sits underneath. |
| CENTER TOP      | `{CHAR1 NAME}` header → 4 close-up facial expressions in a row, then a 4-pose turnaround (front / 3⁄4 / side / back). |
| RIGHT TOP       | `{CHAR2 NAME}` header → mirrors CENTER TOP. Omitted on a solo sheet. |
| BOTTOM CENTER   | `COLOR PALETTE` label → 5–7 circular swatches naming the distinctive colours (hair, skin, top, bottom, prop, accent…). |
| BOTTOM MIDDLE   | `EXPRESSIONS` label → 4–6 additional small emotional portraits across the cast. |
| BOTTOM RIGHT    | `DETAILS` label → 3–5 close-up callouts for the visually distinctive features (a specific hair-tie, a hockey-stick pose, a paw motif, a helmet). |

The full prompt skeleton lives in [`prompt-template.md`](./prompt-template.md), with two end-to-end examples (Pixar and Watercolour) that you can copy and adapt.

## Mode → sheet content

| `character_mode` | Sheet produced? | Character count | Style descriptor source |
|---|---|---|---|
| `human`    | yes — gpt-image-2 with rich template | 1–2 humans in one sheet (extras described via text only) | `brief.style` → `STYLE_DESCRIPTORS[style]` |
| `abstract` | yes — gpt-image-2 with rich template; aesthetic bullets nudge mascot-readability | 1–2 stylised non-human concepts | same |
| `none`     | **no sheet** — `description_block.md` only | 3+ characters or crowd scene | n/a |

## Outputs (human / abstract)

| File | Purpose |
|------|---------|
| `characters/sheet.png` | The image gpt-image-2 produced (16:9 landscape, multi-region layout). |
| `characters/sheet_prompt.md` | The full prompt sent + style descriptor + verbatim character descriptions. Audit trail. |
| `characters/analysis.json` | Gemini 2.5 Pro QA report (`verdict`, `regen_reason`, `corrective_addendum`, plus `_qa_history` of every regen attempt). |
| `characters/descriptions.json` | **The consistency contract.** Per-character paragraphs that downstream prompts must paste verbatim into their CHARACTERS section. Identity locks because every keyframe + clip prompt reads the *same paragraph*. |

## Hard rules

1. **Always 16:9 landscape.** The layout has too many regions for square or portrait. Models can stretch — don't let them.
2. **Always neutral white studio background.** Coloured backgrounds bake into sheet-conditioned downstream keyframes.
3. **Cap at 2 characters per sheet.** More crowds the layout. For 3+ characters, switch the brief to `character_mode: none` and rely on `description_block.md` instead.
4. **Auto-regen up to 2× on QA failure.** Phase runs *describe → audit → verdict*. Gate 3 only sees a sheet the auditor approved, or a sheet that exhausted retries (and is flagged `needs_review`).
5. **Verbatim descriptions, never paraphrased.** The text under each character on the sheet is the same text in `descriptions.json` is the same text downstream prompts read. One source of truth; never rewrite mid-pipeline.

## QA pattern (describe → audit → verdict)

`scripts/lib/visual_analyzer.py CHARACTER_SHEET_SCHEMA` defines the strict JSON shape. The analyser prompt explicitly forbids documentation-only mode — it must:

1. **DESCRIBE** each character (features, palette, poses).
2. **AUDIT** with concrete checks — flag every anomaly:
   - **Limb count ≠ 4** (extra legs, hybrid quadruped/biped anatomy).
   - **Asymmetric features across poses** (spots disappear in side view, eye shape changes).
   - **Missing signature props** (e.g. Jay's hockey stick, Hiru's leaf) in any pose.
   - **Style drift** from the requested style (flat/2D bleed when 3D is asked, photorealism when stylised is asked).
   - **Palette drift** across poses.
   - **Non-neutral background** (clutter that will bleed into downstream generations).
   - **Layout completeness** — title present, all 8 regions populated, palette readable.
3. **VERDICT** — `APPROVED` or `NEEDS_REGEN` with one-line `regen_reason` + 1–2-sentence `corrective_addendum`.

False-positive approvals are worse than false-negatives here — the human will see the sheet at Gate 3 either way; the system should err toward regenerating.

## Why 16:9 and not 1:1 (the previous default)

The old phase used a 1:1 3×3 grid (front/side/3⁄4 × neutral/happy/surprised). That's a fine model-sheet but it doesn't carry the title, hero pose, palette, expressions grid, or detail callouts that make the rich sheet useful as a downstream visual brief. 16:9 gives the eight regions room; the hero pose alone has reading value at Gate 3 (it's the only frame that shows characters *interacting*).

## Why gpt-image-2 and not Nano Banana 2

See [`model-selection.md`](./model-selection.md). Short version: the multi-region structured layout (title + grid + palette + callouts in one sheet) is gpt-image-2's strength. Nano Banana 2 is excellent for single-subject keyframes (Phase 3b's per-keyframe mode) but smears the structured grid.
