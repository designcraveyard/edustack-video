---
name: script-writer
description: Use during Phase 1 of a video run. Writes script.md from brief.json. Supports script_mode standard (original script fitting duration_seconds) and word_to_word (verbatim from a chapter source). Output is a RICH structured document (Strategy + Cast + Sound + Scene Timeline + Beats) — minimal beats-only output is NOT acceptable.
---

# Script Writer (Phase 1)

## Inputs

- `<run-dir>/brief.json`
- **`brief.chapter_source`** when present (collected by brief-collector in BOTH modes since 0.4.0). Resolution:
  - `kind: "text"` → `ref` is an absolute path to `<run-dir>/source/chapter.txt` (server persists pasted text there).
  - `kind: "file"` → `ref` is an absolute path on the user's machine. PDFs go through `scripts/lib/pdf_to_text.py`; `.txt` / `.md` read directly.
  - `kind: "url"` → `ref` is a URL. Fetch with `requests` (PDF or HTML); strip nav/footer if HTML.
- **Standard mode**: `chapter_source` is OPTIONAL but strongly recommended. Absent → degraded path (write from `topic` + general knowledge; mark `grounded: false` in frontmatter). Present → script MUST be grounded in the chapter — every factual claim traceable, examples lifted from the source, no invented data.
- **Word-to-word mode**: `chapter_source` is REQUIRED. Orchestrator refuses to enter Phase 1 without it.

## Output — REQUIRED structure

A single file: `<run-dir>/script.md`. Sections appear in this exact order. **Do not omit Strategy, Cast (when characters are on), Sound, or Scene Timeline.** They are the contract downstream phases rely on.

```
---
title: <video title>
duration_estimate_seconds: 60
mode: standard | word_to_word
class_level: 5
language: English | Hindi | ...
style: <copy from brief>
aspect: <copy from brief>
character_mode: human | abstract | none
dialogues_enabled: true | false
annotations_enabled: true | false
grounded: true | false       # true iff chapter_source was used
source_chapter: source/chapter.txt   # only when grounded=true
---

# {Video title}

## Strategy

3–6 sentences. Name the scene count, the rough duration breakdown, the
pedagogical reasoning (pacing, hook choice, character usage, transition
vocabulary). Concrete and specific — not "engaging and educational."

## Cast                            <!-- omit ENTIRELY when character_mode == "none" -->

If character_mode == "none", write a single line instead of this section:
`Character mode: OFF — narration only.`

If character_mode is on but dialogues_enabled is false, add this line at
the top of the section:
`Dialogue: OFF — characters are visually present but silent.`

Then one `### {Character name}` block per character with these bullets:

### Aarav
- **Role in the video**: one sentence — what they do in the story.
- **Personality**: 2–4 sentences — demeanour, energy, quirks.
- **Voice and tone**: how they speak — register, pace, accent, energy.
  **OMIT this bullet entirely when dialogues_enabled == false.** Silent
  characters don't need a vocal spec, and including one tempts downstream
  prompts to leak speech.
- **Looks**: visual description — age, build, skin tone, hair, clothing
  piece-by-piece, footwear, signature accessories. This bullet is
  load-bearing — Phase 3a pastes it verbatim into the character-sheet
  generator. Be specific (colours, fabrics, motifs), not generic.

## Sound

- **Ambient music**: genre, instrumentation, tempo range, emotional arc
  (when it swells / softens). One bullet, 1–3 sentences.
- **Sound effects**: density (sparse / medium / dense), categories, and
  2–4 example moments with their approximate timestamps.

## Scene Timeline

A Markdown table — one row per scene. Time-sensitive elements carry [M:SS]
timestamps. Pipe characters inside cells must be escaped as `\|`.

Choose ONE of these column sets based on the brief's flags:

When dialogues_enabled=false AND annotations_enabled=false (most common):

| # | Scene Title | Time Range | Dur | Clips | Transition In | Keyframes | Narration | Transition Out |

When dialogues_enabled=true AND annotations_enabled=false:

| # | Scene Title | Time Range | Dur | Clips | Transition In | Keyframes | Narration | Dialogue | Transition Out |

(Add Annotations column to either set when annotations_enabled=true.)

Column rules:
- **#**: 1, 2, 3 …
- **Scene Title**: 3–6 word slug.
- **Time Range**: `[M:SS – M:SS]` absolute in the video.
- **Dur**: `4 s` style.
- **Clips**: decomposition into clips at the active video model's allowed
  durations. Wan 2.7 = 2–15 s; Seedance = 3–10 s. Example: `1 × 4 s`,
  `2 × 5 s`, `3 × 8 s`.
- **Transition In**: timestamped, e.g. `[0:00] Hard cut from black`.
- **Keyframes**: one bullet per keyframe with timestamp, e.g.
  `[0:00] Wide: girl by window`<br>`[0:06] CU: rain on glass`.
  Use `<br>` to separate multiple keyframes in a cell.
- **Narration**: exact VO copy with [M:SS] cue per sentence. Write
  verbatim — vo-generator reads this exactly.
- **Dialogue** (only when included): `[0:04] Aarav: "Their line."` or
  `(none)` for narration-only scenes.
- **Annotations** (only when included): `[0:05] "Label text" — top-right`.
- **Transition Out**: timestamped outgoing transition, e.g.
  `[0:22] Cross-dissolve → Scene 3`. For the final scene write
  `[M:SS] Fade to black — end card`.

