# CLAUDE.md — `edustack-video` workspace memory

This file orients Claude Code (and future maintainers) when working in this repo. Read it before touching anything non-trivial.

---

## What this is

`edustack-video` is a **Claude Code plugin** that generates educational explainer videos through a 5-phase pipeline (script → VO → characters → storyboard → clips → stitch) with 4 chat-driven review gates.

The plugin lives in this repo and is installed by end users via `claude plugin add https://github.com/designcraveyard/edustack-video`. Updates are pulled manually via `/plugin-update`.

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
3. **Image aspect derives from `brief.aspect`.** Never hardcode 16:9 in storyboard or clip code. Read `<output>/.config/models.yaml > aspect_sizes[brief.aspect]`. Character sheets are the only intentional exception (always 1:1).
4. **Supabase observability is best-effort.** `scripts/lib/supabase_sink.py` MUST NOT raise on failure — fall back to `<run-dir>/logs/local.jsonl`. The pipeline never blocks on the sink. `scripts/lib/vps_logger.py` is a thin alias re-exporting `SupabaseSink` for back-compat.
5. **Keys never leave the user's machine.** `<output>/.config/{fal,elevenlabs}.key` are read by local Python only. The Supabase sink writes metadata refs (paths + sha256, prompt sha) — never raw artifacts and never the API keys.
6. **Form field names must match `brief.json` schema** in [skills/brief-collector/references/brief-schema.md](skills/brief-collector/references/brief-schema.md). The Edustack web platform reads the same shape — drift breaks cross-port.
7. **Gates are chat-only.** No web UI. Surfaced via clickable file paths in the chat message; user replies `approve` or `regen <target>: <comment>`.
8. **Book pages have their own canvas, not `brief.aspect`.** A4P (2480×3508 @ 300 DPI) for 3:4 templates, A3L (4961×3508 @ 300 DPI) for 16:9 templates. The canonical map lives in [`scripts/lib/book_canvas.RULES`](scripts/lib/book_canvas.py). Do not derive book canvases from `brief.aspect`.
9. **Book pages are RGBA with transparent BG.** Never burn text into the image. The intended text lives in the sidecar `<run-dir>/book/print/page-NN.txt` and in the `book_voice_copy` field of `book/plan.json`. Phase B2 prompts gpt-image-2 to leave the text zone transparent; the Phase B2 birefnet/v2 fallback cleans up if the model paints a background anyway.

---

## Architecture decisions (locked)

| Area | Decision | Why |
|---|---|---|
| Image + video + vision | fal.ai only | Single key, single retry surface |
| VO | ElevenLabs direct (not via fal) | Need word-level timestamps for stitcher |
| Vision model | Gemini 2.5 Pro via `fal-ai/any-llm` → OpenRouter | Pro materially reduces drift false-negatives vs Flash; cost is rounding-error |
| Stitching | MoviePy + ffmpeg local | Continuity with edu-vid-gen-cloud; full control over transitions |
| Observability sink | Supabase `eduplugin_events` on Edustack project + viewer at EduStack-Platform `/admin/eduplugin/runs` | No standalone VPS; reuses existing infra; one table, six streams |
| Brief UI | Localhost Node stdlib HTTP, random port | Zero deps, exits on submit |
| Update model | `git pull` (fast-forward only) from public GitHub | Fully manual via `/plugin-update`; no auto-check |
| Character modes | `human` / `abstract` / `none` | `none` skips Phase 3a and uses prompt-driven consistency block |
| Image modes | `storyboard_panel` (gpt-image-2 sheet, sliced) / `per_keyframe` (Nano Banana 2) | User picks in brief; defaults to per_keyframe |
| Book mode | Optional sibling artifact: 0–12 transparent-BG RGBA PNGs at A4P (2480×3508) or A3L (4961×3508) @ 300 DPI, post-video, picked via `brief.book.page_count_target` | Designers drop into InDesign and convert CMYK at layout time |

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
- Book pages are RGBA at 300 DPI on a transparent A4P or A3L canvas. **Never burn text into the image.** Text intent lives only in the sidecar `.txt` and the `book_voice_copy` field of `book/plan.json`.
- The book branch is **serial after video** in v1 — never start a book phase while a video phase is still running. The orchestrator's routing contract is in [skills/orchestrator/references/book-routing.md](skills/orchestrator/references/book-routing.md).
- Per-template composition rules (position, scale, margin) live in `scripts/lib/book_canvas.RULES`. Change a template's look there, not in `phase_book_print_prep.py`.

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
