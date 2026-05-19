# Educational script structure

Canonical reference for what a `script.md` should contain. The plugin's [SKILL.md](../SKILL.md) requires the rich format (Strategy + Cast + Sound + Scene Timeline + Beats); this file teaches the format with one fully-worked example, then enumerates the rules.

---

## Full skeleton — 60 s photosynthesis explainer

```
---
title: How photosynthesis works
duration_estimate_seconds: 58
mode: standard
class_level: 6
language: English
style: 3D Pixar
aspect: 16:9
character_mode: human
dialogues_enabled: false
annotations_enabled: false
grounded: true
source_chapter: source/chapter.txt
---

# How photosynthesis works

## Strategy

Six-scene structure for 60 s. Hook on a counter-intuitive observation
(plant wilts in the dark), then build mechanism in three layers: ingredient
introduction → chlorophyll capture → glucose synthesis. Recap re-frames
the mechanism as the everyday reason we have air. Pacing favours visual
beats over dense narration (class 6 vocab ceiling: top 3000 words).
Single recurring character — Maya, a curious 11-year-old — observes
silently in the establishing and closing scenes.

## Cast

### Maya
- **Role in the video**: Curious observer who frames the question in the
  hook and closes the recap. Visually present in scenes 1 and 6; absent
  from the mechanism scenes (2–5).
- **Personality**: 11 years old, eager, science-fair brain, slightly
  shy. Doesn't speak — her reactions carry the emotional throughline.
- **Looks**: 11-year-old Indian girl, warm brown skin, a single long
  black plait reaching mid-back tied with a teal elastic, oval face,
  dark brown almond eyes, soft natural smile. Wears a deep-teal cotton
  T-shirt with a small white leaf-vein print on the chest pocket, mid-blue
  rolled denim shorts, white canvas sneakers with teal laces, slim build,
  ~140 cm tall.

(Voice and tone bullet OMITTED because dialogues_enabled is false.)

## Sound

- **Ambient music**: Soft acoustic guitar + ukulele plucks, 80 bpm,
  warm major key. Swells gently into the mechanism reveal at 0:20,
  softens during the recap at 0:48.
- **Sound effects**: Sparse. (a) [0:00] a single wind-through-leaves
  rustle on the wilted-plant shot. (b) [0:24] a soft chime as the
  chlorophyll glow ignites. (c) [0:53] a gentle inhale-exhale on the
  child's breath at the recap close.

## Scene Timeline

| # | Scene Title | Time Range | Dur | Clips | Transition In | Keyframes | Narration | Transition Out |
|---|---|---|---|---|---|---|---|---|
| 1 | The wilting plant | [0:00 – 0:05] | 5 s | 1 × 5 s | [0:00] Hard cut from black | [0:00] Wide: Maya by sunny window, healthy plant. <br> [0:03] Match cut: same plant in dark cupboard, wilting | [0:00] "Why does a plant in a dark room droop after a few days?" | [0:05] Hard cut → Scene 2 |
| 2 | Three ingredients | [0:05 – 0:15] | 10 s | 2 × 5 s | [0:05] Hard cut | [0:05] CU on a single leaf, three labelled icons floating in: sunlight, water, air | [0:05] "Leaves are tiny food factories." <br> [0:09] "They need three ingredients: sunlight, water, and air." | [0:15] Cross-dissolve 240 ms → Scene 3 |
| 3 | Chlorophyll capture | [0:15 – 0:27] | 12 s | 2 × 6 s | [0:15] Cross-dissolve | [0:15] Cellular zoom: photons enter a chloroplast. <br> [0:21] Glowing green pigment grains capture them | [0:15] "Sunlight hits a green pigment called chlorophyll." <br> [0:21] "Chlorophyll captures the energy and stores it." | [0:27] Match cut → Scene 4 |
| 4 | Glucose synthesis | [0:27 – 0:39] | 12 s | 2 × 6 s | [0:27] Match cut | [0:27] Water rising from roots; CO₂ entering through stomata. <br> [0:33] Glucose chains assembling | [0:27] "With that energy, the leaf splits water from the roots and pulls carbon dioxide from the air…" <br> [0:33] "…then builds glucose — sugar food." | [0:39] Cross-dissolve 240 ms → Scene 5 |
| 5 | Oxygen as byproduct | [0:39 – 0:49] | 10 s | 2 × 5 s | [0:39] Cross-dissolve | [0:39] Oxygen bubbles escape leaf into air. <br> [0:45] Maya off-screen inhales | [0:39] "The leftover oxygen is released back into the air…" <br> [0:45] "…which is what we breathe." | [0:49] Match cut → Scene 6 |
| 6 | Recap | [0:49 – 0:58] | 9 s | 1 × 9 s | [0:49] Match cut | [0:49] Pull out to wide of sunny meadow, Maya in foreground looking at a leaf | [0:49] "So next time you see a leaf in the sun, you're watching a quiet factory making food — and air for you." | [0:58] Fade to black — end card |

> **Timeline check:** 58 s / 60 s — UNDER by 2 s (acceptable, within ±15%).

## Beats

[BEAT 1] hook (≈5s)
Why does a plant in a dark room droop after a few days?
<!-- visual: plant on a sunny windowsill, then match cut to same plant in dark cupboard, wilting -->

[BEAT 2] ingredients (≈10s)
Leaves are tiny food factories — they need three ingredients: sunlight, water, and air.
<!-- visual: CU on a single leaf, three labelled icons floating in: sunlight, water, air -->

[BEAT 3] capture (≈12s)
Sunlight hits a green pigment called chlorophyll. Chlorophyll captures the energy and stores it.
<!-- visual: cellular zoom into chloroplast, photons entering, glowing green pigment grains capturing them -->

[BEAT 4] synthesis (≈12s)
With that energy, the leaf splits water from the roots and pulls carbon dioxide from the air, then builds glucose — sugar food.
<!-- visual: water rising from roots, CO2 entering through stomata, glucose chains assembling -->

[BEAT 5] byproduct (≈10s)
The leftover oxygen is released back into the air — which is what we breathe.
<!-- visual: oxygen bubbles escape leaf into air, Maya off-screen inhales -->

[BEAT 6] recap (≈9s)
So next time you see a leaf in the sun, you're watching a quiet factory making food — and air for you.
<!-- visual: pull-out wide of sunny meadow, Maya in foreground looking at a leaf -->
```

