# Clip validation prompts — Claude-authored, frame-by-frame

Per-clip QA uses **Claude-authored** validation prompts, not a hardcoded Python template. Before `phase_clips.py` generates a clip, the clip-generator skill writes one file per beat at `<run-dir>/clips/clip_<NN>.validation.txt`. That file is read verbatim by `scripts/lib/visual_analyzer.analyse_clip()` and passed to `fal-ai/openrouter/router/video` (Gemini 2.5 Pro multimodal) along with the video itself.

## Why Claude authors the prompt

A static Python template can ask "is character drift present?" but it doesn't know *which* features matter for *this* beat. The skill knows:

- the exact narration sentence the clip illustrates
- the storyboard keyframe (what should be on-screen at t=0)
- the character sheet (palette, props, anatomy locks)
- the beat's `duration_ms` (how many ticks to articulate)
- the script's `aspect` (split-screen orientation rule)

So Claude produces a per-clip prompt that articulates the intended motion at second-level granularity and lists checks tailored to *this* beat. The validator gets a target, not a generic prompt.

## Output file

```
<run-dir>/clips/clip_<NN>.validation.txt
```

One file per clip. Written **before** `phase_clips.py` generates that clip. Plain text — no JSON, no fences. The Python runner appends the strict-JSON schema tail automatically if it's not already in the body.

## Meta-template

Author the file in this shape. The bracketed bits are what you fill in per beat.

```
CLIP_ID: <NN>
BEAT_LABEL: <e.g. hook | mechanism | recap>
DURATION_S: <e.g. 4.2>
ASPECT: <16:9 | 9:16 | 1:1>

CHARACTERS PRESENT IN THIS CLIP
- <name>: <species, palette, signature prop, expected pose at t=0>
- ...

INTENDED MOTION (frame-by-frame articulation)
Articulate what should happen at each tick from 0 → DURATION_S. One bullet per ~1 second.
- 0.0–1.0s: <subject> <verb> <object/direction>; <camera>; <expected expression>.
- 1.0–2.0s: <continued action>; <prop state>; <palette / lighting>.
- ...

QA CHECKS (audit every tick; flag any failure)
1. Character identity: each named character keeps the same palette, anatomy, and signature prop from t=0 to t=DURATION_S.
2. Limb count: exactly 4 limbs per quadruped, 2 per biped. Flag hybrid poses (e.g. quadruped standing on hind legs only if explicitly intended).
3. Style: stays inside <brief.style>. Flag flat/2D bleed if 3D was asked, photorealism if stylised, etc.
4. Motion sanity: motion direction matches the intended articulation above. No teleports, no jarring scene changes mid-clip.
5. Composition: subject readable at thumbnail size; no text/captions/logos overlaid.
6. Split-screen orientation (if the scene is a comparison):
   - 16:9 → vertical divider, left | right
   - 9:16 → horizontal divider, top / bottom (NEVER vertical for 9:16)
   - 1:1 → top / bottom preferred
7. Continuity to next clip: end state should be consistent with the start of clip <NN+1> if a hand-off was planned in the storyboard.

VERDICT
Approve only if every check passes. Otherwise set regen_recommendation to 'minor' (cosmetic, fixable in one re-prompt) or 'major' (structural; needs new keyframe or new beat plan) and include a 1–2 sentence corrective_addendum that names the exact fix.
```

## What the Python runner does automatically

After reading the file, `analyse_clip()`:

1. Uploads the clip to fal so the router can stream the full video.
2. Sends the prompt + video to `fal-ai/openrouter/router/video` (Gemini 2.5 Pro).
3. Appends the `CLIP_SCHEMA` JSON if the body doesn't already mention it.
4. Saves the parsed JSON to `clips/clip_<NN>_analysis.json`.
5. On router failure, falls back to the still-image contact-sheet path with the same prompt + a note that this is a fallback.

## Auto-regen loop

Each `regen_recommendation: 'major'` triggers a regen of the clip (up to `--auto-retries 2`). You may rewrite `clip_<NN>.validation.txt` between attempts to tighten checks — e.g. add a 0.0–0.3s sub-tick if the prior verdict was about an early-frame issue.

## Anti-patterns

- ❌ Generic prompts ("watch the video and audit it"). Use the meta-template; articulate motion.
- ❌ Tick spacing > 2s. Even short clips need at least 2 ticks.
- ❌ Skipping the QA CHECKS section. The check list is what makes the auditor not approve a 6-limb clip.
- ❌ Embedding strict JSON instructions in your prompt body — the Python runner appends them. Don't duplicate.
- ❌ Forgetting to write the file before generation. The runner will fall back to a generic template and quality drops.
