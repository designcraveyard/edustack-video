---
name: vo-generator
description: Use during Phase 2 of a video run. Generates the full voiceover from script.md via ElevenLabs (direct API, not via fal) and produces vo_timeline.json with word-level timestamps for the stitcher. Output MUST be expressive — audio tag insertion is mandatory, not optional.
---

# Voiceover Generator (Phase 2)

The job is **not** to send `script.md`'s plain narration to ElevenLabs. That produces flat, classroom-monotone audio. The job is to **author an expression-tagged version of the narration** that ElevenLabs v3 can render with real emotion, pacing, and emphasis — then call the API with the tagged text and capture word-level timestamps.

## Inputs

- `<run-dir>/script.md` — read both the Beats section (parsed by `script_io.load`) and the human-readable Strategy / Cast / Sound sections (they tell you the emotional arc, character voice characteristics, and where SFX punctuate).
- `<run-dir>/brief.json` — provides `voice_id`, `language`, `class_level`, `ambient_category`, `dialogues_enabled`.

## Outputs

- `<run-dir>/audio/full-vo.mp3` (mp3_44100_192)
- `<run-dir>/audio/vo_timeline.json` — see [references/timeline-spec.md](./references/timeline-spec.md)
- `<run-dir>/audio/vo_prompt.md` — the EXACT tagged text sent to ElevenLabs (for review / regen)

## REQUIRED: audio tag density

Plain narration is unacceptable output. Every voiceover this skill produces must satisfy these minimums:

| Position | Required tag type | Why |
|---|---|---|
| Opening beat (hook) | One emotional tag at the start — `[curious]`, `[excited]`, `[warm]`, or `[mischievously]` depending on hook style | Sets the energy. Plain delivery on a hook kills attention. |
| Each scene transition | One pacing tag — `[pause]`, `[breathes]`, or `[continues after a beat]` | Plain delivery runs scenes together; pacing tags give the listener time to register the cut. |
| Each reveal / key fact | One emphasis or pacing tag right before — `[pause]` then the fact, or `[whispers]` for intimate reveals, `[shouts]` for high-energy ones | Without this every fact lands flat. |
| Recap beat | One emotional tag that resolves — `[warm]`, `[happy]`, or `[satisfied]` | The recap is the payoff; let the voice land it. |
| Long sentences (>15 words) | Embedded `[pause]` mid-sentence at the natural breath point | Otherwise the model rushes through it and the listener loses the thread. |
| Emotional shifts inside a beat | Tag at the shift point | "Why does this happen? [pause] [curious] Because…" |

**Minimum tag density: 6 tags per minute of narration.** Fewer than that and the VO will sound like default TTS. Tag CHOICES come from the beat's role + the script's Strategy section; the COUNT is non-negotiable.

