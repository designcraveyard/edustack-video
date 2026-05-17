# Book Page Prompt Patterns

Ported from layout-gen. Adapted for fal-ai/gpt-image-2 with **transparent-background output**: the text zone is left transparent so book designers can drop pages into InDesign and add their own text.

For each template, the Phase B1 planner picks placeholder values; Phase B2 substitutes them and submits.

---

Each template has a tested prompt pattern. When generating, substitute the `{placeholders}` with actual content.

---

## 1. full-bleed-with-text-zone

**Aspect ratio**: 16:9 (landscape)
**Reference folder**: `template-references/full-bleed-with-text-zone/`
**Best ref**: `ref_06_jungle-boy-text-left.jpg` or `ref_03_kids-tree-text-topleft.jpg`

**Prompt pattern**:
```
Use the character and art style from these reference images. Match the characters' appearance exactly across all generated pages. Generate a children's book page:

Landscape page (16:9). Full-bleed {art_style} illustration filling the entire page. The scene shows {scene_description}.

LAYOUT KEY: The {text_zone_side} {text_zone_percent}% of the page is deliberately LIGHTER and SIMPLER — {text_zone_description}. This lighter zone is the text area where story text will be overlaid later. The detailed illustration ({key_elements}) is concentrated in the opposite {illustration_percent}%.

Some subtle illustrated elements ({bleed_elements}) extend gently into the light text zone to connect it visually.

{art_style_description}. Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only.
```

**Placeholder guide**:
- `text_zone_side`: Usually RIGHT (35-40%) or LEFT
- `bleed_elements`: leaves, petals, particles, stone texture cracks, light rays
- `text_zone_description`: "fades into soft transparent (no painted fill)" / "the sky opens up into warm golden light"

---

## 2. vignette-on-page

**Aspect ratio**: 3:4 (portrait)
**Reference folder**: `template-references/vignette-on-page/`

**Prompt pattern**:
```
Use the character and art style from these reference images. Match the characters' appearance exactly across all generated pages. Generate a children's book page:

A4 portrait page (3:4), transparent background. ONE large VIGNETTE illustration placed at the {vignette_position} of the page, occupying roughly {vignette_percent}% of the page height and {vignette_width}% of the page width. The illustration has SOFT FADED EDGES that blend into the white page — no hard borders.

The vignette shows: {scene_description}. {art_style_description}.

The {text_area_position} of the page is completely empty white — this is where the chapter title and opening text will go.

The vignette illustration fades softly at its {fade_edge} edge into the white page. Small decorative elements ({decorative_elements}) float from the vignette into the white space.

Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only.
```

**Typical values**:
- `vignette_position`: BOTTOM-CENTER
- `text_area_position`: TOP 40-45%
- `vignette_percent`: 50-55%

---

## 3. split-layout

**Aspect ratio**: 16:9 (landscape) or 4:3
**Reference folder**: `template-references/split-layout/`
**Best ref**: `ref_01_old-woman-birds-split.jpg`

**Prompt pattern**:
```
Two reference images. IMAGE 1 is the LAYOUT reference — study how the illustration is on the {illust_side} {illust_percent}% and a lighter text zone is on the {text_side} {text_percent}%, with illustrated elements bleeding into the text zone.

IMAGE 2 is the CONTENT reference — {source_description}.

Generate a children's book page ({aspect}) using LAYOUT from Image 1 and CONTENT from Image 2:

{illust_side_upper} {illust_percent}%: {detailed_scene_description}. Rich detail, {art_style} style.

{text_side_upper} {text_percent}%: {text_zone_description}. Some {bleed_elements} extend gently from the scene into this zone, creating organic overlap. {transition_description}.

Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only.
```

**Key**: The transition description is critical — "The stone wall texture gradually fades into parchment. Not a sharp line."

---

## 4. scattered-spots

**Aspect ratio**: 3:4 (portrait)
**Reference folder**: `template-references/scattered-spots/`
**Best ref**: `ref_01_giraffe-educational-spots.jpg`

**Prompt pattern**:
```
Use the characters and art style from this reference. Generate a children's educational book page:

A4 portrait page (3:4), transparent background. Exactly {num_spots} SMALL spot illustrations scattered on the page like stickers. Each spot is compact — roughly 20-25% of the page width. Total illustration coverage under 35%. 65%+ must be empty white space for text overlay later. Each spot isolated on white with no background, subtle soft drop shadow. {art_style_description}.

The {num_spots} spots placed asymmetrically:
1) {position_1}: {spot_1_description}. Compact.
2) {position_2}: {spot_2_description}. Compact.
3) {position_3}: {spot_3_description}. Compact.

Spots must be SMALL — like thumbnail stickers on a big white sheet. Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only.
```

**Size control tip**: If spots come out too large, add: "STRICT SIZE RULES: The entire page is divided into a 4x5 grid. Each spot must fit within exactly ONE grid cell."