After the table, add one Timeline check line:
> **Timeline check:** {sum} s / {brief duration} s — {OK ✓ / OVER by N s / UNDER by N s}.

For word_to_word mode where there's no target duration, write:
> **Timeline check:** {sum} s total (word-to-word, no target).

## Beats

This section is what `scripts/lib/script_io.py` parses for downstream
phases. Each beat MUST start with a `[BEAT N]` header on its own line —
the parser keys on this. Include a label and an estimated duration in
parentheses. Then narration paragraph(s). End each beat with one
`<!-- visual: ... -->` comment summarising what the keyframe / clip should
show (verbs and nouns, not adjectives — clip-generator extracts this).

[BEAT 1] hook (≈5s)
Narration sentence(s).
<!-- visual: a child's wide curious eyes fill the frame, camera zooms out to reveal iron prison bars -->

[BEAT 2] concept (≈18s)
Narration sentence(s).
<!-- visual: ... -->

…and so on. The Scene Timeline above and the Beats here MUST describe the
SAME video — same scene count, same narration, same timing. Beats are the
machine-parseable mirror of the Timeline.
```

## Checklist (TodoWrite)

1. Load `brief.json`. Note `script_mode`, `character_mode`, `dialogues_enabled`, `annotations_enabled`, `style`, `aspect`, `language`, `class_level`, `duration_seconds`.
2. **Resolve `chapter_source` if present** (both modes). For `kind: "text"`/`"file"` read from disk; for `"url"` fetch (PDFs and HTML pages both supported; strip nav/footer for HTML). Cache the normalized chapter text at `<run-dir>/source/chapter.txt` if it isn't already there. Word-to-word mode: if `chapter_source` is missing, ABORT — orchestrator should have caught this.
3. **Pick scene count and clip decomposition.** Match the active video model's allowed clip durations (Wan 2.7 for human mode = 2–15 s; Seedance for abstract/none = 3–10 s; see [seed/prompts/script-writer.md](../../seed/prompts/script-writer.md) for the full per-model cheat sheet). Scene durations must sum to `duration_seconds` (standard) or to whatever the chapter length implies (word_to_word).
4. **Write the Strategy section first** — it forces you to commit to the structure before drafting prose.
5. **Write the Cast section** (when `character_mode != "none"`) with one block per character. The **Looks** bullet is what Phase 3a pastes into gpt-image-2 — be specific.
6. **Write the Sound section** — pick an ambient vibe consistent with `brief.ambient_category` and the topic mood.
7. **Write the Scene Timeline table** — pick column set based on the dialogues/annotations flags. Add Timeline check at the end.
8. **Write the Beats section** — one `[BEAT N]` header per scene, narration paragraph(s) verbatim, single `<!-- visual: ... -->` comment per beat. The Beats and the Timeline MUST agree on scene count, narration text, and timing.
9. Apply pedagogical guardrails from @references/educational-script-structure.md — concept-before-name, examples-before-abstractions, no jargon without definition.
10. Apply storytelling guardrails from @references/storytelling-best-practices.md.
11. Self-check against the Quality bar below. Re-edit if any item fails.
12. Write `<run-dir>/script.md`. Surface it to the user before the orchestrator advances.

## Quality bar (self-check before exit)

- Frontmatter has `grounded` and (when grounded) `source_chapter`.
- Strategy, Sound, Scene Timeline, and Beats are all present.
- Cast is present iff `character_mode != "none"`. Each cast member has at least Role, Personality, Looks. Voice and tone is present iff `dialogues_enabled == true`.
- Scene Timeline column set matches the dialogues/annotations flags. No column is entirely `(none)`.
- Beats and Scene Timeline agree: same scene count, same narration text per scene, same timing.
- Every beat has a single concept (not three crammed together).
- No technical terms appear before being introduced.
- Visual hints describe verbs and nouns, not adjectives — animatable.
- Total estimated duration is within ±15% of `duration_seconds` (standard mode only).
- For word_to_word, narration preserves the chapter's wording (light cleanup only — no rephrasing).

## Common failure modes (avoid)

- **Emitting only `[BEAT N]` blocks with no Cast / Strategy / Timeline.** This is the pre-0.4.0 thin format. It breaks downstream phases (no Cast → character-sheet-generator invents characters from `topic` → drift; no Timeline → clip-generator has no anchors / transitions).
- **Writing Cast as one prose paragraph instead of `### {Name}` blocks with the four bullets.** The parser at [`scripts/lib/script_io.parse_cast`](../../scripts/lib/script_io.py) keys on the bullet labels (Role / Personality / Voice and tone / Looks) — prose won't parse.
- **Including a Dialogue column or Voice-and-tone bullet when `dialogues_enabled == false`.** It encourages downstream prompts to leak speech.
- **Skipping the `[BEAT N]` Beats section because the Scene Timeline already has narration.** The Timeline is informational; the Beats section is what `script_io.load()` parses for `vo-generator`, `storyboard-generator`, and `clip-generator`. Both must be present.

## References

- @references/storytelling-best-practices.md
- @references/educational-script-structure.md
- @../../seed/prompts/script-writer.md — the original Edustack base prompt; consult its per-model clip-duration cheat sheet and column rules when in doubt.
