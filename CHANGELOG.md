# Changelog

All notable changes to `edustack-video` will be documented here. Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
