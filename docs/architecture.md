# Architecture

A single run takes a topic + class level + a few options and produces `final.mp4` (and optionally `final_subtitled.mp4`). It does this through five generation phases gated by four chat-driven human reviews.

## System diagram

```
                 ┌────────────────────────────────┐
                 │        Claude Code chat        │
                 │  (the only user-facing surface)│
                 └────────────────────────────────┘
                              │
                  /create-video, gates, regen
                              │
                              ▼
                 ┌────────────────────────────────┐
                 │      orchestrator (skill)      │◀──── run.json (per-run state machine)
                 └────────────────────────────────┘
                              │
        ┌──────────┬──────────┼──────────┬──────────┬──────────┐
        ▼          ▼          ▼          ▼          ▼          ▼
   brief-collector  script-writer  vo-generator  character…  storyboard…  clip-generator  stitcher
        │              │             │              │              │             │           │
        ▼              │             ▼              │              ▼             ▼           ▼
   localhost      brief.json   ElevenLabs       fal.ai            fal.ai       fal.ai i2v   MoviePy
   Node form                  (direct API,     gpt-image-2       gpt-image-2  Seedance 1.5  + ffmpeg
                              with_timestamps) rich sheet (16:9)  OR Nano BB-2 Pro          local
                                                or skip (none)
                                                                                          │
                              ┌───── visual analysis (Gemini 2.5 Pro via fal-ai/any-llm) ─┘
                              │
                              ▼
                       <run-dir>/*.png, *.mp4, *_analysis.json

                              ┌───── observability (best-effort, async) ─────┐
                              │                                              │
                              ▼                                              ▼
                    Edustack Supabase                              <run-dir>/logs/local.jsonl
                    public.eduplugin_events                        (fallback when Supabase unreachable)
                    one row per event, six streams
                              │
                              ▼
                    EduStack-Platform Next.js viewer
                    /admin/eduplugin/runs/<run_id>
```

## Two persistence layers

| Layer | Lives at | Owns | Failure mode |
|---|---|---|---|
| **Run state** | `<run-dir>/run.json` (user disk) | Phase status, gate decisions, regen comments. Single source of truth. | If lost, run is unrecoverable — but `final.mp4` is independently complete. |
| **Observability** | `public.eduplugin_events` in the Edustack Supabase project | Logs, prompts, analyses, gate decisions, heartbeats, chat | Best-effort. Pipeline never blocks. On Supabase failure → `<run-dir>/logs/local.jsonl` fallback. |

## Three trust boundaries

1. **User machine ↔ fal.ai / ElevenLabs** — API keys live in `<output>/.config/*.key` (mode 0600). Local Python calls these directly.
2. **User machine ↔ Supabase** — Supabase anon key in `<output>/.config/supabase.anon`. Supabase gets metadata refs only (paths, sha256, prompt sha, latency) — never artifacts and never the upstream API keys. Anon-key writes; reads gated by the EduStack-Platform admin route.
3. **Browser ↔ Brief server** — Localhost only (`127.0.0.1:0`, random port). Untrusted input is treated as such (no `innerHTML`).

## Pipeline phases

### Phase 0 — Brief collection
A localhost Node form posts a `brief.json` matching the [Edustack `runs.brief` shape](../skills/brief-collector/references/brief-schema.md). The schema lets us cross-port projects between the web platform and this plugin.

### Phase 1 — Script
Two modes:
- **standard**: original script generated to fit `duration_seconds`.
- **word_to_word**: verbatim from `<run-dir>/source/chapter.*`; `duration_seconds` is ignored and derived from VO instead.

Output: `script.md` with frontmatter + beat headers + `<!-- visual: ... -->` hints.

### Phase 2 — VO + timeline
ElevenLabs direct (not via fal) for word-level timestamps. Output is `audio/full-vo.mp3` and the canonical `audio/vo_timeline.json` that drives all later timing.

### Phase 3a — Character setup
Branches on `character_mode`:
- **human** / **abstract** → `fal-ai/gpt-image-2` rich-template sheet (16:9 landscape, `quality: high`) + Gemini 2.5 Pro audit with auto-regen (up to 2×). Writes 4 outputs to `<run-dir>/characters/`:
  - `sheet.png` — the generated sheet image.
  - `sheet_prompt.md` — full prompt sent + style descriptor + verbatim character descriptions (audit trail).
  - `analysis.json` — Gemini QA report (`verdict`, `regen_reason`, `corrective_addendum`) plus `_qa_history` of every regen attempt.
  - `descriptions.json` — per-character verbatim paragraphs that downstream phases (3b + 4) paste IDENTICALLY into every prompt's CHARACTERS section. **This is the consistency contract.**
- **none** → skipped; `characters/description_block.md` is written instead and prepended to every later prompt.

The descriptions on the sheet PNG, in `descriptions.json`, and in every downstream prompt are byte-for-byte identical — that's how character identity locks across all beats and clips.

### Phase 3b — Storyboard / keyframes
Branches on `image_mode`:
- **storyboard_panel** → one multi-panel sheet via gpt-image-2, then sliced locally with PIL.
- **per_keyframe** → one Nano Banana 2 image per beat, character-sheet-conditioned.

After every keyframe: Gemini analyzes against the prompt. Up to 2 auto-corrective regens before escalating to Gate 3.

### Phase 4 — Clips
Seedance 1.5 Pro i2v per beat, seeded by the keyframe and timed by `vo_timeline.beats[N].duration_ms`. Each clip gets a frame-by-frame Gemini continuity report in `clip_N_analysis.json`. Up to 2 auto-corrective regens before Gate 4.

### Phase 5 — Stitch
MoviePy reads clip analyses (not just the clips) to choose transitions: cuts on motion boundaries, dissolves on calm beats, whip-pans on big scene changes. VO drives cut points — the cut for beat N happens at the last word's `end_ms`, not the clip's natural end. Final outputs: `final.mp4` and optionally `final_subtitled.mp4`.

## Gate UX

Each gate emits a chat message of the form:

```
Phase 3 — Storyboard ready. Review these and reply.

skills/.../storyboard/keyframes/beat_01.png
skills/.../storyboard/keyframes/beat_02.png
...

Reply:
  approve
  regen storyboard beats 5-7: <comment>
  /create-video-regen storyboard beats 5-7
```

Claude Code linkifies the file paths. The user reviews in their OS file explorer / preview app and replies in chat. Approval advances the orchestrator; `regen …` triggers selective regeneration and persists a `gate_review_comments`-shaped entry in `run.json`.

## Update flow

Public repo, fast-forward only. `/plugin-update`:

1. Refuse if any run is in flight or working tree is dirty.
2. `git fetch origin main`.
3. Show user the `git log HEAD..origin/main` + relevant `CHANGELOG.md` slice.
4. `git merge --ff-only`.
5. If `requirements.txt` changed, `uv pip sync` against `<output>/.venv`.
6. Print new SHA.

`/plugin-rollback <sha>` exists as the escape valve.