---

## 5. full-spread-no-text

**Aspect ratio**: 16:9 (landscape)
**Reference folder**: `template-references/full-spread-no-text/`

**Prompt pattern**:
```
Use the character and art style from these reference images. Match the characters' appearance exactly across all generated pages. Generate a children's book double-page spread:

Landscape (16:9). Full edge-to-edge {art_style} illustration spanning the entire spread. {scene_description}. Rich, immersive, cinematic composition. This is a dramatic moment with no text needed — pure visual storytelling.

{art_style_description}. Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only.
```

---

## 6. illustrated-border

**Aspect ratio**: 3:4 (portrait)
**Reference folder**: `template-references/illustrated-border/`
**Best ref**: `ref_02_fox-crow-tree-frame.jpg`

**Prompt pattern**:
```
Use the character and art style from these reference images. Match the characters' appearance exactly across all generated pages. Generate a children's book page:

Portrait page (3:4). ILLUSTRATED BORDER/FRAME layout:

{frame_description}:
- {frame_element} borders on LEFT, RIGHT, and TOP edges of the page
- {frame_accent} at the {accent_position} of the frame
- The border is roughly 15-20% width on each side

{character_position} ({character_percent}% of page height): {character_description}. Compact, placed at the {character_location} of the page.

{text_zone_position} (the large open area inside the frame, {text_zone_percent}% of the page): {text_zone_description}. This entire area is the TEXT ZONE.

{art_style_description}. Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only.
```

---

## 7. character-text-pocket

**Aspect ratio**: 3:4 (portrait)
**Reference folder**: `template-references/character-text-pocket/`

**Prompt pattern**:
```
Generate a children's book page:

Portrait page (3:4). A large {character_description} in a {pose_description} pose that creates an open white negative space in the {pocket_position} of the composition. The character's body forms a natural frame or pocket where text can be placed.

White/transparent background. The character is rendered in {art_style}. The negative space pocket should be roughly {pocket_percent}% of the page area — clean and empty for text overlay.

Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only.
```

---

## 8. connected-infographic

**Aspect ratio**: 3:4 (portrait)
**Reference folder**: `template-references/connected-infographic/`

**Prompt pattern**:
```
Two reference images. IMAGE 1 is the LAYOUT reference — study how one large central illustration dominates the page with text spaces around it. IMAGE 2 is the CONTENT reference.

Generate a children's educational book page (3:4):

CENTER of the page: One large connected scene showing {connected_scene_description}. The illustration should occupy roughly 40-50% of the page area, placed in the CENTER.

AROUND the illustration on all sides: generous white/cream space for text, labels, and callouts to be added later.

A few tiny decorative elements ({decorative_elements}) scattered in the white space.

Style: {art_style_description}.

CRITICAL: The illustration must be compact in the center. 50%+ of the page must be empty white space. Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only.
```

---

## 9. spread-scene-plus-spots

**Aspect ratio**: 16:9 (landscape)
**Reference folder**: `template-references/spread-scene-plus-spots/`
**Best ref**: `ref_01_fairies-spread-plus-spots.jpg`

**Prompt pattern**:
```
Two reference images. IMAGE 1 is LAYOUT REFERENCE — a children's book double-page spread:
- LEFT PAGE: Full-bleed illustration, one rich scene filling the entire left page
- RIGHT PAGE: White/cream background with 3 small spot vignette illustrations scattered. Each spot has soft faded edges blending into white. Generous white space between spots for text.

IMAGE 2 is CONTENT REFERENCE — {source_description}.

Generate a double-page spread (16:9):

LEFT HALF (full-bleed scene): {main_scene_description}. Rich, immersive, full scene. {art_style} style.

RIGHT HALF (white background with 3 small spot vignettes):
- TOP-RIGHT spot: {spot_1_description}. Soft edges.
- CENTER spot: {spot_2_description}. Soft edges.
- BOTTOM-RIGHT spot: {spot_3_description}. Soft edges.

Each spot is SMALL (roughly 25% of the right half width). 60%+ of the right half is white for text. Spots have soft watercolor-like edges.

Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only.
```

---

## General Tips

### Art style descriptors
- **Claymation**: "3D claymation Pixar stop-motion style, warm studio lighting, handmade clay felt wood textures, visible fingerprints in clay"
- **Watercolor**: "Watercolor style, visible brush strokes, wet-on-wet blending, ink outlines, textured paper feel"
- **Flat illustration**: "Flat illustration style, bold clean colors, geometric shapes, minimal texture"

### Aspect ratio by template
- Portrait (3:4): scattered-spots, vignette-on-page, illustrated-border, character-text-pocket, connected-infographic
- Landscape (16:9): full-bleed-with-text-zone, split-layout, full-spread-no-text, spread-scene-plus-spots
