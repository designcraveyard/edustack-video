# Changelog

All notable changes to `edustack-video` will be documented here. Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.8.0 — 2026-05-26

### Visual localhost template picker for every book path

Book layout selection is now a **polished localhost gallery** instead of picking template names blind from chat. Ported from the `layout-gen` / `layout-templates-web` showcase: each of the 9 templates shows its real reference images (click to zoom in a lightbox), a description + nickname, a meta grid (text position / wrapping / background / aspect·canvas), a frequency bar, tags, and a wireframe that reframes with a Portrait/Landscape toggle. The user selects 2–4 and hits Confirm.

- **New skill `book-template-picker`** — a zero-dependency Node stdlib HTTP server (same lifecycle pattern as the brief-collector server): binds `127.0.0.1:0`, opens the browser, serves the gallery, writes the selection to a handshake JSON, and exits on `PICKER_OK`. Reference thumbnails are served straight from canonical `seed/template-references/` via a guarded `/refs/<path>` route — **no duplicated copy** of the 5 MB of refs.
- **Wired into all three book paths.** `/create-book` (book-standalone) and `/create-book-from-keyframes` (book-from-keyframes) now launch the picker for their template-selection step, with a chat-based fallback if no browser is available. The in-video path (`book-plan`, fed by the brief form) reads `brief.book.templates` as before, and can re-open the picker on request.
- **Brief-form gallery upgraded** to match: richer cards with a frequency badge, nickname, accent ring + checkmark on selection, and larger reference thumbnails.
- **Two-image prompting + attachments verified unchanged** — `scripts/lib/book_layout_renderer.py` already sends `[layout_ref (IMAGE 1), content_ref (IMAGE 2), character_sheets (IMAGE 3+)]` capped at gpt-image-2's 4-image limit, and `phase_book_standalone.py` correctly aggregates plan-level + per-page `character_refs`. No renderer changes needed.

### Files