If `dialogues_enabled == true` and the script has character dialogue lines in the Scene Timeline, treat each character line as a separate tagged segment (the character's "voice and tone" from the Cast block tells you which tag to use).

## Audio tag taxonomy — inline summary

Full taxonomy in [references/elevenlabs-best-practices.md](./references/elevenlabs-best-practices.md). The tags you'll use most:

**Emotional** — `[curious]` `[excited]` `[happy]` `[warm]` `[sad]` `[nervous]` `[mischievously]` `[satisfied]`. Place BEFORE the text they affect.

**Delivery** — `[whispers]` `[shouts]` `[speaking softly]` `[loud]`.

**Pacing** — `[pause]` (brief) `[breathes]` (audible breath) `[continues after a beat]` (slight delay) `[rushed]` (fast).

**Emphasis** — Wrap a word in CAPS for stress, e.g. `Three INGREDIENTS — sunlight, water, air.` (Don't overuse — 1–2 per beat max.)

**Hindi / Hinglish** — `eleven_v3` model handles Devanagari natively. Don't romanise. Numbers and English loanwords inside Hindi can be written either way; prefer Devanagari spelling for the model to phonemize consistently (`दस` not `10`, `ऑक्सीजन` not `oxygen`).

Tags ONLY work with `model_id: eleven_v3` — other models speak them literally.

## Checklist (TodoWrite)

1. Load `script.md`. Parse with `script_io.load`. Note `language`, `mode`, `class_level`, `style`, `dialogues_enabled`, and the Cast block (for character voice cues if dialogues_enabled).
2. Read the Strategy and Sound sections of the script (human-readable, not parsed) to understand the emotional arc and SFX-cue points.
3. **For each beat, compose tagged narration** following the required-density table. Pick tag choices based on the beat's role (hook → curious/excited; setup → calm/warm; mechanism → focused/clear; consequence → satisfied/serious; recap → warm/happy). For Hindi, prefer Devanagari for numbers and loanwords.
4. **Concatenate** all tagged beats into a single tagged narration string with `<BEAT N>` markers retained inline so beat boundaries can be computed from the alignment later.
5. **Count tags before calling the API.** If `total_tags / total_narration_minutes < 6`, the prompt is too thin — go back to step 3 and add more.
6. **Save the tagged text** to `<run-dir>/audio/vo_prompt.md` BEFORE calling the API.
7. **Call** `POST /v1/text-to-speech/{voice_id}/with-timestamps` with `model_id: eleven_v3` (pinned), `text: <tagged narration>`, `output_format: mp3_44100_192`. Never downgrade — the audio tags become literal speech under `multilingual_v2` / `flash_v2_5`.
8. **Save** the MP3 to `audio/full-vo.mp3`. Parse the alignment payload into `vo_timeline.json` with `words[]`, `beats[]` (computed from `<BEAT N>` boundary positions in the tagged text vs. their alignment timestamps), `total_duration_ms`.
9. **Validate**: every beat from `script.md` is represented in `beats[]`. If word-count drift > 5% (tags stripped), flag.
10. Log to Supabase `eduplugin_events` stream `vo` — include the prompt SHA and the count of tags by category so we can later regress on density.

## Quality bar (self-check before exit)

- `vo_prompt.md` exists and contains the full tagged narration with `<BEAT N>` boundaries preserved.
- Tag count satisfies the per-minute minimum (≥6 per minute of narration). If under, REGENERATE the prompt before calling the API.
- Every beat opens or closes with at least one tag (opener for hook/setup beats, pacing tag for transitions).
- For Hindi content, the prompt uses Devanagari for numbers and key loanwords.
- `model_id: eleven_v3` confirmed in the API call.
- `vo_timeline.beats[]` has one entry per `script.md` beat.

## Word-to-word mode

In `script_mode: word_to_word`, the `duration_seconds` in brief is overridden by the VO's actual length. Subsequent phases read `vo_timeline.total_duration_ms` for timing. The tag-density rules still apply — word-to-word doesn't mean tag-free. Apply tags more sparingly when the chapter text already has strong rhetorical structure, but never zero.

## Common failure modes (avoid)

- **Sending raw `script.md` narration to ElevenLabs without tag insertion.** Produces flat default TTS. This is the pre-0.4.1 thin-output bug.
- **Inserting `[pause]` everywhere as the only tag.** Pauses without emotional or emphasis tags still sounds robotic.
- **Using `multilingual_v2` or `flash_v2_5`.** Audio tags become literal speech ("bracket curious bracket"). Hard fail.
- **Romanising Hindi.** "namaste" instead of `नमस्ते` — `eleven_v3` Devanagari phonemizer produces materially better Hindi than romanised input.
- **Tags inside CAPS emphasis or vice-versa.** `[excited]THREE` is fine; `THREE[excited]` is parsed as literal text.

## References

- [references/elevenlabs-best-practices.md](./references/elevenlabs-best-practices.md) — full audio-tag taxonomy, Hindi pronunciation fixes, voice-selection guidance.
- [references/timeline-spec.md](./references/timeline-spec.md) — the `vo_timeline.json` schema.
