# Overnight summary — 2026-05-17 — book mode

## What landed

**Branch:** `feat/book-mode` (16 commits including this note)
**Version bump:** plugin `0.1.0` → `0.2.0`

### New capability
Book mode produces a curated 0–12-page set of **transparent-background RGBA PNG illustrations** sized to **A4 Portrait (2480×3508)** or **A3 Landscape (4961×3508)** at **300 DPI**, alongside the existing video pipeline. Pages are intended for book designers to drop into InDesign / Affinity and add their own text.

### Pipeline shape
Same brief, script, characters as the video. After Phase 6 (stitch) completes, if `brief.book.page_count_target > 0`:

1. **Phase B1 `book-plan`** — curates a page list (~60% reused video keyframes + ~40% book-only scenes), assigns one of 9 layout templates per page (content-type heuristic), rewrites narration into book voice. New chat **Gate B1**.
2. **Phase B2 `book-render`** — per page: `fal-ai/gpt-image-2` with `background=transparent` + reference images (character sheets + keyframe if present, cap 4) → `fal-ai/birefnet/v2` fallback when output isn't transparent → Gemini 2.5 Pro QA via `fal-ai/any-llm/vision` checking 4 binary axes (transparent BG, no text, character consistency, scene match) → up to 2 retries with corrective addendum.
3. **Phase B3 `book-print-prep`** — pure Pillow. Per-template composition rules in `scripts/lib/book_canvas.RULES` (position, scale, margin), Lanczos resize, auto-level + unsharp on RGB channels (alpha preserved), `info["dpi"]=(300,300)`. Sidecar `.txt` carries `book_voice_copy` for the designer.

### Per-page regen
`/create-book-regen page-NN [--template <id>] [--scene "<text>"] [--copy "<text>"]` — edits `plan.json` and re-runs Phase B2 + B3 for that page only.

### Brief-collector additions
New **Book** step in the form:
- Page count slider 0–12 (0 = no book; rest of section hides).
- Book voice dropdown: storybook_narrator / factual_calm / playful_rhyming.
- Template gallery: 9 cards with inline SVG wireframes + 2 thumbnail refs each. Click to multi-select 2–4.
- All 39 reference images + 9 wireframes bundled at `skills/brief-collector/server/public/templates/`. No external dependency on the Vercel-hosted layout-templates-web.

### Files
- **15 new files** (3 phase scripts, 3 skills with SKILL.md, 2 references for book-render, prompt patterns ported and adapted from layout-gen, `book_canvas.py`, 1 command, 1 routing reference, manifest + 9 wireframes).
- **10 modified files** (plugin.json, CHANGELOG.md, CLAUDE.md, brief-schema.md, models.yaml, fal_client.py, visual_analyzer.py, orchestrator SKILL.md, form server html/js/css/mjs).
- **Bundled assets**: 39 reference images ported from `layout-gen/template-references/`.

### Provider stack — unchanged invariant
All external calls still go through fal.ai. Two new fal endpoints used:
- `fal-ai/gpt-image-2` — page illustration with `background=transparent`.
- `fal-ai/birefnet/v2` — BG removal fallback.
QA continues to use the existing `fal-ai/any-llm/vision` path with Gemini 2.5 Pro.

