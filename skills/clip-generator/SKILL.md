---
name: clip-generator
description: Use during Phase 4 of a video run. Generates one i2v clip per beat (Wan 2.7 for human characters, Seedance 1.5 Pro otherwise), seeded by each beat's keyframe. Per-clip validation prompts are MANDATORY — phase_clips.py refuses to start without them.
---

# Clip Generator (Phase 4)

## Inputs

- `<run-dir>/storyboard/storyboard.json` (post-Gate-3 approved; includes structured `anchors[]` per beat where applicable)
- `<run-dir>/storyboard/keyframes/beat_*.png`
- `<run-dir>/audio/vo_timeline.json` (per-beat durations)
- `<run-dir>/characters/descriptions.json` (verbatim per-character paragraphs) or `<run-dir>/characters/description_block.md` (none-mode equivalent)
- `<run-dir>/brief.json` — provides `character_mode` (routes the model), `dialogues_enabled` (gates speech suppression), `style`, `aspect`

## Outputs

- `<run-dir>/clips/clip_NN.mp4` — one per beat, zero-padded, duration ≈ `vo_timeline.beats[N].duration_ms`
- `<run-dir>/clips/clip_NN_analysis.json` — frame-by-frame continuity report
- `<run-dir>/clips/clip_NN.validation.txt` — Claude-authored QA prompt (**precondition**, written BEFORE generation)
- `<run-dir>/clips/summary.json` — one row per beat with `motion_intensity`, `needs_review` flag

## HARD PRECONDITION: per-clip validation prompts

`phase_clips.py` reads `clip_NN.validation.txt` for every beat. If the file is missing, the runner falls back to a generic template — and you'll get exactly the drift / anatomy / anchor-swap bugs the validation system was built to catch. **Authoring these files is not optional, not a "best practice" — it's the precondition that makes the QA loop work.**

Order of operations is strict:

```
  for each beat:
    1. Claude writes clips/clip_NN.validation.txt
  ↓
  2. Invoke phase_clips.py — it reads the .validation.txt files and runs the model + QA
  ↓
  3. Review summary.json, surface Gate 4
```

If you call `phase_clips.py` with any `clip_NN.validation.txt` missing, the runner logs `clip {NN} QA using GENERIC FALLBACK` — that's the signature of skipping step 1.

## Validation prompt meta-template — inline summary

Full meta-template + anti-patterns in [references/clip-validation-prompts.md](./references/clip-validation-prompts.md). Every `clip_NN.validation.txt` must include these sections, in this order:

```
CLIP_ID: <NN>
BEAT_LABEL: <hook | setup | mechanism | consequence | recap>
DURATION_S: <e.g. 4.0>
ASPECT: <16:9 | 9:16 | 1:1>

CHARACTERS PRESENT IN THIS CLIP
- <name>: <species, palette, signature prop, expected pose at t=0>
- ...

INTENDED MOTION (one bullet per ~1 second tick)
- 0.0–1.0s: <subject> <verb> <object>; <camera>; <expression>.
- 1.0–2.0s: <next tick>...
- ... up to DURATION_S

QA CHECKS (audit every tick)
1. Character identity locked across all frames (palette, anatomy, signature prop).
2. Limb count correct (4 per quadruped, 2 per biped — flag hybrids).
3. Style matches brief.style (no 3D bleed in 2D, no flat in Pixar, etc.).
4. Motion matches the INTENDED MOTION above. No teleports, no jarring mid-clip cuts.
5. Composition readable at thumbnail; no text/captions/logos overlaid.
6. Split-screen orientation (when applicable):
   - 16:9 → vertical divider (left | right)
   - 9:16 → horizontal divider (top / bottom) — NEVER vertical for 9:16
   - 1:1  → top / bottom preferred
7. Anchors held (when the beat has anchors[] in storyboard.json): every anchored element stays on its named side from t=0 to t=DURATION_S.

VERDICT
Approve only if every check passes. Otherwise set regen_recommendation to
'minor' or 'major' and include a 1–2 sentence corrective_addendum naming
the exact fix.
```

Tick spacing > 2 seconds is too coarse — even a 4 s clip needs at least 4 ticks. Generic prompts ("watch the video and audit it") will be flagged by the runner. Do NOT embed the strict-JSON schema in your prompt body — the Python runner appends it.

## Checklist (TodoWrite)

