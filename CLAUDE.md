# CLAUDE.md — `edustack-video` workspace memory

This file orients Claude Code (and future maintainers) when working in this repo. Read it before touching anything non-trivial.

---

## What this is

`edustack-video` is a **Claude Code plugin** that generates educational explainer videos through a 5-phase pipeline (script → VO → characters → storyboard → clips → stitch) with 4 chat-driven review gates.

The plugin lives in this repo and is installed by end users **inside a Claude Code session** via the canonical slash-command flow (`claude plugin add` is not a real CLI command — a common point of confusion):

```text
/plugin marketplace add designcraveyard/edustack-video
/plugin install edustack-video@edustack-video
/reload-plugins
```

The repo is both the marketplace and the plugin — that pattern is declared in `.claude-plugin/marketplace.json`. Updates pull on the user's schedule via `/plugin marketplace update edustack-video` or this plugin's `/plugin-update` (which additionally runs `uv pip sync` / `npm ci` if deps changed).

It is **not** a library, not an app, not a service. It is a directory of Markdown, Python, Node, and YAML that Claude Code loads and executes.

---

## Repository map

```
edustack-video/
├── plugin.json             # declares commands, skills, hooks — single source of truth
├── commands/               # 8 slash commands; each routes to a skill
├── skills/                 # 9 skills with SKILL.md + per-skill references/
├── scripts/                # Python phase scripts + scripts/lib/ shared helpers
├── skills/brief-collector/server/  # Node stdlib HTTP server (no Express)
├── vps/                    # FastAPI observability sink + Caddy + Docker
├── hooks/ship-chat.sh      # PostToolUse + Stop hook (chat transcript shipping)
├── seed/                   # Exported defaults + porting source for Edustack prompts
└── CHANGELOG.md            # human-readable, drives /plugin-update output
```

---

## Cross-file invariants — read before editing

These are not enforced by any linter. Break them and the plugin silently misbehaves.

1. **`plugin.json` lists everything.** When you add a command, skill, or hook, edit `plugin.json` too.
2. **A skill is its directory.** `skills/X/SKILL.md` is mandatory; `references/*.md` are loaded by Claude only when the SKILL.md links to them via `@references/...`.
3. **Image aspect derives from `brief.aspect`.** Never hardcode 16:9 in storyboard or clip code. Read `<output>/.config/models.yaml > aspect_sizes[brief.aspect]`. Character sheets are the only intentional exception — always **16:9 landscape** because the rich 8-region layout (title + LEFT hero + CENTER/RIGHT TOP per-character grids + BOTTOM palette / expressions / details) needs the horizontal real estate.
4. **Supabase observability is best-effort.** `scripts/lib/supabase_sink.py` MUST NOT raise on failure — fall back to `<run-dir>/logs/local.jsonl`. The pipeline never blocks on the sink. `scripts/lib/vps_logger.py` is a thin alias re-exporting `SupabaseSink` for back-compat. The chat hook (`hooks/ship-chat.sh`) writes to the same Supabase table (stream=`chat`) — when it changes, run `/test-logs` to verify it still round-trips.
5. **Keys never leave the user's machine.** `<output>/.config/{fal,elevenlabs}.key` are read by local Python only. The Supabase sink writes metadata refs (paths + sha256, prompt sha) — never raw artifacts and never the API keys.