### No new system dependencies
- Pillow was already pinned in `requirements.txt` (>=10.0.0). No new pins required.
- ImageMagick is **not** added (Pillow handles the RGBA + Lanczos + sharpen path we need; ImageMagick is only better when targeting CMYK, which we explicitly don't).
- No PDF tooling. No Node deps added to the brief server.

### Observability
Existing Supabase event streams cover book phases via the existing shapes (`phase: book-plan|book-render|book-print-prep`). No schema migration needed; the EduStack-Platform `/admin/eduplugin/runs` reader will surface them automatically.

## What's tested (overnight)

| Component | Test |
|---|---|
| `book_canvas.compose` | Smoke test: all 9 templates compose; resulting size matches canvas dims; mode=RGBA. ✅ |
| `phase_book_plan.py` | End-to-end smoke with synthetic `brief.json` + `script.md` + 3 fake beats: emits valid `book/plan.json` with 4 pages (3 reused + 1 book-only), templates from shortlist, correct canvas. ✅ |
| `phase_book_print_prep.py` | End-to-end smoke with synthetic Phase-B2 PNGs: produces A4P (2480×3508) and A3L (4961×3508) RGBA outputs at 300 DPI with sidecar `.txt` files. ✅ |
| `phase_book_render.load_templates_md` | Parses all 9 template prompt patterns from the ported `templates.md`. ✅ |
| `phase_book_render.render_prompt` | Substitutes placeholders + appends transparent-BG directive. ✅ |
| Python syntax — all phase + lib files | `ast.parse` across `scripts/**/*.py`. ✅ |
| `plugin.json` | Valid JSON, 12 skills + 9 commands listed. ✅ |
| Brief UI structure | DOM contains `book-section`, `book-page-count`; `form.js` wires `selectedTemplates` + `brief.book` payload; manifest has exactly 9 entries. ✅ |

## What's NOT tested

- **Live fal-ai/gpt-image-2 call.** Requires `<output>/.config/fal.key` and incurs cost. Not run.
- **Live birefnet fallback.** Same.
- **Live `fal-ai/any-llm/vision` QA pass on a real page.** Same.
- **Real brief-collector form launch in a browser.** Implementation is straight DOM + fetch — confirmed structurally — but a real `node server.mjs` + browser interaction wasn't executed.
- **Real Gate B1 chat-side rendering.** Orchestrator changes are documented but not exercised end-to-end.
- **`/create-book-regen` slash command invocation.** Command file written and registered, but not run through the slash-command harness.

The first real end-to-end run with a fal key should be the v1 acceptance test. Expected per-page cost is roughly $0.05–0.15 (gpt-image-2) + $0.01 (birefnet, only when triggered) + $0.01 (Gemini QA), so a 12-page book is roughly $0.80–$2.

## Open questions resolved by the planner overnight (with assumptions)

1. **gpt-image-2 reference image limit:** capped at 4 in `FalClient.gpt_image_2_book_page` (1 keyframe + up to 3 character sheets). Conservative; matches the documented gpt-image-1 limit and what `image_urls` typically accepts. If runtime testing shows the limit is higher, raise the cap.
2. **Static-image QA fal route:** confirmed by inspecting `scripts/lib/visual_analyzer.py`. Reused `fal-ai/any-llm/vision` via the existing `FalClient.any_llm_vision()` helper. Same path as `analyse_keyframe()` and `analyse_character_sheet()`.
3. **Pillow dependency:** already pinned at `Pillow>=10.0.0` in `requirements.txt`. No change.

## Risks / things to watch on first real run

1. **gpt-image-2 may paint a background despite `background=transparent` + prompt directive.** Mitigation: birefnet fallback engages when the border-alpha heuristic flags >2% opaque border pixels. Watch the QA `transparent_background` rate on the first run.
2. **Character drift across 12 pages.** Video pipeline keeps ~6–8 keyframes consistent; 12 book pages stretches it. Mitigation: each page receives the character sheet refs; QA flags drift; 2 retries per page.
3. **Template-aware composition rules** (`scripts/lib/book_canvas.RULES`) are table-driven and reasonable defaults but unverified visually. Smoke output proves the math is right — composition aesthetics need a human eye on the first real book.
4. **gpt-image-2 endpoint name** is the public fal route. If fal has versioned it (e.g. `fal-ai/gpt-image-2/v2`), the call will need adjusting in `fal_client.py:gpt_image_2_book_page`.

## Next steps for you

1. Open a PR from `feat/book-mode` → `main`. (Branch is pushed.)
2. Run a real generation on a small brief with `page_count_target=3` to validate the live fal calls and the Gate B1 chat flow.
3. Observe the run in the EduStack-Platform admin viewer (`/admin/eduplugin/runs`) — the existing reader should pick up the `book-*` phase events without code changes.
4. If first run looks good, merge.

## Commits on this branch (newest first)

```
release(0.2.0): book mode — register skills/commands, doc invariants, changelog
feat(commands): /create-book-regen for per-page book regeneration
feat(orchestrator): post-video book branch routing + Gate B1 contract
feat(book): Phase B3 (book-print-prep) — Pillow composer for A4P/A3L 300dpi RGBA
feat(book): Phase B2 (book-render) — gpt-image-2 + birefnet fallback + QA retry loop
feat(book): Phase B1 (book-plan) skill + script with content-type template assignment
feat(book): canvas compose rules + Pillow helpers (A4P/A3L 300dpi)
feat(qa): analyse_book_page (4 binary checks via fal-ai/any-llm/vision)
feat(fal): gpt_image_2_book_page + birefnet_remove_bg helpers
feat(book-plan): port layout-gen prompt patterns (transparent-BG adapted)
feat(config): seed book.* model defaults (gpt-image-2 + birefnet + qa + canvases)
feat(brief): book step in form (page count, voice, template gallery)
docs(brief): add book.* schema to brief-schema reference
feat(brief): bundle layout-gen template assets (39 refs + 9 wireframes + manifest)
docs: book-mode design spec + implementation plan
```

— assistant, 2026-05-17 (overnight)
