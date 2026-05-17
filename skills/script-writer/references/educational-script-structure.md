# Educational script structure

A canonical 60-second explainer script:

```
---
title: How photosynthesis works
duration_estimate_seconds: 58
mode: standard
class_level: 6
language: English
---

[BEAT 1] hook  (≈5s)
Why does a plant in a dark room droop after a few days?
<!-- visual: plant on a sunny windowsill vs same plant in a dark cupboard, time-lapse droop -->

[BEAT 2] setup  (≈10s)
Leaves are tiny food factories — they need three ingredients: sunlight, water, and air.
<!-- visual: three labeled icons floating into a leaf -->

[BEAT 3] mechanism A  (≈12s)
Sunlight hits a green pigment called chlorophyll. Chlorophyll captures the energy and stores it.
<!-- visual: photons entering a chloroplast, glowing pigment grains capturing them -->

[BEAT 4] mechanism B  (≈12s)
With that energy, the leaf splits water from the roots and pulls carbon dioxide from the air, then builds glucose — sugar food.
<!-- visual: H2O and CO2 molecules entering a leaf, glucose chains forming -->

[BEAT 5] consequence  (≈10s)
The leftover oxygen is released back into the air — which is what we breathe.
<!-- visual: oxygen bubbles escaping leaf into air, a child inhaling -->

[BEAT 6] recap  (≈9s)
So next time you see a leaf in the sun, you're watching a quiet factory making food — and air for you.
<!-- visual: pulled-out wide shot of sunny meadow, calm musical resolve -->
```

## Rules

- **Frontmatter:** title, duration_estimate_seconds, mode, class_level, language.
- **Beat header:** `[BEAT N] <label> (≈Ns)` — label is a free-text purpose tag.
- **Narration:** one paragraph per beat, plain prose. NO bullet lists in narration.
- **Visual hint:** one HTML comment per beat, starting with `<!-- visual:` — describes verbs and nouns only, no adjectives that don't translate to motion.
- **Length:** sum of beat duration estimates should equal `duration_estimate_seconds` ± 10%.

## word_to_word mode

Frontmatter `mode: word_to_word`. No fabricated narration — every word comes from the chapter source. Beats are paragraph-aligned. `duration_estimate_seconds` is computed from word count, not specified upfront.
