# Character sheet prompt template

This is the **canonical structure** used by `scripts/phase_characters.py` when it composes the prompt for `fal-ai/gpt-image-2`. The Python implementation in `phase_characters.py` mirrors this template field-for-field. When the rendered sheet under-delivers, fix the template here AND the renderer in lockstep.

## Skeleton

The first line is the **style descriptor** (one paragraph, drawn from `STYLE_DESCRIPTORS[brief.style]` in `phase_characters.py`). The model anchors its entire aesthetic on this line.

```text
{STYLE_DESCRIPTOR}

Create a highly detailed {STYLE} character turnaround sheet on a clean white studio background. Layout should resemble a professional animation pre-production character design board, 16:9, with generous whitespace and handwritten sketchbook typography labels.

Title at top-left:
"{TITLE}"
Subtitle:
"CHARACTER SHEET"

Overall aesthetic:
    - {AESTHETIC BULLET 1}
    - {AESTHETIC BULLET 2}
    - {AESTHETIC BULLET 3}
    - {AESTHETIC BULLET 4}

LEFT SECTION:
Show a full-body hero pose of {HERO POSE DESCRIPTION}.

{CHARACTER 1 NAME}:
{CHARACTER 1 VERBATIM DESCRIPTION}

{CHARACTER 2 NAME}:        # only when 2 characters; omit block entirely for solo
{CHARACTER 2 VERBATIM DESCRIPTION}

CENTER TOP:
Label: "{CHAR1 NAME UPPER}"
- 4 close-up facial expressions in a horizontal row: {CLOSEUP_EXPRESSIONS_1}
- Below: full-body turnaround views — front, 3/4, side, back

RIGHT TOP:                  # only when 2 characters
Label: "{CHAR2 NAME UPPER}"
- 4 close-up facial expressions in a horizontal row: {CLOSEUP_EXPRESSIONS_2}
- Below: full-body turnaround views — front, 3/4, side, back

BOTTOM CENTER:
Label: "COLOR PALETTE"
Circular swatches for the distinctive colors in this sheet: {PALETTE_SWATCHES}

BOTTOM MIDDLE:
Label: "EXPRESSIONS"
Show additional small emotional portraits for {EXPRESSION_GRID_SUBJECTS}: {EXPRESSION_GRID}

BOTTOM RIGHT:
Label: "DETAILS"
Close-up detail callouts for the visually distinctive features: {DETAIL_CALLOUTS}

Style requirements:
- Cohesive visual language
- Character proportions matching the brief's style
- {STYLE_FINISH_BULLETS}
- Clean presentation sheet, white margins, balanced grid layout
- 16:9 horizontal aspect ratio
- Concept-art quality
```

## Field rules

| Placeholder | Where it comes from | Constraint |
|---|---|---|
| `STYLE_DESCRIPTOR` | `STYLE_DESCRIPTORS[brief.style]` | One paragraph. Names the medium (Pixar 3D / watercolour / cel-shaded 2D / whiteboard ink). |
| `STYLE` | `brief.style` (verbatim) | Single word or short phrase: "Pixar", "Watercolour", "2D Flat". |
| `TITLE` | `"{Char1}" or "{Char1} & {Char2}"` | Match the on-sheet header convention. |
| `AESTHETIC BULLETS` | `aesthetic_bullets_for(mode, style)` | 4–5 bullets. Bias on `mode` (human → silhouette/lighting; abstract → mascot-readability). |
| `HERO POSE DESCRIPTION` | `hero_pose_description(cast)` | "X standing beside Y, interacting in-character and clearly distinct" or solo. |
| `CHARACTER N VERBATIM DESCRIPTION` | `CastMember.verbatim_description` | **Verbatim** from the script's `## Cast` block. Never paraphrase. |
| `CLOSEUP_EXPRESSIONS_N` | `closeup_expressions_for(cast_member)` | 4 emotions drawn from the character's personality/voice_tone fields. |
| `PALETTE_SWATCHES` | `palette_swatches_from_looks(cast)` | 5–7 named swatches mined from looks text. Always close on a `neutral background` or `paper white`. |
| `EXPRESSION_GRID` | `expression_grid_for_cast(cast)` | 4–6 emotions spanning the cast. |
| `DETAIL_CALLOUTS` | `detail_callouts_for_cast(cast)` | 3–5 visually distinctive features. `"{Char}'s {feature}"` reads best on-sheet. |
| `STYLE_FINISH_BULLETS` | `STYLE_FINISH_BULLETS[brief.style]` | 1–3 bullets describing render finish (subsurface scattering, watercolour blooms, cel shading). |