When you touch anything observability-related — the sink (`scripts/lib/supabase_sink.py`), the hook (`hooks/ship-chat.sh`), `eduplugin_events` schema, or the `user_id` / `run_id` partitioning — **run `/test-logs` to verify the change**. It emits a synthetic event per stream, SELECTs each back, and exercises the chat hook end-to-end. Six streams × one POST + one SELECT in ~3 s.
6. **Form field names must match `brief.json` schema** in [skills/brief-collector/references/brief-schema.md](skills/brief-collector/references/brief-schema.md). The Edustack web platform reads the same shape — drift breaks cross-port.
7. **Gates are chat-only.** No web UI. Surfaced via clickable file paths in the chat message; user replies `approve` or `regen <target>: <comment>`.
8. **Book pages have their own canvas, not `brief.aspect`.** A4P (2480×3508 @ 300 DPI) for 3:4 templates, A3L (4961×3508 @ 300 DPI) for 16:9 templates. The canonical map lives in [`scripts/lib/book_canvas.RULES`](scripts/lib/book_canvas.py). Do not derive book canvases from `brief.aspect`.
9. **Book pages are opaque RGB on a white-flattened canvas with a painted soft-light text zone.** Never burn text into the image. The intended text lives in the sidecar `<run-dir>/book/print/page-NN.txt` and in the `book_voice_copy` field of `book/plan.json`. The renderer prompts gpt-image-2 to paint a "soft light area in a single pale colour" in the text zone — NOT to leave it transparent — because the model misinterprets transparent-BG requests as "paint a checker pattern" (visible grid artifact). `book_canvas.compose()` flattens any residual alpha onto solid white at print time. The legacy birefnet/v2 BG-removal path remains in the runner for opt-in cases (e.g. `/create-book-from-keyframes` with `remove_background: true`) where the user wants a true cutout, not a layout-composed page.
10. **Template selection is a visual localhost picker, and template metadata lives in synced manifests.** Every book path chooses layouts through the [`book-template-picker`](skills/book-template-picker/SKILL.md) localhost gallery — standalone `/create-book` + `/create-book-from-keyframes` launch its zero-dep Node server directly (binds `127.0.0.1:0`, opens the browser, writes `<run-dir>/book/template-selection.json`, exits on `PICKER_OK`); the in-video path uses the equivalent gallery embedded in the brief form. The picker serves reference thumbnails straight from canonical `seed/template-references/` via `/refs/<path>` — **never duplicate the 5 MB of refs**. Three files describe the nine templates and their **template ids MUST stay identical** across all three: [`seed/template-references/manifest.json`](seed/template-references/manifest.json) is the renderer's source of truth (aspect_ratio, canvas, content_type, best_ref, alt_refs); [`skills/book-template-picker/server/public/templates.json`](skills/book-template-picker/server/public/templates.json) is the picker's display source of truth (name, nickname, description, tags, full ref lists, wireframe); `skills/brief-collector/server/public/templates/manifest.json` is the brief form's slim mirror. Add/rename a template → update all three.

---

## Architecture decisions (locked)

