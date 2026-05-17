---
name: script-writer
description: Use during Phase 1 of a video run. Writes script.md from brief.json. Supports script_mode standard (original script fitting duration_seconds) and word_to_word (verbatim from a chapter source).
---

# Script Writer (Phase 1)

## Inputs

- `<run-dir>/brief.json`
- If `script_mode: word_to_word` → `<run-dir>/source/chapter.*` (file written by brief-collector)

## Output

- `<run-dir>/script.md` — a beat-by-beat structured script. Frontmatter: `title`, `duration_estimate_seconds`, `mode`. Body: beats with `[BEAT N]` headers, narration text, visual hints in `<!-- visual: ... -->` comments.

## Checklist (TodoWrite)

1. Load `brief.json`. Determine mode.
2. **standard**: write an original script structured around an opening hook (5s), 3–5 explanatory beats (40–80s combined), and a recap (5–10s). Match `duration_seconds`. Use class-appropriate vocabulary.
3. **word_to_word**: read `<run-dir>/source/chapter.*` (text or PDF — for PDF, use `scripts/lib/pdf_to_text.py`). Normalize: paragraph breaks, sentence boundaries, light punctuation cleanup. Preserve wording. Break into beats by paragraph or natural pauses. Compute and store `duration_estimate_seconds` from word count (~150 wpm).
4. Apply pedagogical guardrails from @references/educational-script-structure.md — concept-before-name, examples-before-abstractions, no jargon without definition.
5. Apply storytelling guardrails from @references/storytelling-best-practices.md.
6. Write `script.md`. Log to VPS `/prompts` with the prompt + the SHA256 of the result.

## Quality bar (self-check before exit)

- Every beat has a single concept (not three crammed together).
- No technical terms appear before being introduced.
- Visual hints describe verbs and nouns (not adjectives) — animatable.
- Total estimated duration is within ±15% of `duration_seconds` (standard mode only).

## References

- @references/storytelling-best-practices.md
- @references/educational-script-structure.md
- @../../seed/prompts/script-writer.md (the original Edustack base prompt)