## Canonical example 1 — Pixar (Jay & Scooterist)

```text
Pixar 3D animated film aesthetic, soft directional lighting, smooth subsurface materials, expressive characters, shallow depth of field.

Create a highly detailed Pixar character turnaround sheet on a clean white studio background. Layout should resemble a professional animation pre-production character design board, 16:9, with generous whitespace and handwritten sketchbook typography labels.

Title at top-left:
"Jay & Scooterist"
Subtitle:
"CHARACTER SHEET"

Overall aesthetic:
- Soft cinematic lighting with clear action-movie readability for a child audience
- Rounded Pixar-style proportions with strong posture contrast between child and adult
- Clean studio presentation with polished 3D shading and easy silhouette recognition
- Bright playground-and-road palette with a comedic, family-friendly tone
- Gentle surface detail, smooth materials, and strong clarity for motion scenes

LEFT SECTION:
Show a full-body hero pose of Jay standing beside the scooterist, both in-character and clearly distinct.

Jay:
A slightly taller child silhouette with determined eyebrows, warm brown skin, dark hair, and a clear hockey-stick pose that reads instantly.

Scooterist:
A simple, readable adult silhouette on a scooter, wearing a proper helmet, modest everyday clothes, and warm neutral colours so the red or blue scooter stays visually clear.

CENTER TOP:
Label: "JAY"
- 4 close-up facial expressions in a horizontal row: focus, determination, surprise, delighted laughter
- Below: full-body turnaround views — front, 3/4, side, back

RIGHT TOP:
Label: "SCOOTERIST"
- 4 close-up facial expressions in a horizontal row: calm neutrality, unaware focus, casual riding, mild confusion
- Below: full-body turnaround views — front, 3/4, side, back

BOTTOM CENTER:
Label: "COLOR PALETTE"
Circular swatches for the distinctive colors in this sheet: warm brown skin, dark hair, helmet colour, scooter body colour, neutral adult clothing, Jay's sporty clothing, hockey-stick colour

BOTTOM MIDDLE:
Label: "EXPRESSIONS"
Show additional small emotional portraits for Jay and Scooterist: concentration, surprise, calm, laughter

BOTTOM RIGHT:
Label: "DETAILS"
Close-up detail callouts for the visually distinctive features: Jay's determined eyebrows, Jay's hockey-stick pose, the scooterist's helmet, the scooter basket, the scooter body colour

Style requirements:
- Cohesive visual language
- Character proportions matching the brief's style
- Pixar 3D finish with soft global illumination, subtle subsurface scattering, gentle ambient occlusion, and polished family-film rendering
- Clean presentation sheet, white margins, balanced grid layout
- 16:9 horizontal aspect ratio
- Concept-art quality
```

## Canonical example 2 — Watercolour (Leafy Grazer & Claw Hunter)