| Area | Decision | Why |
|---|---|---|
| Image + video + vision | fal.ai only | Single key, single retry surface |
| VO | ElevenLabs direct (not via fal) | Need word-level timestamps for stitcher |
| VO writing system | For `language ∈ {Hindi, Hinglish}`, the narration Claude writes (and that reaches ElevenLabs) must have **all Hindi words in Devanagari** — देवनागरी for Hindi; for Hinglish, Hindi in Devanagari with English/technical terms kept in Latin | ElevenLabs `eleven_v3` phonemizes from the written script, so romanised Hindi is read with English phonemes. Enforced **where the text is authored** — the Claude-driven [`script-writer`](skills/script-writer/SKILL.md) (writes `script.md` narration) and [`vo-generator`](skills/vo-generator/SKILL.md) (pre-API Devanagari validation) skills, which ARE Phase 1/2. `scripts/phase_script.py` / `phase_vo.py` are **legacy and not invoked** — don't put VO-content rules there. |
| Vision model | Gemini 2.5 Pro via `fal-ai/any-llm` → OpenRouter | Pro materially reduces drift false-negatives vs Flash; cost is rounding-error |
| Stitching | MoviePy + ffmpeg local | Continuity with edu-vid-gen-cloud; full control over transitions |
| Observability sink | Supabase `eduplugin_events` on Edustack project + viewer at EduStack-Platform `/admin/eduplugin/runs` | No standalone VPS; reuses existing infra; one table, six streams |
| Brief UI | Localhost Node stdlib HTTP, random port | Zero deps, exits on submit |
| Update model | `git pull` (fast-forward only) from public GitHub | Fully manual via `/plugin-update`; no auto-check |
| Character modes | `human` / `abstract` / `none` | `none` skips Phase 3a and uses prompt-driven consistency block |
| Chapter content collection | Brief-collector asks for chapter content in BOTH script modes (since 0.4.0). Required for word_to_word, optional-but-recommended for standard. Pasted text persists to `<run-dir>/source/chapter.txt`. | Standard-mode scripts pre-0.4.0 drifted because they were written from `topic` + general knowledge. Grounding in actual chapter content cuts hallucinations. Orchestrator gates entry to Phase 1 on this; soft-warn in standard, hard-halt in word_to_word. |
| Human-character video | `fal-ai/wan/v2.7/image-to-video` (720p via config) when `brief.character_mode == "human"`; Seedance 1.5 Pro (720p, hardcoded) otherwise | Seedance + most i2v models distort/reject real human faces in keyframes. Wan 2.7 explicitly supports humans; smoke-validated 2026-05-18, identity locked. Seedance resolution is hard-pinned to 720p in [`scripts/phase_clips._resolution_for`](scripts/phase_clips.py) — a `models.yaml:video_i2v.resolution` override is ignored. Routing in [`scripts/phase_clips._resolve_video_stage`](scripts/phase_clips.py). |
| Clip-gen sequencing | Strictly sequential — one beat at a time, no parallelism | Earlier ThreadPoolExecutor parallelism was removed: fal queue caps (2 for new accounts) made it unreliable, and sequential gen keeps `run.json` job-id writes race-free. Each fal job id is persisted to `run.json` (`items.clip_jobs`) the instant a clip is enqueued, so a long/interrupted generation is recoverable by `request_id`. |
| Clip QA → no auto-regen | Generate once, flag `needs_review` on a `major` verdict | Clips are never auto-regenerated. A `major` QA verdict sets `needs_review: true` in `clips/summary.json` for Gate 4; the user drives `/create-video-regen` to retry. Removes the prior ≤2 auto-corrective regens. |
| Dialogue at clip layer | Opt-in via `brief.dialogues_enabled` (default off) | When off, every clip prompt receives a verbatim "no speech, no mouth movement for speech" audio direction. Stitcher still lays in narration VO + music; this only suppresses model-invented in-clip speech (Seedance hallucinates Mandarin, Wan 2.7 invents lip-sync motion). |
| Character sheet model | `fal-ai/gpt-image-2` at `image_size: landscape_16_9, quality: high` | gpt-image-2 holds the structured multi-region rich-template layout; Nano Banana 2 smeared the regions |
| Character description contract | `characters/descriptions.json` is pasted IDENTICALLY into every storyboard + clip prompt | One source of truth; identity locks across the pipeline. See [character-sheet-generator/references/prompt-template.md](skills/character-sheet-generator/references/prompt-template.md). |
| Image modes | `storyboard_panel` (gpt-image-2 sheet, sliced) / `per_keyframe` (Nano Banana 2) | User picks in brief; defaults to per_keyframe |
| Book mode | Optional sibling artifact: 0–12 opaque RGB PNGs at A4P (2480×3508) or A3L (4961×3508) @ 300 DPI on a white-flattened canvas with a painted soft-light text zone, post-video, picked via `brief.book.page_count_target` | Designers drop into InDesign and overlay text on the painted text zone at layout time. Previous RGBA-transparent default was dropped in 0.6.2 — gpt-image-2 painted a checker pattern when asked for transparent BG. |
| Book-from-keyframes | Standalone post-video path (`/create-book-from-keyframes`) that reuses the video's storyboard keyframes as book illustrations. Two render modes per page: (a) layout-renderer (default since 0.6.0) — sends keyframe as IMAGE 2 + template's layout reference as IMAGE 1 to gpt-image-2, produces a layout-composed page that holds the video's characters and style; (b) birefnet-only (legacy 0.5.0) — just cuts out the keyframe BG, no fresh image gen. Skips Phase B1/B2 entirely; goes straight to print-prep. | Layout-renderer mode gives layout-faithful text zones at the cost of ~Rs 15/page; birefnet-only mode is ~Rs 2/page but no text-zone composition. Mutually exclusive with default `brief.book.page_count_target > 0` on the same run. |
| Book-standalone (video-less) | `/create-book` builds a print-ready book WITHOUT making a video first. Mini-brief + chapter text (text/file/URL) + user-uploaded reference images. Uses the same shared two-image-prompting renderer (scripts/lib/book_layout_renderer.py) that the default Phase B2 and book-from-keyframes paths use. | Book is the deliverable for several customers who don't need video output. Same quality bar; no video phases means lower latency + cost. |
| Two-image prompting (shared renderer) | scripts/lib/book_layout_renderer.py is the single source of truth for all book page generation. Sends a LAYOUT REFERENCE (from seed/template-references/<template>/best_ref) as IMAGE 1 + the source CONTENT REFERENCE (keyframe / user upload) as IMAGE 2, with explicit "use LAYOUT from IMAGE 1, CONTENT/STYLE from IMAGE 2" prompt framing. Optional character sheets as IMAGE 3+. Ported from layout-gen — its dominant insight was "two-image prompting is king" for layout-faithful results. | Without explicit IMAGE 1 / IMAGE 2 framing, gpt-image-2 mixes layout and content guidance unpredictably. The shared renderer means every book path produces consistent output. Reference images live in seed/template-references/ — 39 images across 9 templates, ~5 MB. |
| Skill specs are the contract, not the references | Each Claude-driven skill (script-writer, vo-generator, storyboard-generator, clip-generator, stitcher) must define its rich output spec INLINE in the SKILL.md, with a quality bar and a common-failure-modes section. References are loaded on demand; the skill body is always loaded. Pre-0.4.1, loose Output specs led to ~30% variance across runs (sometimes Claude read the references and produced rich output, sometimes it didn't). Since 0.4.1, every skill enforces its rich format via the body itself. | Variance from "did Claude read the reference this time?" is the dominant pre-0.4.1 failure class. The fix is structural — not a model-choice problem. |
| Recommended client config | Claude Sonnet 4.6, reasoning effort `high` | Model + effort give an additional ~10–15% diligence headroom on top of the structural fix. Token cost is rounding error next to image (₹15+/call) and video (₹100+/call) gen. Document: `commands/create-video-setup.md`. |

---

## How Claude should think about tasks here

### Adding a new phase or skill
1. Read [skills/orchestrator/SKILL.md](skills/orchestrator/SKILL.md) first — the orchestrator owns phase ordering and gate routing.
2. Create `skills/<new-skill>/SKILL.md` + `references/*.md`. Use progressive disclosure: SKILL.md is short, references are loaded on demand.
3. Add the skill to `plugin.json`'s `skills[]`.
4. If it's a new phase, update orchestrator's phase routing table.
5. If it adds a brief field, also update [skills/brief-collector/references/brief-schema.md](skills/brief-collector/references/brief-schema.md) AND the form server's `index.html`/`form.js`.

### Touching a Python script
- `scripts/lib/` is shared. Phase scripts (`phase_*.py`) consume it.
- All external API calls go through `fal_client.py` or `elevenlabs_client.py` — never raw HTTP elsewhere. Both wrap retry + logging.
- All state mutations go through `run_state.RunState`. Never write `run.json` directly.

### Touching a book phase
- Three book phase scripts live alongside the video phase scripts: `scripts/phase_book_plan.py`, `phase_book_render.py`, `phase_book_print_prep.py`. They share `RunState`, `RunPaths`, `FalClient`, and `VisualAnalyzer`.
- Book pages are opaque RGB at 300 DPI on a white-flattened A4P or A3L canvas, with a painted soft-light text zone (NOT transparent — gpt-image-2 paints a checker pattern when asked for transparency). **Never burn text into the image.** Text intent lives only in the sidecar `.txt` and the `book_voice_copy` field of `book/plan.json`. `book_canvas.compose()` cover-scales the gpt-image-2 output to fill the print canvas and flattens to white.
- The book branch is **serial after video** in v1 — never start a book phase while a video phase is still running. The orchestrator's routing contract is in [skills/orchestrator/references/book-routing.md](skills/orchestrator/references/book-routing.md).
- Per-template composition rules (position, scale, margin) live in `scripts/lib/book_canvas.RULES`. Change a template's look there, not in `phase_book_print_prep.py`.
- Template selection for all three book paths goes through the [`book-template-picker`](skills/book-template-picker/SKILL.md) localhost gallery (see invariant #10). It's a zero-dep Node server cloned from the brief-collector pattern; the UI lives in `skills/book-template-picker/server/public/`. Don't add npm deps. If you change the template list, update the three synced manifests (invariant #10).

### Touching the brief UI
- The HTML form server has zero npm deps on purpose. Don't add Express or React.
- Untrusted browser input: a PreToolUse hook flags `innerHTML` usage. Use `textContent` or `appendChild`-based DOM construction.

### Touching the VPS
- The FastAPI service is auth-gated by bearer tokens minted at `POST /users`.
- JSONL on disk, partitioned by date + stream. Don't add a DB.
- Caddy handles TLS automatically via the `eduplugin.birdzeye.in` A record.

---

## Workflow conventions

### Commits
Use Conventional Commits prefixes (`feat:`, `fix:`, `chore:`, `docs:`). Body explains *why*. Sign with co-author trailer when assisted by Claude. The body of the commit drives `/plugin-update`'s changelog summary if you also update `CHANGELOG.md`.

### Versioning
Bump `plugin.json.version` in the same commit as user-visible behavior changes. CHANGELOG entry mandatory for any release commit.

### Dependencies
- **Python deps**: edit `requirements.txt`, run `uv pip sync` against `<output>/.venv`. The `/plugin-update` command auto-runs this for users on update.
- **Node deps**: avoid. The brief server uses Node stdlib only.

### Testing
No automated tests yet. The Verification section of the original implementation plan (see `~/.claude/plans/check-these-2-folders-glistening-stallman.md` if you have it) lists 14 manual end-to-end checks. Add tests opportunistically; don't refactor for testability prematurely.

---

## Where things live (quick reference)

| You want to… | Open this |
|---|---|
| Add or change a slash command | [commands/](commands/) + [plugin.json](plugin.json) |
| Tune what a phase does | `skills/<phase>/SKILL.md` + its `references/*.md` |
| Change retry behavior | [scripts/lib/fal_client.py](scripts/lib/fal_client.py), [scripts/lib/elevenlabs_client.py](scripts/lib/elevenlabs_client.py) |
| Change the brief form | [skills/brief-collector/server/public/](skills/brief-collector/server/public/) + [skills/brief-collector/references/brief-schema.md](skills/brief-collector/references/brief-schema.md) |
| Change the book template picker | [skills/book-template-picker/server/public/](skills/book-template-picker/server/public/) + sync the 3 manifests (invariant #10) |
| Change a default model | [seed/models.yaml](seed/models.yaml) (user overrides in `<output>/.config/models.yaml`) |
| Change observability schema | Apply a Supabase migration to `public.eduplugin_events` (via `Supabase-Edustack` MCP), update [scripts/lib/supabase_sink.py](scripts/lib/supabase_sink.py) writers, and update [EduStack-Platform/app/(authenticated)/admin/eduplugin/](../edustack/EduStack-Platform/app/(authenticated)/admin/eduplugin) reader in lockstep |
| Change Claude chat shipping | [hooks/ship-chat.sh](hooks/ship-chat.sh) + the consent prompt in [skills/setup/SKILL.md](skills/setup/SKILL.md) |
| Re-export Edustack seed data | Use the `Supabase-Edustack` MCP server (see `seed/form-options.json` for the source query) |

---

## Don't do

- Don't add a web UI for review gates. They are chat-only on purpose.
- Don't centralize state in Supabase. The sink is observability only; the source of truth is `<run-dir>/run.json` on the user's disk.
- Don't add a second image or video provider. Single-provider is the simplification we want.
- Don't add a database. JSONL on disk is sufficient for the VPS's life.
- Don't write skill descriptions starting with "This skill does X" — they activate poorly. Use trigger phrases that match user intent.
- Don't hardcode the Supabase URL outside `scripts/lib/config.DEFAULT_SUPABASE_URL`. Users may bring their own project (override at setup).

---

## Out of scope (intentionally deferred)

- Multi-part video series
- Batch generation
- Google Drive sync (edu-vid-gen-cloud's pattern; we use local + VPS)
- Multi-org / multi-user
- Hosting phase scripts on the VPS (planned v2; abstraction is in `vps_logger.py`)

---

## Doc-freshness hook (auto-enforced)

Two repo-local hooks live in [.claude/](.claude/). The Stop hook **blocks completion** any time you edit plugin source without also reviewing CLAUDE.md / docs/. Details: [.claude/README.md](.claude/README.md). Practical impact: when you finish a task that touched anything under `commands/`, `skills/`, `scripts/`, `hooks/`, `vps/`, `seed/`, or `plugin.json`, you must either update the relevant doc or explicitly `rm .claude/.docs-stale` with a one-line reason. No silent drift.

## Lineage

This plugin combines patterns from two predecessors. Neither repo is edited; both remain as references:

- `~/Documents/GitHub/edustack` — Next.js + Supabase web platform. Source of the prompt library (`seed/prompts/`), brief schema, gate model.
- `~/Documents/GitHub/edu-vid-gen-cloud` — first-gen Claude plugin. Source of `scripts/lib/_api-errors.md`, transitions reference, MoviePy stitcher patterns, audio-tags reference.

The implementation plan that produced this scaffold is at `~/.claude/plans/check-these-2-folders-glistening-stallman.md`.