- `skills/book-template-picker/SKILL.md` — new skill (launch instructions, handshake contract, fallback).
- `skills/book-template-picker/server/server.mjs` — zero-dep server (`--run-dir` / `--out` / `--min` / `--max` / `--page-count` / `--title` / `--no-open`).
- `skills/book-template-picker/server/public/{index.html,styles.css,picker.js,templates.json}` — the gallery UI + display metadata (picker's source of truth).
- `skills/book-template-picker/server/public/wireframes/{1..9}.svg` — copied from the brief-collector wireframes.
- `skills/book-standalone/SKILL.md`, `skills/book-from-keyframes/SKILL.md`, `skills/book-plan/SKILL.md` — launch the picker / point at it.
- `commands/create-book.md`, `commands/create-book-from-keyframes.md` — flow updated to mention the picker.
- `skills/brief-collector/server/public/{form.js,styles.css,templates/manifest.json}` — richer book-template cards.
- `plugin.json` — registered `skills/book-template-picker`; version → 0.8.0.

### Invariants updated

New CLAUDE.md invariant #10: template selection is a visual localhost picker, and the **template ids MUST stay identical** across the three manifests — `seed/template-references/manifest.json` (renderer), `skills/book-template-picker/server/public/templates.json` (picker display), and `skills/brief-collector/server/public/templates/manifest.json` (brief-form mirror). Never duplicate the reference images.

### Verification

The picker server was smoke-tested end-to-end (every endpoint, path-traversal guard, POST→handshake→clean exit) and visually verified in a headless Chromium via Playwright (all 39 reference thumbnails load; selection state, lightbox open/close, and orientation toggle confirmed). Two CSS bugs caught and fixed during visual review: a `[hidden]` lightbox that an over-broad `display:flex` class kept permanently visible (whole page dimmed), and lazy-loaded thumbnails that could render blank — switched to eager loading.

## 0.7.0 — 2026-05-25

### Clip generation: no auto-regen, sequential, job-id persistence, Seedance pinned to 720p

Four coupled changes to Phase 4 (`scripts/phase_clips.py`), driven by a need to keep clip generation predictable and recoverable.

- **No automatic regeneration.** Clips are generated exactly once. The prior ≤2 auto-corrective regen loop is removed. QA still runs on every clip; a `major` verdict now logs a warning and sets `needs_review: true` in `clips/summary.json` for Gate 4 — the user decides whether to regenerate (via `/create-video-regen`). `minor`/clean verdicts are recorded in the analysis JSON but not flagged.

- **Seedance resolution hard-pinned to 720p.** `_resolution_for` now forces `720p` for `fal-ai/bytedance/seedance/v1.5/pro/image-to-video` regardless of any `models.yaml:video_i2v.resolution` override. Wan 2.7 (human mode) still honours its configured `720p`.

- **fal job ids persisted to `run.json`.** `FalClient.run` gained an `on_enqueue` callback (wired to `fal_client.subscribe`). `phase_clips` writes `{endpoint, request_id, status, updated_at}` to `run.json` (`items.clip_jobs[<id>]`) the instant each clip is enqueued — before the generation wait — via new `RunState.record_clip_job`. A long-running or interrupted generation can now be recovered by `request_id` instead of losing the thread. Status transitions enqueued → complete/failed.

- **Strictly sequential generation.** The `ThreadPoolExecutor` fan-out is removed; beats are processed one at a time, in order. The `--concurrency` and `--auto-retries` flags and the `models.yaml:<stage>.concurrency` knob are gone. Sequential keeps the `run.json` job-id writes race-free and respects fal's new-account queue cap (2).

### Files

- `scripts/phase_clips.py` — removed retry loop, `ThreadPoolExecutor`, `--concurrency`/`--auto-retries`; sequential beat loop; `_resolution_for(model, stage, smoke)` hard-pins Seedance to 720p; `on_enqueue` persists job ids.
- `scripts/lib/fal_client.py` — `run()` accepts optional `on_enqueue` callback forwarded to `fal_client.subscribe`.
- `scripts/lib/run_state.py` — new `record_clip_job()` writing `items.clip_jobs`.
- `seed/models.yaml` — documented Seedance 720p hard-pin; removed dead `concurrency` knobs.
- Docs: CLAUDE.md decisions table (human-video / sequencing / no-auto-regen rows), `skills/clip-generator/SKILL.md`, `skills/clip-generator/references/clip-validation-prompts.md`.

## 0.6.2 — 2026-05-19

### Book page output is now opaque + full-bleed + checker-pattern-free

Three coupled fixes after 0.6.0 caught real failure modes during a live test on the herbivore-vs-carnivore run:

- **Checker pattern in text zone (visible grid artifact).** Root cause: `gpt-image-2` was being asked to "leave the text zone transparent" (via prompt) AND was being passed `background: "transparent"` (via fal payload). The model interpreted this as "paint a literal checkerboard pattern in that area" rather than actually outputting transparent pixels. The grid was baked INTO the painted RGBA. Fix: dropped both. The prompt now asks for a "soft light area in a single pale colour appropriate to the scene (light cream, light pastel sky, soft warm beige) — NO checker pattern, NO grid pattern". The fal payload no longer sends `background: "transparent"`. Output is opaque on every pixel; the designer overlays text on the painted text zone in InDesign.

- **Blank space on the canvas (image placed left/right with margins).** Root cause: `book_canvas.compose()` was using per-template `position` / `scale` / `margin` rules to place a fractional-size image somewhere on the canvas — but the gpt-image-2 output ALREADY contains the composed page layout (text zone, bleed, illustration, all baked in). The legacy positioning produced redundant blank space because the image's own text zone was being placed inside ANOTHER positional offset. Fix: `compose()` now does a single cover-scale + center-crop to fill the canvas. Any 0.5–6% aspect mismatch between gpt-image-2's preset and A4P/A3L is absorbed as edge crop. The per-template `RULES` dict's geometry fields are kept only for backwards-compatible `canvas_for()` lookups (A4P vs A3L).

- **White-flatten at print time.** RGB output, not RGBA. Even when gpt-image-2 returns some residual alpha, `book_canvas.compose()` composites onto a white background and returns RGB. Files open in any image viewer without checker-pattern transparency rendering. Designers overlay text on solid white.

### Files

- `scripts/lib/book_layout_renderer.py` — dropped `transparency_directive`; added text-zone-fill directive ("soft light area, no checker, no grid"); `RenderRequest.transparent_bg` default flipped to `False`.
- `scripts/lib/fal_client.py` — removed `"background": "transparent"` from `gpt_image_2_book_page` payload.
- `scripts/lib/book_canvas.py` — `compose()` now does cover-scale + center-crop + flatten-to-white; legacy `position`/`scale`/`margin` rules retained in `RULES` only for backwards-compat `canvas_for()` lookups.

### Invariants updated

CLAUDE.md invariant 9 (and the corresponding "Don't do" line) was: "Book pages are RGBA with transparent BG." Now: "Book pages are opaque RGB on a white-flattened canvas with a painted soft-light text zone." The Book mode row in the decisions table updated accordingly.

### Aspect-fit caveat (worth knowing)

gpt-image-2's `landscape_4_3` preset is 1024×768 (aspect 1.333), A3L is 4961×3508 (aspect 1.414) — a 6% mismatch. The cover-scale crops ~6% off the long edge, which gives a natural full-bleed look (illustration extends to the page edges). For templates where precise composition matters (`split-layout`, `illustrated-border`) this could clip important content; for `full-bleed-with-text-zone`, `full-spread-no-text`, and `spread-scene-plus-spots` it's the right behaviour. If we hit composition-clipping in production, the renderer can be switched to explicit `{width, height}` dims at gpt-image-2's 3840 max-edge limit for aspect-exact output — ~1.5× slower and more expensive per call.

## 0.6.0 — 2026-05-19

### Book pipeline overhaul — two-image prompting + standalone book runs

Ported the layout-gen plugin's "two-image prompting is king" approach into edustack-video's book pipeline. Every book page is now rendered through a **shared layout renderer** ([scripts/lib/book_layout_renderer.py](scripts/lib/book_layout_renderer.py)) that sends:

- **IMAGE 1** — the template's LAYOUT REFERENCE from [seed/template-references/](seed/template-references/) (bundled, 39 reference images across the 9 templates, ~5 MB).
- **IMAGE 2** — the CONTENT REFERENCE (a video keyframe / a user-uploaded reference image).
- **IMAGE 3+** — optional character sheets for consistency anchoring.

Prompt framing explicitly tells gpt-image-2: "use LAYOUT from IMAGE 1, CONTENT/STYLE from IMAGE 2." Without that, the model mixes layout and content guidance unpredictably and the output looks generic. With it, the output respects the template's text-zone composition while holding the source's characters and style.

**New entry points and renderers:**

- **`/create-book`** — NEW. Video-less standalone book runs. User provides a mini-brief (topic / class / language / style), chapter text or reference images, picks templates from the 9, plans per page. No video generation at all. New skill at [skills/book-standalone/SKILL.md](skills/book-standalone/SKILL.md), new runner at [scripts/phase_book_standalone.py](scripts/phase_book_standalone.py).
- **`/create-book-from-keyframes`** — UPGRADED. Default mode is now layout-renderer (was birefnet-only in 0.5.0). Each keyframe is sent as IMAGE 2 to gpt-image-2 alongside the template's layout reference; result is a layout-composed page with the video's characters and style. The legacy birefnet-only path is preserved per-page via `remove_background: true` for users who want the keyframes cut out and used verbatim (~Rs 2/page vs ~Rs 15/page for the renderer path).
- **Default Phase B2 (book-render)** — UPGRADED. `phase_book_render.py` now uses the same shared renderer instead of its own ad-hoc prompt builder. The Phase B1 (book-plan) → B2 (render) → B3 (print-prep) chain is unchanged; only the per-page render call is rewritten.

**Bundled assets:**

- [seed/template-references/](seed/template-references/) — 39 reference images across 9 templates, ported from layout-gen. Each template has 1–6 reference images plus the manifest below.
- [seed/template-references/manifest.json](seed/template-references/manifest.json) — per-template metadata: aspect_ratio (16:9 or 3:4), canvas (A3L or A4P), content_type (narrative / educational / character-intro / process), best_ref (the one ref the renderer picks by default), alt_refs (siblings). Plus a `content_type_to_templates` map for content-classification-driven template selection.

**Three book paths summary:**

| Path | When | Quality | Cost |
|---|---|---|---|
| `/create-video` with `brief.book.page_count_target > 0` (Phase B1–B3) | Video + book on same topic, fresh book art | Highest (per-page planning, Gemini QA, retry loop) | ~Rs 15–20 / page |
| `/create-book-from-keyframes` (layout-renderer mode) | Have video, want book with same characters | High (keyframes as content reference) | ~Rs 15 / page |
| `/create-book-from-keyframes` (birefnet mode, opt-in per page) | Have video, want keyframes verbatim with BG removed | Layout-less (no text zone) | ~Rs 2 / page |
| `/create-book` standalone | No video, book is the deliverable | High (depends on source-image quality) | ~Rs 15 / page |

## 0.5.0 — 2026-05-19

### New skill + command: book from keyframes

Users wanted to build a print-ready picture book using the **existing storyboard keyframes** from a completed video run — preserving visual continuity between the video and the book, and skipping the cost of fresh gpt-image-2 generation. The default book branch (Phase B1–B3, gated on `brief.book.page_count_target > 0`) always generated new illustrations. Now there's an alternative standalone path.

- **New slash command** `/create-book-from-keyframes` — post-video entry point. Invokes the new skill.
- **New skill** `skills/book-from-keyframes/SKILL.md` — chat-driven page assignment. Lists available keyframes from `<run-dir>/storyboard/keyframes/`, walks the user through which keyframe → which page → which template → what book voice copy → BG removal yes/no per page. Saves the assignment to `<run-dir>/book/from_keyframes.config.json` (reviewable, re-runnable).
- **New Python phase** [scripts/phase_book_from_keyframes.py](scripts/phase_book_from_keyframes.py) — reads the config, runs `fal-ai/birefnet/v2` on pages with `remove_background: true`, copies-with-RGBA-convert for the others, writes `book/plan.json` in the same shape Phase B3 expects, and (with `--run-print-prep`) auto-invokes `phase_book_print_prep` to compose the final A4P / A3L canvases at 300 DPI.
- **Mutually exclusive** with the default `brief.book.page_count_target > 0` flow on the same run (both write to `<run-dir>/book/`). The skill names the conflict and tells the user to pick one path per run.
- **Per-page BG-removal defaults** documented per template (full-bleed templates default to `false` to preserve scene context; vignette / split / spots templates default to `true` for clean cutouts on white).
- Registered in `plugin.json` under `commands[]` and `skills[]`.

## 0.4.2 — 2026-05-19

### Hotfix: force eleven_v3 for VO regardless of config

Users on stale `<output>/.config/models.yaml` (generated before vo was pinned to `eleven_v3`) were hitting a bad failure mode: 0.4.1's tagged narration like `[curious] Why does a plant droop? [pause] Because…` was being sent to `eleven_multilingual_v2`, which **speaks audio tags literally**. The final audio contained the words "curious" and "pause" spoken aloud.

Setup never overwrites an existing `models.yaml` (intentional — preserves user tweaks), so seed updates to `model_id: eleven_v3` didn't reach existing installs.

- **[scripts/phase_vo.py](scripts/phase_vo.py)**: `model_id` is now force-overridden to `eleven_v3` at runtime. Any other value in the user's models.yaml triggers a loud warning in logs + stderr but the API call uses `eleven_v3` regardless. Failure mode is too bad to tolerate silently for users with stale configs.
- **[seed/generation-defaults.json](seed/generation-defaults.json)**: legacy vo defaults (`eleven_flash_v2_5`, `eleven_multilingual_v2`) replaced with `eleven_v3` across all tiers + a `_warning` comment noting the runtime force-override.
- **[seed/models.yaml](seed/models.yaml)**: comment updated to spell out that audio tags are spoken literally on older models and that `phase_vo.py` overrides regardless.
- **[skills/setup/SKILL.md](skills/setup/SKILL.md)**: noted the "setup doesn't overwrite existing models.yaml" gotcha + the runtime override for vo, plus how to recover (`rm <output>/.config/models.yaml` and re-run setup).

## 0.4.1 — 2026-05-19

### Skill output specs tightened across all five generation phases

0.4.0 fixed the script-writer skill (the worst offender). 0.4.1 applies the same pattern — inline rich Output spec, hard preconditions, quality bar, common-failure-modes section — to the other four Claude-driven skills. Same root cause across the board: skill specs were loose, rich references existed but were loaded on demand, and whether Claude followed them was non-deterministic. Diligent runs produced solid output; lazy runs produced thin output. Net effect: ~30% variance in output quality across runs of the same brief.

The fix kills that variance. Five skills changed:

- **[skills/vo-generator/SKILL.md](skills/vo-generator/SKILL.md)** — was emitting plain TTS sometimes. Now mandates **audio tag density: ≥6 tags per minute of narration**, with required positions (emotional tag on hook, pacing tag at each scene transition, emphasis before reveals, emotional resolve on recap). Inline taxonomy summary so Claude doesn't need to load the reference. New output: `vo_prompt.md` — the exact tagged text sent to ElevenLabs, reviewable before the API call. Tag-count check happens BEFORE the API call; failing prompts get regenerated, not sent.

- **[skills/clip-generator/SKILL.md](skills/clip-generator/SKILL.md)** — was sometimes skipping per-clip validation prompts, letting `phase_clips.py` fall back to a generic QA template, letting drift slip through. Authoring `clip_NN.validation.txt` for every beat is now a **hard precondition** — the skill's pre-flight check verifies all files exist before invoking the runner. Inline meta-template summary covers tick-spacing, character-identity locks, anchor cross-references. Common failures section names the generic-fallback signature so it's caught at log review.

- **[skills/storyboard-generator/SKILL.md](skills/storyboard-generator/SKILL.md)** — was sometimes skipping anchor authoring on split-screen beats, producing the HERBA/CARNI side-swap class of bug in the resulting clips. Authoring `anchors[]` for any beat with two-or-more named spatial elements is now a **hard requirement** with explicit trigger phrases and a flowchart. New reference [skills/storyboard-generator/references/anchor-authoring.md](skills/storyboard-generator/references/anchor-authoring.md) — full schema, aspect-ratio rules (9:16 must use top/bottom, never left/right), good/bad examples, integration with `phase_clips.py:_anchors_block()`.

- **[skills/stitcher/SKILL.md](skills/stitcher/SKILL.md)** — was sometimes emitting all-hard-cut stitch plans, producing choppy video. Now requires per-beat `transition_reasoning` in `stitch_plan.json`, mandates ≤60% `cut` transitions, includes the transition rules table inline (motion-intensity-driven). `stitch_plan.json` must be written BEFORE the render so it's reviewable.

- **[skills/script-writer/references/educational-script-structure.md](skills/script-writer/references/educational-script-structure.md)** — was a 49-line stub with one example, no coverage of Cast / Sound / Scene Timeline. Beefed up to ~200 lines: full skeleton with a worked 60s photosynthesis example, frontmatter rules table, per-section rules, hook patterns by class level, beat count & pacing by duration target, word_to_word mode notes.

- **[skills/script-writer/references/storytelling-best-practices.md](skills/script-writer/references/storytelling-best-practices.md)** — was a 37-line stub with one-liner rules. Beefed up to 10 rules, each with bad-vs-good examples. Adds: stage-direction-in-narration anti-pattern, throughline character guidance, numbers-and-units pacing for kid-explainer register.

### Recommended client config

The above fixes work with any Claude model, but reasoning effort matters. For client laptops:
- Model: `claude-sonnet-4-6` (great for skill-following structured output at sensible cost).
- Reasoning effort: **high**.
- The token cost is rounding error next to image gen (₹15+/call) and video gen (₹100+/call).

### Files touched

```
plugin.json (version bump)
CHANGELOG.md (this entry)
CLAUDE.md (architecture decisions table — note skill-spec tightening invariant)
skills/vo-generator/SKILL.md
skills/clip-generator/SKILL.md
skills/storyboard-generator/SKILL.md
skills/storyboard-generator/references/anchor-authoring.md (NEW)
skills/stitcher/SKILL.md
skills/script-writer/references/educational-script-structure.md
skills/script-writer/references/storytelling-best-practices.md
```

## 0.4.0 — 2026-05-19

### Script writer now emits the rich structured format

The plugin's [skills/script-writer/SKILL.md](skills/script-writer/SKILL.md) previously specified a deliberately minimal output (frontmatter + `[BEAT N]` blocks + `<!-- visual: ... -->` comments) — no Cast block, no Strategy section, no Scene Timeline. But [scripts/lib/script_io.py](scripts/lib/script_io.py) has a `parse_cast()` function expecting `## Cast` / `### {name}` / Role/Personality/Voice/Looks bullets sourced from the seed prompt format. The mismatch silently made `script.cast == []` for every run, which forced [character-sheet-generator](skills/character-sheet-generator/) to invent characters from `brief.topic` + `brief.notes` — the root cause of character drift across runs.

- **Skill rewrite.** The skill now requires Strategy + Cast (when characters are on) + Sound + Scene Timeline (table) + Beats sections, in that order. Frontmatter expanded with `character_mode`, `dialogues_enabled`, `annotations_enabled`, `grounded`, and `source_chapter` so downstream phases can read brief-state directly off the script.
- **Cast block format pinned.** `### {Name}` headers with bullet sub-sections Role / Personality / Voice and tone / Looks — matching what `parse_cast()` already parses. "Voice and tone" is dropped when `dialogues_enabled == false`. The Looks bullet is the load-bearing field — pasted verbatim into Phase 3a's gpt-image-2 prompt.
- **Scene Timeline column set is brief-flag-driven.** Dialogue and Annotations columns appear only when their corresponding flag is true (no more half-empty `(none)` columns).
- **Beats and Scene Timeline must agree.** Same scene count, same narration text, same timing. Beats stay as the machine-parsed source for vo / storyboard / clip phases; Timeline is the human-readable mirror.
- **Common-failures section** added so Claude doesn't slide back into emitting the thin format.

### Chapter content collected in both script modes

Pre-0.4.0, `chapter_source` was only collected for `script_mode == "word_to_word"`. In `"standard"` mode the script writer fell back to general knowledge about `topic` — which is why standard-mode scripts were thin and occasionally hallucinated. Now:

- **Brief-collector form always asks for chapter content** (text paste / URL / absolute file path). Strongly recommended in `standard` mode, required in `word_to_word`. The submit handler blocks word-to-word without a source.
- **Server persists pasted text to `<run-dir>/source/chapter.txt`** so phase_script has a stable on-disk artifact regardless of input method. The brief's `chapter_source.ref` is rewritten to the file path before `brief.json` is saved. URL and file-path kinds are resolved lazily by Phase 1.
- **Orchestrator gates entry to Phase 1.** When `chapter_source` is missing in word-to-word mode the orchestrator halts and asks the user in chat (paste / path / url), persists the answer back into `brief.json`, then proceeds. In standard mode, missing source is a soft-warn — the user can `skip` to the degraded general-knowledge path.
- **Script-writer skill resolves all three `chapter_source.kind` values** (`text` / `file` / `url`) and emits a `grounded: true|false` frontmatter flag on `script.md` so downstream phases and reviewers can tell whether the script was anchored to source material.
- **Schema mirrored** in [skills/brief-collector/references/brief-schema.md](skills/brief-collector/references/brief-schema.md). The Edustack web platform must mirror this when porting — `chapter_source` is no longer conditional on script_mode.

## 0.3.0 — 2026-05-18

### Human-character video path

- **Phase 4 now routes by `brief.character_mode`.** When `character_mode == "human"` the clip generator uses `fal-ai/wan/v2.7/image-to-video` (Wan 2.7) at 720p by default; Seedance 1.5 Pro continues to handle `abstract` and `none`. Smoke-validated 2026-05-18: 4 keyframes × 4 s @ 720p, identity locked, total spend ~$1.60. Wan 2.7's payload shape matches Seedance (prompt + image_url + duration + resolution), so the runner is a single code path — only the model slug + resolution differ. Routing in [`scripts/phase_clips._resolve_video_stage`](scripts/phase_clips.py).
- **New `models.yaml:video_i2v_human` stanza** with `concurrency: 4` and `resolution: "720p"`. The existing `video_i2v` stanza also gains `concurrency: 4`. Users can override per-stage.

### Concurrent clip generation

- **Phase 4 fans clip gen across a ThreadPoolExecutor.** Each beat's gen + QA + auto-retry loop is independent (no shared state), so beats run in parallel. Default 4 workers, read from `models.yaml:<stage>.concurrency`. New `--concurrency` flag on `phase_clips.py` overrides. Cuts wall-clock for an 8-beat video from ~8× per-beat time to ~2× — significant.

### Dialogue opt-in (default off)

- **New `brief.dialogues_enabled` field, default `false`.** When false (the default), `phase_clips.py` injects a verbatim audio-direction block into every clip prompt: "no dialogue, no speech, no voice-over, no humming, no singing. Characters remain silent — no mouth movement for speech." Without this, Seedance hallucinates Mandarin and Wan 2.7 occasionally invents lip-sync motion. The stitcher still lays in narration VO + ambient music — this only suppresses model-invented in-clip speech.
- **Brief-collector form gains a Dialogues checkbox** in the same row as Subtitles and Annotations. Schema mirrored in [skills/brief-collector/references/brief-schema.md](skills/brief-collector/references/brief-schema.md). The Edustack web platform must mirror this field when porting.
- **Script writer also honours the flag.** [seed/prompts/script-writer.md](seed/prompts/script-writer.md) now drops the Dialogue column entirely (and the Cast block's "Voice and tone" bullet) when `dialogues_enabled` is false — silent characters don't need a vocal spec, and dialogue lines that downstream phases would ignore no longer clutter the script. Same treatment for the Annotations column when `annotations_enabled` is false.

## 0.2.0 — 2026-05-17

### Book mode (post-video, optional)

- **New optional Book output** alongside the explainer video. After the video finishes, a curated 0–12-page picture book renders as **transparent-background RGBA PNGs** sized to A4 Portrait (3:4 templates) or A3 Landscape (16:9 templates) at 300 DPI — drop-in for book designers (InDesign / Affinity / Photoshop).
- **Brief-collector grows a Book step**: page count 0–12 (0 = skip), book voice (storybook narrator / factual calm / playful rhyming), and a template gallery with 9 layout cards (wireframes + 39 bundled reference images). Pick 2–4 templates; the planner auto-assigns one per page based on scene content.
- **Three new phases**, registered in `plugin.json`:
  - **B1 `book-plan`** — curated page list (~60% reused video keyframes + ~40% new book-only scenes), per-page template assignment, book-voice copy rewrite. New chat gate (`Gate B1`).
  - **B2 `book-render`** — `fal-ai/gpt-image-2` with `background=transparent` + `fal-ai/birefnet/v2` fallback, then Gemini 2.5 Pro visual QA via `fal-ai/any-llm/vision`. Four binary checks (transparent BG, no text, character consistency, scene match); up to 2 retries per page.
  - **B3 `book-print-prep`** — Pillow-only canvas composer. Per-template positioning + scaling (`scripts/lib/book_canvas.py`), Lanczos resize, auto-level + unsharp mask on RGB channels, alpha preserved, embedded `dpi=(300, 300)`.
- **New slash command**: `/create-book-regen page-NN` for one-shot per-page regen with optional `--template` / `--scene` / `--copy` overrides.
- **Provider stack unchanged**: all external calls remain routed through fal.ai. No ImageMagick, no PDF tooling. No new system binaries.
- **brief.book schema** documented at `skills/brief-collector/references/brief-schema.md` — must be mirrored when porting to the Edustack web platform.
- **Observability reuses existing six event streams**; no Supabase migration needed. Book phases emit `phase: book-plan|book-render|book-print-prep` events.

## [Unreleased]

### Install flow — `.claude-plugin/marketplace.json` + trust posture (2026-05-18)

End users have been bouncing off install: client-side Claudes correctly flag that `claude plugin add <url>` is not a real command, and (just as correctly) decline to pipe API keys into a repo they haven't reviewed. Fix is twofold — fix the install commands, and explain the trust posture upfront so a defensive Claude has explicit "yes, this is legitimate" framing.

- **NEW: `.claude-plugin/marketplace.json`** — declares this repo as both a plugin marketplace AND the single plugin inside it (Anthropic's recommended pattern for solo-maintained plugins). Users can now `/plugin marketplace add designcraveyard/edustack-video` and `/plugin install edustack-video@edustack-video` from inside Claude Code, the way the docs intend.
- **README rewritten** with the correct slash-command install flow, a "before you install — trust posture" section that explicitly walks a reviewer through the files worth reading (`plugin.json`, `hooks/ship-chat.sh`, `scripts/`), an explicit key-handling statement (keys saved at mode 0600 to `<output>/.config/`, never posted to Supabase or the maintainer), and a note that `/test-logs` can verify the telemetry posture after install.
- **`commands/create-video-setup.md` leads with a "Note for Claude reading this on a client machine for the first time"** — names the upstream repo, links the three short files (`fal_client.py`, `elevenlabs_client.py`, `supabase_sink.py`) that establish that keys stay local. Pre-empts the most common review-pushback.
- **`commands/plugin-update.md` documents the equivalent native command** (`/plugin marketplace update edustack-video` + `/reload-plugins`) and explains what /plugin-update does on top (dep sync, in-flight-run guard, dirty-tree guard).
- **`CLAUDE.md` + `docs/developing.md`** updated to remove the old `claude plugin add` references; both now show the correct slash-command flow for local-path installs too.

### Observability self-test — `/test-logs` (2026-05-18)

- **New command `/test-logs`** verifies the entire Supabase telemetry pipeline. Emits one synthetic event per stream (`logs`, `prompts`, `analyses`, `gates`, `heartbeat`, `chat`), SELECTs each row back through the REST API to prove it landed, and exercises the chat hook (`hooks/ship-chat.sh`) end-to-end with a synthetic transcript. Per-stream PASS/FAIL output with HTTP status / payload-key / fallback-path details so failures point at the exact cause.
- **Fixed: chat hook was still posting to the legacy FastAPI VPS endpoint** (`/chat-transcripts` with `vps.token`). Rewritten to write directly to Supabase `eduplugin_events` with `stream=chat`, mirroring `SupabaseSink.chat()` — same row shape, same auth, same RLS path. Falls back to `<run-dir>/logs/local.jsonl` on Supabase failure (with HTTP status captured in `_fallback`). Uses stdlib `urllib` so the hook doesn't depend on the project venv being active.
- **New synthetic-row markers** — every test event carries `test_marker: true` so admin analytics queries can `WHERE payload->>'test_marker' IS NULL` to exclude them.
- **CLAUDE.md invariant #5 augmented**: any touch to `supabase_sink.py`, `ship-chat.sh`, the `eduplugin_events` schema, or `user_id`/`run_id` partitioning must be verified with `/test-logs`.
- **Registered in `plugin.json`** under `commands[]`. Documented in `README.md` and `commands/test-logs.md` (the command file itself walks Claude through the run, surfaces stdout verbatim, and explains the common failure causes).

### Rich character sheets — gpt-image-2 + verbatim descriptions contract (2026-05-18)

Reference Jay & Scooterist / Leafy Grazer & Claw Hunter examples raised the bar for what Phase 3a should produce. Reworked to match.

- **Default model switched: `fal-ai/nano-banana-2` → `fal-ai/gpt-image-2`** for character sheets. gpt-image-2 holds the multi-region structured layout (title + LEFT hero + CENTER/RIGHT TOP per-character expressions row + turnaround + BOTTOM CENTER palette + BOTTOM MIDDLE expressions grid + BOTTOM RIGHT details); Nano Banana 2 was smearing the regions. Nano Banana 2 stays the default for Phase 3b's per-keyframe mode where its single-subject strength shines. Override path documented in [`skills/character-sheet-generator/references/model-selection.md`](skills/character-sheet-generator/references/model-selection.md).
- **Aspect switched: 1:1 → 16:9 landscape** (`image_size: landscape_16_9`). The 8-region rich layout needs the horizontal real estate.
- **`scripts/phase_characters.py` rewritten** to compose the canonical rich-template prompt: style descriptor → title → aesthetic bullets → hero pose → per-character verbatim descriptions → CENTER/RIGHT TOP expression rows + turnarounds → BOTTOM palette / expressions grid / details → style finish bullets. Per-style descriptor + finish-bullet tables let any style (Pixar / Watercolour / 2D Flat / Cinematic / Whiteboard / Doodle / Clay / 2D Animated) render correctly out of the box. Auto-regen QA loop (up to 2×) preserved; analyser now also audits **layout completeness** (missing regions are regen-worthy).
- **Cast-block parsing added to `script_io`** — `script_io.parse_cast()` extracts `### Name → Role / Personality / Voice and tone / Looks` from the script's `## Cast` block. `Script.cast: list[CastMember]` is now part of the parsed script object. `CastMember.verbatim_description` is the canonical paragraph for downstream prompts.
- **New output: `characters/descriptions.json`** — per-character verbatim paragraphs that downstream phases must paste IDENTICALLY into every prompt. This is the consistency contract. Storyboard and Clip prompts now read precedence: `descriptions.json` (verbatim) → `description_block.md` (none-mode) → `analysis.json` (legacy fallback).
- **New output: `characters/sheet_prompt.md`** — audit trail of the full prompt sent + style descriptor + verbatim character descriptions; mirrors the structured reference doc the team provided as a "this is how it should look" example.
- **`phase_storyboard.character_brief()` and `phase_clips.py`** updated to embed verbatim descriptions (not just a "characters present" label). Identity now locks across the whole pipeline.
- **References rebuilt**:
  - `references/character-sheet-design.md` — rich 8-region layout, hard rules, QA pattern, output contract.
  - `references/model-selection.md` — flipped to recommend gpt-image-2; documents WHY (multi-region layout, legible labels, consistent turnaround, locked studio background).
  - `references/prompt-template.md` (new) — canonical skeleton + Jay & Scooterist (Pixar) and Leafy Grazer & Claw Hunter (Watercolour) end-to-end examples.
  - `references/description-block-template.md` — generalised: now covers `descriptions.json` (human/abstract) AND `description_block.md` (none-mode) with the same rules.
- **`SKILL.md` rewritten** to reflect the new outputs, downstream contract, and reference structure.
- **`paths.RunPaths` adds `character_descriptions` and `character_prompt`** — canonical paths for the new outputs.

### Brief UI + VO improvements (2026-05-17 evening)
- **Brief UI voice picker** is now a live ElevenLabs combobox matching the Edustack `publisher/generate` `VoiceComboBox` UX. Server adds `GET /voices?language=…` that reads `<output>/.config/elevenlabs.key`, fetches `/v1/voices`, scores Indian-accent voices first for Hindi/Hinglish/Tamil/Bengali/Marathi, caches 5 min, and returns a slim `{voice_id, name, preview_url, labels}` list. The form replaces the static `<select>` with a searchable + scroll-paginated dropdown with per-row and selected-voice play/stop preview buttons. Refetches on `language` change.
- **ElevenLabs model pinned to `eleven_v3`** in `seed/models.yaml`, `ElevenLabsClient.tts_with_timestamps`, and `phase_vo`. Required for correct multilingual phonemizing — older `multilingual_v2` mispronounces Hinglish-in-Devanagari and other Indic scripts.
- **Hinglish narration must be in Devanagari** — the `STANDARD_SYSTEM` prompt in `phase_script.py` now spells this out as non-negotiable: Hindi/Hinglish/Marathi → Devanagari, Tamil → Tamil script, Bengali → Bengali script. Romanised text is forbidden because EL phonemizes Latin characters with English phonemes.
- **`word_to_word` mode warns on language mismatch** — if the chapter source contains no native-script characters for the brief's language, the run logs a `warn` event so the user knows the VO will mispronounce.
- **Split-screen composition rule** is now embedded in `KEYFRAME_PROMPT` and `CLIP_PROMPT` and the `storyboard-prompting.md` reference: 16:9 → vertical split (left ⎮ right), 9:16 → horizontal split (top ▬ bottom). Never split a vertical canvas down the middle.
- **Audio prompt is now persisted** — `phase_vo` writes `<run-dir>/audio/full-vo.prompt.txt` (the exact narration sent to EL) and `<run-dir>/audio/full-vo.prompt.json` (voice_id, voice_name, model_id, output_format, language, char count, endpoint) BEFORE the API call, so a failed run still leaves the prompt on disk for inspection.

### Pivot — Supabase replaces FastAPI VPS
- Dropped the standalone FastAPI/Caddy observability service that ran on `eduplugin.birdzeye.in`. It required GHCR image hosting, Hostinger MCP deploys, Caddy TLS issuance, and a per-user bearer-token bootstrap — none of which earned its complexity given that the user already runs an Edustack Supabase + Next.js stack.
- Replaced with **one Supabase table** (`public.eduplugin_events`) on the existing Edustack project. Six streams (`logs`, `prompts`, `analyses`, `gates`, `heartbeat`, `chat`) live as rows; the plugin writes with the project's anon key; reads are gated by the EduStack-Platform admin route.
- Added **debug viewer** to `EduStack-Platform/app/(authenticated)/admin/eduplugin/`:
  - `page.tsx`: recent-runs index (across all installs).
  - `runs/[runId]/page.tsx`: chronological event timeline with per-stream coloring and expandable payload details.
- Removed `vps/`, `.github/workflows/publish-vps-images.yml`, and the GHCR push workflow from this repo.
- `scripts/lib/vps_logger.py` now re-exports `SupabaseSink` for back-compat; `scripts/lib/supabase_sink.py` is the new home.
- `scripts/lib/config.py` gained `supabase_url`, `supabase_anon`, `user_id` (auto-generated UUID per install); `vps_url` / `vps_token` properties retained as aliases.
- Setup skill + `/create-video-setup` now prompt for the Supabase anon key (default URL is the Edustack project) and the chat-capture consent text now mentions Supabase.
- Hostinger DNS record for `eduplugin.birdzeye.in` and the (failed) `eduplugin` Docker Compose project have been removed.

### Added
- Production-grade `scripts/lib/fal_client.py` with bounded retries, transient-vs-permanent classification, and per-prompt VPS logging (path + sha + latency, never raw artifacts).
- Production-grade `scripts/lib/elevenlabs_client.py` with `/v1/text-to-speech/{voice}/with-timestamps` integration; `/v1/user` validate ping.
- `scripts/lib/visual_analyzer.py` rewritten to use `fal-ai/any-llm/vision` (the multimodal endpoint) and graceful-degrade when the vision endpoint is unavailable or returns prose. For clips, samples frames via ffmpeg into a single contact-sheet image (work around any-llm/vision's 1-image-per-call limit).
- `scripts/lib/paths.RunPaths` — single source of truth for all per-run paths.
- `scripts/lib/aspect.py` — aspect-aware sizing (`aspect_sizes[brief.aspect]`) and beat-grid layout (`grid_for_beats`).
- `scripts/lib/script_io.py` — round-trip `script.md` parser/emitter with strict frontmatter + beat headers + `<!-- visual: -->` hints.
- **`phase_script.py`** — `standard` mode (Gemini-generated original script) and `word_to_word` mode (verbatim from PDF / text / URL chapter source via pypdf).
- **`phase_vo.py`** — ElevenLabs + `vo_timeline.json` with word-level alignment; beat anchoring with order-preserving normalized word matching.
- **`phase_characters.py`** — `human` / `abstract` Nano Banana 2 character sheet + Gemini description; `none` mode writes `characters/description_block.md` (Gemini-generated, prepended to every later prompt).
- **`phase_storyboard.py`** — `storyboard_panel` (gpt-image-2 + PIL slice) and `per_keyframe` (Nano Banana 2 + sheet conditioning) modes; auto-corrective vision retry loop (≤2 retries per beat).
- **`phase_clips.py`** — Seedance 1.5 Pro i2v per beat, contact-sheet Gemini analysis, auto-corrective retry, `--smoke` flag for short low-res test runs.
- **`phase_stitch.py`** — MoviePy 2.x compose, transition picking from clip analyses (cuts on high motion, dissolves on calm), Pillow-based karaoke-style subtitle burn-in driven by `vo_timeline.json` word timestamps (active word highlighted in accent color). No `libass` dependency.
- **`tests/`** — 26 pytest unit tests across `run_state`, `vps_logger` fallback, `aspect`, `script_io`, `make_subtitles` chunkers, `extract_keyframes`, and `phase_vo.assign_beats`. All pass.
- **`.github/workflows/publish-vps-images.yml`** — builds `vps/app` and `vps/caddy` and publishes to GHCR (`ghcr.io/designcraveyard/edustack-video-app` and `-caddy`) on every push to `main` that touches `vps/`. Tags `:latest` and `:<sha>`.
- **`vps/caddy/`** — new directory with a custom Dockerfile that bakes the Caddyfile into the image (so no host-side bind mount is needed for Hostinger MCP deployment).

### Changed
- `vps/docker-compose.yml` now references prebuilt GHCR images via `image:` instead of `build:` — required because Hostinger's compose runner does `pull + up -d` (not `up --build`).
- `make_subtitles.chunk_words_grouped()` added — keeps per-word objects intact for karaoke rendering.
- `seed/models.yaml` clarified: image sizes derive from `aspect_sizes[brief.aspect]`; character sheets remain 1:1 by design.
- Brief UI `form.js` switched to safe DOM construction (no `innerHTML`).

### Fixed
- `fal-ai/any-llm` schema corrected from OpenAI-style `messages` to flat `prompt` + `system_prompt` (the old call format returned HTTP 400 "Field required: prompt").
- MoviePy 2.x compatibility: `from moviepy import ...` (was `moviepy.editor`), `.with_speed_scaled()`, `.resized()`, `.with_audio()`, `.subclipped()`.
- Smoke tests revealed and patched: (a) `fal-ai/any-llm/vision` accepts only one image per call → contact-sheet workaround for clip analysis; (b) brew ffmpeg 8.1 lacks `--enable-libass` on the user's box → switched burn-in to MoviePy + Pillow which is portable.

### Verified (manual smoke, fresh fal.ai + ElevenLabs keys)
- ✅ 20-second VO via ElevenLabs `with-timestamps` → 42 word timestamps split correctly across 2 beats.
- ✅ `phase_characters` (mode=none) → Gemini-generated `description_block.md` with characters, palette locks, lighting rules.
- ✅ 1 keyframe via Nano Banana 2 at 768×432 → 1.4MB PNG.
- ✅ 4-second clip via Seedance 1.5 Pro at 720p → 4MB MP4 (h264+aac).
- ✅ Gemini 2.5 Pro contact-sheet clip analysis → `motion_intensity: calm, character_consistency: ok`.
- ✅ Stitch → `final.mp4` (1920×1080, ~6s) and `final_subtitled.mp4` with karaoke per-word highlighting.

## [0.1.0] — 2026-05-17

### Added
- Initial scaffold: plugin.json, 8 commands, 9 skills (orchestrator, setup, brief-collector, script-writer, vo-generator, character-sheet-generator, storyboard-generator, clip-generator, stitcher).
- Reference doc taxonomy ported from `edu-vid-gen-cloud` (`prompting.md`, `validation.md`, `transitions.md`, `audio-tags.md`, `api-errors.md`) and `edustack/docs/prompts/` (9 prompt specs).
- Python `scripts/` skeleton with `lib/` package (fal client, elevenlabs client, visual analyzer, vps logger, run state, config).
- Node brief-collector localhost UI server (stdlib http, no Express).
- FastAPI VPS observability service (`vps/`) — Docker + Caddy auto-TLS for `eduplugin.birdzeye.in`.
- `ship-chat.sh` hook (PostToolUse + Stop) for opt-in chat transcript shipping.
- Seed data from Edustack: `generate_form_options` (72 rows) and `generation_defaults` (7 rows).
- Repo-local doc-freshness hook (`.claude/hooks/`) — blocks Stop until CLAUDE.md/docs are reviewed when plugin source changes.