1. **Author all `clip_NN.validation.txt` files first.** One per beat in `script.beats`. Use the meta-template above. Pull intended motion from the beat's narration + the storyboard keyframe + the Scene Timeline transitions. Pull character identity locks from `descriptions.json`. Reference any `anchors[]` from storyboard.json verbatim in QA check 7.
2. **Verify all files exist before invoking the runner.** A bash one-liner: `ls clips/clip_*.validation.txt | wc -l` should equal the beat count. If not, you skipped a step.
3. **Invoke `phase_clips.py`** — do NOT call fal inline. The runner:
   - reads `storyboard.json` (incl. structured `anchors`)
   - routes the i2v model by `brief.character_mode`: `"human"` → `models.yaml:video_i2v_human` (Wan 2.7 I2V on fal, 720p default); anything else → `models.yaml:video_i2v` (Seedance 1.5 Pro, 1080p default)
   - injects a dialogue-suppression audio direction into every prompt unless `brief.dialogues_enabled === true`
   - fans clip generation across `<stage>.concurrency` threads (default 4) — beats are independent
   - uploads each keyframe via `fal_client.upload_file()`
   - runs the Claude-authored validation prompt through `fal-ai/openrouter/router/video`
   - retries up to 2× with corrective addenda
   - saves zero-padded `clip_NN.mp4` + `clip_NN_analysis.json`

   ```bash
   "$OUTPUT/.venv/bin/python" -m scripts.phase_clips --run-dir "$RUN_DIR"
   ```

   Inline `fal_client.subscribe` calls are forbidden — they skip retry logic, anchor injection, and validation-prompt loading, and produce non-zero-padded filenames that break the stitcher.

4. **Auto-correct loop** (handled inside `phase_clips.py`, max 2 retries per clip):
   - When analysis flags drift / anatomy / anchor swap, the runner appends a corrective addendum and regenerates.
   - You may rewrite `clips/clip_NN.validation.txt` between human-driven `/create-video-regen` calls to tighten checks; the runner reads the latest version on each run. Add a finer-grained tick (e.g. 0.0–0.3s) if the prior verdict was about an early-frame issue.
   - If still flagged after 2 tries → `needs_review: true` lands in `summary.json` and Gate 4 surfaces.

5. **Surface for Gate 4.** Walk the user through `summary.json` — flag any `needs_review: true`, show motion intensities (used by the stitcher to pick transitions).

## Quality bar (self-check before exit)

- `clip_NN.validation.txt` exists for EVERY beat in `script.beats`. Missing files = blocked.
- Each `.validation.txt` has all five sections (CLIP_ID / CHARACTERS / INTENDED MOTION / QA CHECKS / VERDICT) and tick spacing ≤ 2 s.
- Character names and signature props in each `.validation.txt` match `descriptions.json` exactly (no paraphrasing).
- All four QA-check sections (identity / limbs / style / motion) plus the conditional ones (split-screen, anchors) are present.
- `clips/summary.json` has one row per beat with `motion_intensity` populated.
- For human-character runs (`character_mode == "human"`), confirm `phase_clips.py` logged `model=fal-ai/wan/v2.7/image-to-video` — if it logged Seedance, brief routing failed.

## Common failure modes (avoid)

- **Skipping `.validation.txt` authoring and relying on the generic fallback.** This is the dominant failure mode — produces vague QA reports, lets drift / wrong-anatomy / anchor-swap slip through to the final video.
- **Calling `fal_client.subscribe` inline instead of the runner.** Skips retry logic, anchor injection, dialogue suppression, model routing. Bypasses every QA improvement.
- **Embedding the strict-JSON schema inside the prompt body.** The runner appends it; duplication confuses the auditor.
- **Generic intended-motion bullets.** "Character moves around the scene" gives the auditor nothing to check. Be tick-specific.
- **Forgetting to reference storyboard anchors in QA check 7.** If the beat has `anchors[]` and your validation prompt doesn't mention them, anchor swaps go unflagged.

## References

- [references/clip-prompting.md](./references/clip-prompting.md) — style descriptor table, BEFORE-state rules, character description verbatim rule.
- [references/clip-validation-prompts.md](./references/clip-validation-prompts.md) — full meta-template, anti-patterns, runner contract.
- [references/transitions.md](./references/transitions.md) — transition cues to plan ahead for the stitcher.
