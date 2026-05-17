# Book-page QA prompt

Four binary checks, returned as JSON matching `BOOK_PAGE_SCHEMA` in `scripts/lib/visual_analyzer.py`.

| Check | Pass criterion |
|---|---|
| `transparent_background` | All non-illustration pixels have alpha 0 (or are within the alpha-stripe noise floor: <2% of border pixels with alpha >5). |
| `no_text_in_image` | No glyphs, numerals, or text artifacts anywhere. |
| `character_consistency_vs_refs` | Each character on the page matches the reference sheet's palette, features, proportions, and signature props. |
| `scene_matches_prompt` | The depicted action and setting match the page's `scene_prompt`. |

Verdict: `APPROVED` only when all four pass. Otherwise `NEEDS_REGEN` with a single-sentence `corrective_addendum` that names the specific failure (e.g. "Background gradient detected — request transparent canvas more emphatically").

The full prompt assembled at runtime by `VisualAnalyzer.analyse_book_page()` includes:
- The full prompt used for generation (so the auditor knows the intent)
- The page's `scene_prompt`
- The character brief (from `characters/description_block.md`)
- Explicit instructions to flag *any* painted background and *any* visible text

Retry loop: up to 2 retries per page. On each retry the prompt is augmented with the `corrective_addendum` from the previous QA pass.