---

## Rules

### Frontmatter

| Field | Required | Notes |
|---|---|---|
| `title` | yes | Declarative, not a question. Questions live in the hook narration. |
| `duration_estimate_seconds` | yes | Integer. Standard mode = match `brief.duration_seconds`. Word-to-word = computed from word count (~150 wpm English, ~135 wpm Hindi). |
| `mode` | yes | `standard` or `word_to_word`. |
| `class_level` | yes | 1..12. Drives vocab ceiling — see [storytelling-best-practices.md](./storytelling-best-practices.md). |
| `language` | yes | `English`, `Hindi`, etc. Drives wpm and Phase 2 audio-tag choices. |
| `style` | yes | Copy from `brief.style`. |
| `aspect` | yes | Copy from `brief.aspect`. Drives split-screen anchor orientation in Phase 3b. |
| `character_mode` | yes | Copy from `brief.character_mode`. Gates the Cast block. |
| `dialogues_enabled` | yes | Copy from `brief.dialogues_enabled`. Gates the Dialogue column and the "Voice and tone" bullet. |
| `annotations_enabled` | yes | Copy from `brief.annotations_enabled`. Gates the Annotations column. |
| `grounded` | yes | `true` iff `brief.chapter_source` was used. `false` for the degraded general-knowledge path. |
| `source_chapter` | when grounded | Relative path to the chapter file. |

### Strategy section

3–6 sentences. Must name: total scene count, rough duration breakdown, the pedagogical reasoning, character usage choice, the ambient mood pick. **Concrete and specific** — "engaging and educational" is not a strategy.

### Cast section

- Omit ENTIRELY when `character_mode == "none"`. Write the one-liner `Character mode: OFF — narration only.` instead.
- When `character_mode != "none"`, one `### {Name}` block per character with these bullets:
  - **Role in the video** — what they do, which scenes they appear in.
  - **Personality** — 2–4 sentences. Demeanour, energy, quirks.
  - **Voice and tone** — register, pace, accent, energy. **OMIT this bullet when `dialogues_enabled == false`.** Silent characters don't need a vocal spec, and including one tempts downstream prompts to leak speech.
  - **Looks** — visual description. Age, build, skin tone, hair, clothing piece-by-piece, footwear, signature accessories. **This bullet is load-bearing** — Phase 3a pastes it verbatim into the gpt-image-2 character-sheet prompt. Be specific (colours, fabrics, motifs), not generic.
- If character_mode is on but dialogues_enabled is false, add this line at the top of the section:
  `Dialogue: OFF — characters are visually present but silent.`

### Sound section

- **Ambient music** bullet — genre, instrumentation, tempo, emotional arc (when it swells / softens). 1–3 sentences.
- **Sound effects** bullet — density (sparse / medium / dense), categories, 2–4 example moments with timestamps `[M:SS]`.

### Scene Timeline section

Markdown table, one row per scene. Pick column set based on the brief flags:

