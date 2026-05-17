# Empirical Prompt Log (from layout-gen)

Few-shot examples of placeholder values that produced good pages. Phase B1 reads this to ground its placeholder choices.

---

All prompts used with `gemini-3.1-flash-image-preview` via Google AI API.
API Key project: `vardhman-educational-videos`

---

## 1. Clothes We Wear — Type D Scattered Spots (v7, FINAL)

**Source**: `all-source-images/clothes-we-wear_frame-08.jpg`
**Output**: `output_type_d_clothes_v7.png`
**Model**: `gemini-3.1-flash-image-preview`
**Aspect**: `3:4` (portrait)
**Reference image**: Yes (source image for style)

**Prompt**:
```
Use the character and art style from this reference image. Generate a children's book page layout:

A4 portrait page (3:4), pure white background. Exactly 3 SMALL spot illustrations scattered on the page like stickers. Each spot is compact — roughly 20-25% of the page width. Total illustration coverage under 35%. 65%+ must be empty white space for text overlay later. Each spot isolated on white with no background, subtle soft drop shadow. Same 3D claymation Pixar style as the reference.

The 3 spots placed asymmetrically:
1) Top-right: Traditional Indian wooden handloom with colorful threads and small spools.
2) Center-left: Clay dye pot with colorful splashes and the cute magenta spool character with googly eyes next to it, arms raised excitedly. One combined compact scene.
3) Bottom-right: Sky-blue kurta on wooden hanger with gold embroidery on neckline.

CRITICAL: spots must be SMALL — like thumbnail stickers on a big white sheet. Most of the page is white. No text no words no letters no numbers.
```

---

## 2. Mowgli Joins the Pack — Template C Split Layout

**Source**: `all-source-images/mowgli-joins-the-pack_frame-05.jpg`
**Layout Reference**: `Reference images/3b73188a4e2e9e3e5cb2750ef314c97d.jpg`
**Output**: `output_mowgli_layout.png`
**Model**: `gemini-3.1-flash-image-preview`
**Aspect**: `4:3` (landscape)
**Reference images**: Yes (2 — layout ref + content ref)

**Prompt**:
```
I am giving you two reference images.

IMAGE 1 (first image) is the LAYOUT REFERENCE — a children's book page spread. Study its layout carefully:
- The illustration occupies the LEFT 55% of the page
- The RIGHT 40-45% is a lighter/cream colored area reserved for text
- The illustration elements (tree branches, birds) bleed and extend INTO the text zone, creating organic overlap
- Text would go in two blocks: top-right area and bottom-right area
- The illustration has a hand-painted, textured, artistic style with a limited color palette (greys, blacks, terracotta orange, cream)
- The composition uses a large tree as the main framing element on the left

IMAGE 2 (second image) is the CONTENT/SCENE REFERENCE — it shows Mowgli (a small human boy) sleeping peacefully, curled up against a large mother wolf, with small wolf cubs also sleeping around them. Warm forest setting. 3D claymation style.

NOW GENERATE: A children's book page that uses the LAYOUT from Image 1 but the SCENE/CONTENT from Image 2.

Specifically:
- LEFT 55% of the page: A large illustration of Mowgli sleeping with the mother wolf and wolf cubs, nestled under a big jungle tree. The tree's trunk and branches dominate the left side and extend across the top. Fireflies or small glowing particles float around them. Warm jungle foliage at the bottom. The style should be the same 3D claymation as Image 2.
- RIGHT 40-45%: A lighter, cream/warm-toned area with NO text but clearly designed as the text zone. Some illustrated elements from the main scene (small leaves, a vine, maybe a tiny firefly) should gently extend into this zone, just like the birds extend into the text zone in Image 1.
- The overall composition should feel like a book page spread where text WILL be placed later on the right side.

No text, no words, no letters, no numbers. Just the illustration with the built-in text zone on the right.
```

---

## 3. Reproduction in Plants — Option 1: Type D Scattered Spots

**Source**: `all-source-images/reproduction-in-plants_frame-11.jpg`
**Output**: `output_reproduction_option1.png`
**Model**: `gemini-3.1-flash-image-preview`
**Aspect**: `3:4` (portrait)

**Prompt**:
```
Use the characters and art style from this reference image. Generate a children's educational book page:

A4 portrait page (3:4), pure white background. Exactly 3 SMALL spot illustrations scattered on the page like stickers. Each spot is compact — roughly 20-25% of the page width. Total illustration coverage under 35%. 65%+ must be empty white space for text overlay later. Each spot isolated on white with no background, subtle soft drop shadow. Same 3D claymation Pixar style as the reference.

The 3 spots placed asymmetrically:
1) Top-right: A carrot with its green leafy top, shown with a soil cross-section so you can see the orange root underground. Compact.
2) Center-left: A sprouting potato with small tubers growing from it, and the cute anthropomorphic bean character sitting on top happily. One combined compact scene with soil visible.
3) Bottom-right: A bryophyllum leaf with tiny baby plantlets growing from its edges, small roots dangling down. Compact.

Spots must be SMALL — like thumbnail stickers on a big white sheet. No text no words no letters no numbers.
```