```text
Watercolour illustration aesthetic, paper texture, soft pigment bleeds, layered washes, hand-mixed earthy palette.

Create a highly detailed Watercolour character turnaround sheet on a clean white studio background. Layout should resemble a professional animation pre-production character design board, 16:9, with generous whitespace and handwritten sketchbook typography labels.

Title at top-left:
"Leafy Grazer & Claw Hunter"
Subtitle:
"CHARACTER SHEET"

Overall aesthetic:
- Soft watercolor washes with visible paper texture
- Gentle, classroom-friendly storybook mood
- Clean silhouette design with readable mascot shapes
- Muted organic palette with one warm accent family per character
- Light sketch-line outlines, no heavy ink blacks

LEFT SECTION:
Show a full-body hero pose of Leafy Grazer standing beside Claw Hunter, interacting in-character.

Leafy Grazer:
Abstract watercolor herbivore mascot blending deer-like ears, a rounded rabbit softness, and a leaf-green palette with cream highlights. Calm, friendly, and curious. Safe and easy for a Class 5 learner to read instantly. Movement is unhurried and reassuring. No spoken lines in this cut; the tone is carried through gentle head tilts, soft chewing gestures, and relaxed body language.

Claw Hunter:
Abstract watercolor carnivore mascot with a lion-like mane shape, tiger-striping hints, warm orange-brown tones, and darker paw accents. Alert, focused, and confident without feeling scary. The energy is sharper than Leafy Grazer, but still classroom-friendly and non-threatening. Movements are precise and controlled. No spoken lines in this cut; the tone comes through firm posture, quick head turns, and crisp paw placement.

CENTER TOP:
Label: "LEAFY GRAZER"
- 4 close-up facial expressions in a horizontal row: curiosity, gentle surprise, relaxed chewing, friendly smile
- Below: full-body turnaround views — front, 3/4, side, back

RIGHT TOP:
Label: "CLAW HUNTER"
- 4 close-up facial expressions in a horizontal row: alert focus, confident calm, quick head turn, classroom-friendly determination
- Below: full-body turnaround views — front, 3/4, side, back

BOTTOM CENTER:
Label: "COLOR PALETTE"
Circular swatches for the distinctive colors in this sheet: leaf green, cream highlight, soft beige, warm orange-brown, tiger stripe umber, dark paw accent, paper white

BOTTOM MIDDLE:
Label: "EXPRESSIONS"
Show additional small emotional portraits for Leafy Grazer and Claw Hunter: curiosity, calm, surprise, focus, reassurance, confidence

BOTTOM RIGHT:
Label: "DETAILS"
Close-up detail callouts for the visually distinctive features: deer-like ears, rounded rabbit muzzle, leaf-green watercolor washes, lion-like mane shape, tiger-striping hints, dark paw accents

Style requirements:
- Cohesive visual language
- Character proportions matching the brief's style
- Watercolour finish with soft pigment blooms, translucent washes, and hand-painted edges
- Clean presentation sheet, white margins, balanced grid layout
- 16:9 horizontal aspect ratio
- Concept-art quality
```

## Tuning by style

| `brief.style` | Override behaviour |
|---|---|
| `Pixar` | Polished 3D, soft subsurface scattering, ambient occlusion, rounded family-film proportions. |
| `Watercolour` / `Watercolor` | Paper texture, pigment bleeds, layered washes, muted earthy palette, no heavy ink blacks. |
| `2D Flat` | Crisp vector silhouettes, limited cel shading, no gradients on character forms, bold colour blocks. |
| `2D Animated` | Cel shading + hand-painted backgrounds; expressive line weight; vibrant story-driven palette. |
| `Cinematic` | Photoreal cinematic finish; naturalistic skin/fabric; filmic grade. Use sparingly. |
| `Whiteboard` | Ink lines on warm off-white; spot colour for emphasis; simple flat shading. |
| `Doodle` | Slightly imperfect ink lines; hand-noted labels; paper grain; restrained spot colour. |
| `Clay` | Plasticine sheen; visible thumbprints; soft studio lighting; slightly chunky proportions. |

When introducing a new style, add it to:

1. `STYLE_DESCRIPTORS` in `scripts/phase_characters.py` (one-paragraph descriptor).
2. `STYLE_FINISH_BULLETS` in `scripts/phase_characters.py` (1–3 finish bullets).
3. The table above.

## Hard rules (mirror the design doc)

- 16:9 landscape only. Other aspects break the 8-region layout.
- Max 2 characters per sheet. 3+ → `character_mode: none`.
- Verbatim descriptions on the sheet must match `descriptions.json` byte-for-byte. Both come from the same `CastMember.verbatim_description` source.
- Never embed text past the labels. The model should not invent dialogue or captions; we use labels only.