| Dialogues | Annotations | Columns |
|---|---|---|
| off | off | `# • Scene Title • Time Range • Dur • Clips • Transition In • Keyframes • Narration • Transition Out` |
| on | off | add `Dialogue` between Narration and Transition Out |
| off | on | add `Annotations` between Narration and Transition Out |
| on | on | add both: Narration, Dialogue, Annotations, Transition Out |

**Never include a column you'd fill entirely with `(none)`.**

Column rules:

- `#` — 1, 2, 3 …
- `Scene Title` — 3–6 word slug.
- `Time Range` — `[M:SS – M:SS]` absolute in the video.
- `Dur` — `5 s` style.
- `Clips` — decomposition at the active i2v model's allowed durations. Wan 2.7 = 2–15 s; Seedance = 3–10 s. Example: `1 × 4 s`, `2 × 5 s`, `3 × 8 s`.
- `Transition In` — timestamped, e.g. `[0:00] Hard cut from black`.
- `Keyframes` — one bullet per keyframe with timestamp. Use `<br>` to separate multiple keyframes in a cell.
- `Narration` — exact VO copy with `[M:SS]` cue per sentence. Verbatim — Phase 2 reads this.
- `Dialogue` (when on) — `[M:SS] Character: "line."` or `(none)` for narration-only scenes.
- `Annotations` (when on) — `[M:SS] "Label text" — position` (e.g. `top-right`).
- `Transition Out` — timestamped outgoing transition. Final scene: `Fade to black — end card`.

After the table, one Timeline check line:
`> **Timeline check:** {sum} s / {brief duration} s — {OK ✓ / OVER by N s / UNDER by N s}.`

### Beats section

The Beats section is what [`scripts/lib/script_io.load()`](../../../scripts/lib/script_io.py) parses for Phase 2 (VO) and Phase 3b (storyboard). Each beat starts with `[BEAT N] <label> (≈Ns)` on its own line, then narration paragraph(s), then one `<!-- visual: ... -->` HTML comment.

- Narration is verbatim what Phase 2 sends to ElevenLabs (after audio-tag insertion).
- One concept per beat. If you'd write two unrelated ideas, split into two beats.
- Visual hint: verbs and nouns only — no adjectives that don't translate to motion. "leaf opens toward sunlight" ✅ — "beautiful sunny leaf" ❌.

**Beats and Scene Timeline must agree** on scene count, narration text per scene, and timing. They are two views of the same video. Drift between them is a bug.

---

## Hook patterns by class level

The opening 5-second beat sets the energy. Pick a class-appropriate hook style:

| Class | Hook style | Example |
|---|---|---|
| 1–3 | Direct sensory question | "Have you ever seen a leaf *eat the sun*?" |
| 4–6 | Counter-intuitive observation | "A plant in a dark closet wilts. Why?" |
| 7–9 | Phenomenon + invitation to explain | "Some plants survive desert summers. Most don't. The difference comes down to one molecule." |
| 10–12 | Problem statement | "If photosynthesis is 6% efficient at converting sunlight, why has 3.5 billion years of evolution not improved it?" |

**Never** open with:
- "Today we'll learn about…" (kills attention, sets a school-lecture tone).
- A definition. Definitions are the payoff, not the hook.
- The video title spoken aloud.
- A logo or brand intro.

---

## Beat count and pacing per duration

| Duration | Suggested scenes | Pacing notes |
|---|---|---|
| 15 s | 3 (5+5+5) | One concept only. Hook + setup + payoff. Cut all mechanism. |
| 30 s | 4 (5+10+10+5) | Hook + one mechanism beat + one consequence + recap. |
| 45 s | 5 | Hook + setup + 2 mechanism beats + recap. |
| 60 s | 6 (5+10+12+12+10+11) | The "ideal" — see the example above. |
| 90 s | 7–9 | Two mechanism layers + one bridge consequence + recap. |
| 120 s | 9–11 | Adds historical context or a worked example. Risk: over-stuffing. |

Visual beats need ~5–8 seconds to land. Sub-3-second beats feel rushed; sub-5 second mechanism beats are usually too dense.

---

## word_to_word mode

When `mode: word_to_word`:

- Frontmatter `grounded: true` always; `source_chapter` always points at the resolved file.
- No fabricated narration — every word comes from the chapter source. Light cleanup only (paragraph breaks, sentence boundaries, light punctuation). Don't rephrase, don't paraphrase.
- Beats are paragraph-aligned where natural, sentence-aligned when paragraphs are long.
- `duration_estimate_seconds` is computed from word count, not specified upfront.
- The Strategy section explains the pacing choice. The Cast section still applies (the chapter probably names characters; bring their visual descriptions from the chapter or from the user's earlier brief notes).
- Scene Timeline still required — Timeline check line reads `> **Timeline check:** {sum} s total (word-to-word, no target).`