---

## 4. Reproduction in Plants — Option 2: Type C Horizontal Split

**Source**: `all-source-images/reproduction-in-plants_frame-11.jpg`
**Output**: `output_reproduction_option2.png`
**Model**: `gemini-3.1-flash-image-preview`
**Aspect**: `3:4` (portrait)

**Prompt**:
```
Use the characters and art style from this reference image. Generate a children's educational book page:

A4 portrait page (3:4), white background. HORIZONTAL SPLIT layout:

TOP 35-40% of the page: A horizontal strip showing 3 spot illustrations in a loose row (NOT a rigid grid). The 3 illustrations are:
1) Left spot: A carrot with green top, soil cross-section showing the root underground
2) Center spot: A sprouting potato with tubers, the cute bean character sitting on top
3) Right spot: A bryophyllum leaf with baby plantlets growing from edges

Each spot is isolated on white with subtle shadow, slightly different sizes, slight random rotations (2-3 degrees). They sit in the top portion of the page like a display shelf.

BOTTOM 60-65%: Completely empty white/cream space. Nothing here — this is reserved for text paragraphs and explanations to be added later.

Style: Same 3D claymation Pixar style as the reference. Warm earthy colors.

No text no words no letters no numbers.
```

---

## 5. Reproduction in Plants — Option 3: Infographic (Connected Scene)

**Source**: `all-source-images/reproduction-in-plants_frame-11.jpg`
**Layout Reference**: `Reference images/c191d08e5ccde29493d71c8ef3b769d4.jpg` (giraffe page)
**Output**: `output_reproduction_plants.png`
**Model**: `gemini-3.1-flash-image-preview`
**Aspect**: `3:4` (portrait)

**Prompt**:
```
I am giving you two reference images.

IMAGE 1 (first image) is the LAYOUT REFERENCE — a children's educational book page about giraffes. Study its layout:
- One LARGE central illustration dominates the page (the giraffe)
- Multiple smaller illustration pieces are scattered around it
- Text blocks fill the GAPS between illustrations
- Labels and callouts point to specific parts
- The illustrations are on a white page background
- It feels like a scientific diagram page — informative, visual, scattered but organized

IMAGE 2 (second image) is the CONTENT REFERENCE — it shows 3 types of vegetative reproduction in plants in 3D claymation Pixar style:
1. A carrot growing underground (root reproduction)
2. A cute anthropomorphic bean/seed character jumping from a sprouting potato (tuber reproduction)
3. A leaf with baby plantlets growing from its edges (leaf reproduction / bryophyllum)
All shown with soil cross-section visible.

NOW GENERATE: A children's educational book page (A4 portrait, 3:4 aspect ratio) that uses a CONNECTED INFOGRAPHIC layout:

- CENTER of the page: One large connected soil cross-section scene showing ALL 3 plants growing together in one continuous ground. Left section has the carrot underground with its green top above soil. Middle section has the potato with sprouts and the cute bean character sitting on top. Right section has the bryophyllum leaf with tiny plantlets growing from its edges. The soil layer connects all three, showing underground roots/tubers.
- The illustration should occupy roughly 40-50% of the page area, placed in the CENTER
- AROUND the illustration on all sides: generous white/cream space for text, labels, and callouts to be added later
- A few tiny decorative elements (small leaves, seeds, soil particles) scattered in the white space to connect the illustration to the surrounding area — like the birds in Image 1's layout
- Style: Same 3D claymation Pixar style as Image 2. Warm earthy colors, clay textures, soft lighting.
- The scene should feel like a SCIENTIFIC DIAGRAM — educational, clear, each plant section distinct and identifiable

CRITICAL: The illustration must be compact in the center. 50%+ of the page must be empty white space. No text, no words, no letters, no numbers, no labels.
```

---

## 6. Mandalay Jail Tilak — Option A: Full-Bleed + Text Zone

**Source**: `all-source-images/mandalay-jail-lokmanya-tilak_frame-05.jpg`
**Output**: `output_tilak_optionA.png`
**Model**: `gemini-3.1-flash-image-preview`
**Aspect**: `16:9` (landscape)

