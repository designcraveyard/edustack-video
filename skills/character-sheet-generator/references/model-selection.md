# Model selection (Phase 3a)

Default per `seed/models.yaml`: **`fal-ai/gpt-image-2`** with `image_size: landscape_16_9`, `quality: high`.

| Need | Model | Why |
|---|---|---|
| Default character sheet (human + abstract) | `fal-ai/gpt-image-2` | Handles the structured multi-region layout (title, hero pose, expressions row, turnaround, palette, callouts) reliably. Strong text rendering for region labels. Predictable 16:9 framing. |
| Tighter realism / photoreal humans | `fal-ai/flux/pro-v1.1-ultra` (override) | When `brief.style` is "cinematic" and you want photorealistic faces. Loses some layout fidelity vs. gpt-image-2. |
| Stylised 2D / illustrative looks | `fal-ai/imagen4` (override) | Stronger style adherence on hand-drawn looks; weaker at multi-region layout. Use only when the gpt-image-2 stylisation under-delivers. |

Override per stage in `<output>/.config/models.yaml`:

```yaml
character_sheet:
  model: fal-ai/flux/pro-v1.1-ultra
  image_size: landscape_16_9
```

## Why gpt-image-2 here

gpt-image-2's strengths line up with the character sheet's needs:

- **Structured multi-region layout.** The sheet has 8 distinct regions (title, LEFT hero, CENTER+RIGHT TOP per-character grids, BOTTOM CENTER palette, BOTTOM MIDDLE expressions, BOTTOM RIGHT details). gpt-image-2 holds the regions; most diffusion-style image models smear them.
- **Region labels render legibly.** Handwritten-sketchbook labels ("CHARACTER SHEET", "COLOR PALETTE", "JAY", per-detail callouts) come out readable. Critical because the labels are part of the design language.
- **Consistent turnaround.** Front / 3⁄4 / side / back of the same character with consistent proportions is the primary use-case gpt-image-2 was tuned for.
- **Locked white studio background.** When you ask for a clean white studio background it stays clean. No environmental bleed.

## Why not Nano Banana 2 for sheets

Nano Banana 2 is excellent at **single-subject high-fidelity keyframes** — that's why it's the default for Phase 3b's `per_keyframe` mode (one image per beat, character-sheet conditioned). But for the structured multi-region sheet:

- It smears the regions (the LEFT hero pose bleeds into the CENTER expressions row).
- Text labels render unreliably.
- The 4-pose turnaround often drifts in proportions across the four views.

Reserving Nano Banana 2 for keyframes (and gpt-image-2 for sheets + storyboard panels) also lets each endpoint be tuned independently and keeps rate-limit pressure off either one.

## Why not fal-ai/flux as the default

Flux's photoreal bias is too strong for stylised classroom content (Pixar, watercolour, doodle). When the brief is explicitly "cinematic", flux is the override of choice — but for the bread-and-butter educational explainer styles, gpt-image-2 reads the style descriptor more faithfully.

## Tuning knobs

Inside `models.yaml > character_sheet`:

```yaml
character_sheet:
  model: fal-ai/gpt-image-2
  image_size: landscape_16_9   # or {width:1536, height:864} for exact dims
  quality: high                 # low / medium / high; sheets MUST be high
  # background: "white"        # default; rarely needs override
  # output_format: png         # default; jpg loses palette swatch fidelity
```

`quality: high` is non-negotiable for sheets — the sheet feeds downstream image conditioning, and a low-quality sheet means every later keyframe inherits the artefacts.