**Prompt**:
```
Use the character, scene, and watercolor art style from this reference image. Generate a children's history book page:

Landscape page (16:9). Full-bleed watercolor illustration filling the entire page. The scene shows Lokmanya Tilak sitting cross-legged in meditation inside his dark Mandalay jail cell, holding the Bhagavad Gita. He wears white dhoti and a red Maharashtrian cap. A warm golden spiritual glow emanates from him. A barred window is on the stone wall behind him. The mood is serene, spiritual, and powerful.

LAYOUT KEY: The illustration is composed so that the RIGHT 35-40% of the page is deliberately LIGHTER and SIMPLER — the stone wall fades into a soft warm cream/parchment tone. This lighter zone is the text area where story text will be overlaid later. The detailed illustration (Tilak, glow, window, jail details) is concentrated in the LEFT 60%.

Some subtle illustrated elements (faint Sanskrit letterforms floating as golden particles, stone texture, a crack in the wall) extend gently into the light text zone to connect it visually.

Watercolor style — visible brush strokes, wet-on-wet blending, ink outlines. Warm palette: golden yellows, deep stone greys, white fabric, touches of red.

No text, no words, no letters, no numbers.
```

---

## 7. Mandalay Jail Tilak — Option B: Split Layout

**Source**: `all-source-images/mandalay-jail-lokmanya-tilak_frame-05.jpg`
**Output**: `output_tilak_optionB.png`
**Model**: `gemini-3.1-flash-image-preview`
**Aspect**: `16:9` (landscape)

**Prompt**:
```
Use the character, scene, and watercolor art style from this reference image. Generate a children's history book page:

Landscape page (16:9). SPLIT LAYOUT — the page is divided into two clear zones:

LEFT 55%: A rich watercolor illustration of Lokmanya Tilak sitting in meditation inside his Mandalay jail cell. He wears white dhoti and red Maharashtrian cap, holding the Bhagavad Gita. Golden spiritual glow around him. Stone walls, barred window with moonlight. Dark atmospheric mood. Full detail and rich watercolor textures.

RIGHT 45%: An aged parchment/yellowed paper texture zone — warm cream/beige color, like an old manuscript page. This area is completely EMPTY of any illustration details — it is purely the text zone. The only visual elements here are very subtle: faint golden particles drifting from the left illustration into this zone, and perhaps a very light watercolor wash at the edges where the two zones meet, creating a soft transition rather than a hard cut.

The transition from illustration to text zone should feel organic — the stone wall texture gradually fades into parchment. Not a sharp line.

Watercolor style throughout. Warm palette.

No text, no words, no letters, no numbers.
```

---

## 8. Mandalay Jail Tilak — Option C: Frame/Border Layout

**Source**: `all-source-images/mandalay-jail-lokmanya-tilak_frame-05.jpg`
**Output**: `output_tilak_optionC.png`
**Model**: `gemini-3.1-flash-image-preview`
**Aspect**: `3:4` (portrait)

**Prompt**:
```
Use the character, scene, and watercolor art style from this reference image. Generate a children's history book page:

Portrait page (3:4). ILLUSTRATED BORDER/FRAME layout:

The jail cell itself forms a FRAME around the page:
- Stone wall texture borders on LEFT, RIGHT, and TOP edges of the page (like looking at the inside of a cell)
- A barred window at the TOP CENTER of the frame, with moonlight streaming in
- The stone border is roughly 15-20% width on each side

BOTTOM CENTER (30% of page height): Lokmanya Tilak sitting cross-legged in meditation, holding the Bhagavad Gita. White dhoti, red cap. He is compact, placed at the bottom of the page. Rich watercolor detail.

CENTER/UPPER CENTER (the large open area inside the frame, 50% of the page): A warm GOLDEN GLOW radiates upward from Tilak, filling the center of the page. This glow zone is lighter, warmer, almost ethereal — cream and gold watercolor wash. This entire glowing area is the TEXT ZONE where verses and narrative will be placed later. Faint golden particles and wisps float in this zone.

The overall effect: dark stone frame on edges → golden light in center → Tilak at bottom. Like looking into a spiritual space inside a prison cell.

Watercolor style — wet washes, visible brush texture, ink details on the stone. Warm golden center contrasting with cool grey stone edges.

No text, no words, no letters, no numbers.
```

---

## 2026-04-17 08:00 — split-layout

**Source**: `all-source-images/mowgli-joins-the-pack_frame-05.jpg`
**Output**: `output_test_skill.png`
**Template**: `split-layout`
**Aspect**: `16:9`
**Model**: `gemini-3.1-flash-image-preview`

**Prompt**:
```
I am giving you two reference images.

IMAGE 1 is the LAYOUT REFERENCE — study its spatial arrangement: where the illustration sits, where the text zones are, how elements bleed between zones.

IMAGE 2 is the CONTENT/STYLE REFERENCE — use its characters, art style, and visual language.

Generate a new image that uses the LAYOUT from Image 1 with the CONTENT/STYLE from Image 2.

Landscape page (16:9). SPLIT LAYOUT: LEFT 55%: Rich illustration of Mowgli sleeping peacefully curled up against a large mother wolf under a banyan tree at night, wolf cubs snuggled around, fireflies glowing, warm moonlight through jungle canopy, 3D claymation Pixar style. Full detail. RIGHT 45%: Lighter warm cream/parchment text zone. Some illustrated elements drift from left into right zone. Transition is organic, not a hard cut. No text, no words, no letters, no numbers.
```
