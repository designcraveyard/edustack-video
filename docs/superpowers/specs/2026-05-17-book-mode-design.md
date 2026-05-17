# Book Mode — Design Spec

**Date:** 2026-05-17
**Status:** Draft (brainstorming complete, pending user review before implementation plan)
**Owner:** edustack-video plugin

---

## 1. Goal

Add a **Book Mode** to the `edustack-video` plugin that produces a curated set of A4-Portrait / A3-Landscape **RGBA PNG illustrations** as a sibling artifact to the explainer video. The two artifacts share `brief`, `script`, and `characters` but have independent page lists and visual treatments.

Book pages are intended for **book designers** to drop into InDesign/Affinity layouts: transparent background, illustration only, no burnt-in text, sized to print canvas at 300 DPI.

The functionality is ported from the standalone `layout-gen` plugin (Gemini-based, 9 templates, Next.js gallery) into this plugin and re-grounded on the fal.ai-only provider stack.

---

## 2. Non-goals (v1)

- PDF assembly, CMYK output, bleed/crop marks.
- Parallel execution of video and book branches (serial only — book runs after video).
- Per-image review gate after `book-render` (QA loop handles drift).
- Multi-book, batch, or series workflows.
- Hosting book phases on the VPS.
- Standalone `/edustack-book` command — book mode is invoked exclusively via the existing `/edustack-video` flow with `brief.book.page_count_target > 0`.

A per-page regen command (`/edustack-video-book-regen page-NN`) is in scope so Gate B1 replies like "regen page 4" have a concrete handler.

---

## 3. Architecture

### 3.1 Flow

```
brief-collector (browser)
  ├─ Step 1: existing brief fields
  └─ Step 2 NEW: Book
      ├─ page_count_target slider (0–12; 0 = no book)
      ├─ template shortlist (2–4 of 9 cards; only shown if count ≥ 1)
      └─ book voice dropdown
        ↓
brief.json (now may carry brief.book.*)
  ↓
Phase 1: script ── Gate 1 ──┐
  ↓                          │
Phase 2..6 (video, existing) │
  ↓                          │
final.mp4 ───────────────────┤  if brief.book.page_count_target > 0:
                             ▼
                       Phase B1: book-plan
                       ├─ uses script.json + characters/* + keyframes/*
                       ├─ produces book/plan.json (page_count_target pages,
                       │  each w/ template assignment + book-voice copy +
                       │  scene prompt + keyframe/character refs)
                       └─ Gate B1 (chat): approve / regen page N / regen all
                             ↓
                       Phase B2: book-render
                       ├─ per page → fal-ai/gpt-image-2 with image_url refs
                       ├─ if opaque BG → fal-ai/birefnet/v2 fallback
                       ├─ visual QA via fal-ai/any-llm → openrouter → gemini-2.5-pro
                       └─ output: book/pages/page-NN.png (RGBA, native dims)
                             ↓
                       Phase B3: book-print-prep
                       ├─ Pillow: Lanczos upscale, template-aware compositing
                       │  onto A4P (2480×3508) or A3L (4961×3508) canvas @ 300 DPI
                       ├─ mild auto-level + unsharp on RGB channels, preserve alpha
                       └─ output: book/print/page-NN.png + page-NN.txt sidecar
```

### 3.2 Cross-file invariants honoured

- **`plugin.json` lists everything**: new skills (`book-plan`, `book-render`, `book-print-prep`) and the regen command registered.
- **Image aspect derives from canvas, not brief.aspect**: book pages use `A4P` or `A3L` based on the assigned template's natural aspect (3:4 → A4P, 16:9 → A3L). `brief.aspect` continues to drive video only.
- **Supabase sink stays best-effort**: book phases reuse `SupabaseSink`/`VpsLogger`; failures fall back to `<run-dir>/logs/local.jsonl`. No schema migration needed; events use existing shapes with `phase: book-plan|book-render|book-print-prep`.
- **Keys local-only**: gpt-image-2 + birefnet + openrouter calls all flow through fal.ai with the existing `<output>/.config/fal.key`. No new key material.
- **Form schema mirrors Edustack web platform**: `brief.book.*` shape documented in `skills/brief-collector/references/brief-schema.md`; web platform must adopt the same shape before cross-port is exercised.
- **Gates are chat-only**: Gate B1 is a Markdown summary of `book/plan.json` posted to chat; user replies `approve` or `regen page N: <comment>`.

---

## 4. Brief schema additions

```json
{
  "topic": "...",
  "aspect": "16:9",
  "...": "(existing fields)",
  "book": {
    "page_count_target": 12,
    "templates": ["split-layout", "scattered-spots", "vignette-on-page"],
    "voice": "storybook_narrator",
    "deliverable": {
      "format": "png_rgba",
      "canvas_portrait": "A4",
      "canvas_landscape": "A3",
      "dpi": 300
    }
  }
}
```

- `page_count_target`: integer 0–12. `0` skips Phase B1–B3 entirely; book section in the form is collapsed.
- `templates`: 2–4 of the 9 supported templates. Phase B1 assigns one per page based on content type.
- `voice`: enum `storybook_narrator | factual_calm | playful_rhyming`.
- `deliverable`: fixed defaults in v1; surfaced in schema for forward compat.

Updated authoritative location: `skills/brief-collector/references/brief-schema.md`.

---

## 5. Phases

### 5.1 Phase B1 — `book-plan`

- **Script**: `scripts/phase_book_plan.py`
- **Skill**: `skills/book-plan/SKILL.md` + `references/templates.md` (prompt patterns ported from layout-gen).
- **Inputs**: `brief.json`, `script.json`, `characters/*.png` (Phase 3), `phase4/keyframes/*` (Phase 4), `brief.book.templates`.
- **Output**: `<run-dir>/book/plan.json`:
  ```json
  {
    "pages": [
      {
        "page_no": 1,
        "scene_source": "video_scene_3",
        "keyframe_ref": "phase4/keyframes/scene-03.png",
        "character_refs": ["characters/mowgli.png"],
        "template": "split-layout",
        "canvas": "A3L",
        "scene_prompt": "Mowgli sleeping with wolves under a banyan tree, dawn light",
        "book_voice_copy": "When the moon dipped low, Mowgli curled up beside his wolf brothers.",
        "text_zone_hint": "left third, top-aligned, 3 lines"
      }
    ]
  }
  ```
- **Logic**: a single Claude call with the prompt at `skills/book-plan/SKILL.md` produces a curated list of exactly `page_count_target` pages. Mix of reused video scenes (when their `keyframe_ref` fits a chosen template) and new book-only scenes that elaborate on the script. Template assignment uses the layout-gen content-type rules.
- **Gate B1**: orchestrator posts `book/plan.json` summary to chat with thumbnails (file:// links). User reply parsed via existing gate-handler patterns.

### 5.2 Phase B2 — `book-render`

- **Script**: `scripts/phase_book_render.py`
- **Skill**: `skills/book-render/SKILL.md` + `references/qa-prompt.md`.
- **Inputs**: `book/plan.json`, all referenced keyframe / character images.
- **Per-page algorithm**:
  1. Build gpt-image-2 prompt:
     - Template's prompt pattern from `references/book-templates.md`.
     - `scene_prompt` from plan.
     - Explicit instructions: *"Transparent background. Illustration only. Leave the {text_zone_hint} region empty — no text, no lettering."*
     - `image_url` array: character sheets first, keyframe last (if present).
  2. Call `fal-ai/gpt-image-2` via existing `fal_client.py`.
  3. If returned PNG has opaque pixels in >2% of canvas border, call `fal-ai/birefnet/v2` to extract RGBA cutout.
  4. Visual QA call via the fal → openrouter route (exact endpoint mirrors clip-QA's `fal-ai/openrouter/router/video`; static-image equivalent resolved in impl plan) targeting `google/gemini-2.5-pro` with QA prompt asserting: character consistency, scene match, empty text zone, transparent background. Returns four binary axes; threshold 4/4.
  5. On QA fail: up to 2 retries with adjusted prompt (drift-aware). On 3rd failure: write `qa.json` with `status: failed`, surface in Gate B1 follow-up so user can manually regen.
- **Output**: `<run-dir>/book/pages/page-NN.png` (RGBA, gpt-image-2 native ≈1024×1456 or 1456×1024) + `<run-dir>/book/pages/page-NN.qa.json`.

### 5.3 Phase B3 — `book-print-prep`

- **Script**: `scripts/phase_book_print_prep.py`
- **Skill**: `skills/book-print-prep/SKILL.md`.
- **Helper**: `scripts/lib/book_canvas.py` — template-aware compositing table.
- **Per-page algorithm** (Pillow only, no ImageMagick):
  1. Open `book/pages/page-NN.png` (RGBA).
  2. Resolve target canvas: A4P = `2480×3508` or A3L = `4961×3508` @ 300 DPI.
  3. Lookup template's compose rule (`book_canvas.RULES[template]`): position (e.g. `left_60_percent`, `center_60_percent_scale`, `full_bleed`), padding, scale factor.
  4. Lanczos resize illustration; auto-level + unsharp mask `(radius=1.5, amount=0.7, threshold=2)` on RGB channels with alpha preserved.
  5. Paste onto blank RGBA canvas at the computed position.
  6. Set `info["dpi"] = (300, 300)`; save PNG.
  7. Write `<run-dir>/book/print/page-NN.txt` with `book_voice_copy` for designer reference.
- **Output**: `<run-dir>/book/print/page-NN.png` + `<run-dir>/book/print/page-NN.txt`.

---

## 6. Brief-collector UI changes

- Single Node-stdlib server, same URL, **no new deps**.
- New `Book` step added to existing form:
  - `page_count` number/slider 0–12. `0` collapses the rest.
  - Template gallery: 9 cards rendered from `public/templates/manifest.json`. Each card shows inline SVG wireframe, two reference thumbnails, frequency-of-use badge, "best for" tags, and natural aspect (3:4 / 16:9).
  - Multi-select chip toggles, with a banner if <2 or >4 chosen.
  - Voice dropdown.
- All gallery assets (9 wireframes + 39 ref images) ported into `skills/brief-collector/server/public/templates/`. No external network calls.
- Untrusted-DOM rule honoured: chips and gallery cards built via `textContent` and `appendChild`, never `innerHTML` (per repo pre-commit hook).

---

## 7. Provider routing

| Step | fal endpoint | Cost order | Latency order |
|---|---|---|---|
| Illustration | `fal-ai/gpt-image-2` | $$ | ~10–20s/page |
| BG removal fallback | `fal-ai/birefnet/v2` | $ | ~2–3s/page (only when needed) |
| Visual QA | fal → openrouter → `google/gemini-2.5-pro` (exact fal route mirrors clip-QA's `fal-ai/openrouter/router/video`; static-image equivalent confirmed in impl plan) | $ | ~3–5s/page |

`<output>/.config/models.yaml` additions:

```yaml
book:
  illustration:
    provider: fal
    model: fal-ai/gpt-image-2
    native_output_sizes: { portrait: "1024x1456", landscape: "1456x1024" }   # native gpt-image-2 output; upscaled to A4P/A3L canvas in B3
  bg_removal:
    provider: fal
    model: fal-ai/birefnet/v2
  qa:
    provider: fal
    # Endpoint analogous to clip QA routing (fal-ai/openrouter/router/video for clips);
    # the static-image equivalent fal route is resolved during implementation.
    model: fal-ai/openrouter/router   # placeholder; confirm in implementation plan
    model_id: google/gemini-2.5-pro
    threshold: 4
    max_retries: 2
```

All three endpoints reuse `scripts/lib/fal_client.py`'s existing retry/log harness. `_api-errors.md` extended with gpt-image-2 + birefnet error catalogue.

---

## 8. Orchestrator changes

`skills/orchestrator/SKILL.md` gains a routing addendum:

```
After all video phases complete:
  if brief.book and brief.book.page_count_target > 0:
    run phase_book_plan.py → Gate B1
    on approve → run phase_book_render.py → run phase_book_print_prep.py
    on regen page N: <comment> → update plan.json entry, rerun book-render
                                  for that page only, rerun book-print-prep
                                  for that page only
```

A new reference doc `skills/orchestrator/references/book-routing.md` carries this contract.

---

## 9. File layout

```
edustack-video/
├── plugin.json                                              ← updated
├── commands/
│   └── edustack-video-book-regen.md                        NEW
├── skills/
│   ├── orchestrator/
│   │   ├── SKILL.md                                        ← updated
│   │   └── references/book-routing.md                      NEW
│   ├── brief-collector/
│   │   ├── references/brief-schema.md                      ← updated
│   │   └── server/public/
│   │       ├── index.html                                  ← updated
│   │       ├── form.js                                     ← updated
│   │       └── templates/                                  NEW
│   │           ├── manifest.json
│   │           ├── refs/                                   (39 ref images)
│   │           └── wireframes/                             (9 SVGs)
│   ├── book-plan/                                          NEW
│   │   ├── SKILL.md
│   │   └── references/templates.md
│   ├── book-render/                                        NEW
│   │   ├── SKILL.md
│   │   └── references/qa-prompt.md
│   └── book-print-prep/                                    NEW
│       └── SKILL.md
├── scripts/
│   ├── phase_book_plan.py                                  NEW
│   ├── phase_book_render.py                                NEW
│   ├── phase_book_print_prep.py                            NEW
│   └── lib/
│       ├── fal_client.py                                   ← updated
│       ├── book_canvas.py                                  NEW
│       └── _api-errors.md                                  ← updated
├── seed/
│   └── models.yaml                                         ← updated
└── docs/superpowers/specs/2026-05-17-book-mode-design.md   (this spec)
```

Run-dir layout per book run:

```
<output>/<run-id>/
  brief.json                       (may carry .book)
  script.json
  characters/
  phase4/keyframes/
  phase5/clips/
  final.mp4
  book/                            NEW
    plan.json                      (Phase B1)
    pages/page-NN.png              (Phase B2)
    pages/page-NN.qa.json
    print/page-NN.png              (Phase B3)
    print/page-NN.txt
  logs/local.jsonl
```

---

## 10. Dependencies

- **Python**: `Pillow` pinned explicitly in `requirements.txt` (verify whether it is already a transitive dep during impl; either way the pin is required). No `ImageMagick`, no `numpy` strictly required.
- **Node**: unchanged — brief server remains stdlib-only.
- **System binaries**: none added.

The existing `edu-vid-gen-cloud/scripts/enhance-for-print.mjs` (Node + ImageMagick) is referenced as **prior art for the upscale + sharpen pipeline** but not ported as-is — its CMYK conversion is intentionally dropped because we output RGBA PNG.

---

## 11. Prompting strategy (ported from layout-gen)

The layout-gen plugin ships two prompt sources we adopt:

1. **Canonical prompt patterns** — `layout-gen/skills/layout-gen/references/templates.md` (232 lines). One templated prompt per template with `{placeholders}` (e.g. `{scene_description}`, `{text_zone_side}`, `{vignette_position}`, `{art_style_description}`). Ported verbatim into `skills/book-render/references/book-templates.md`, then adapted for our pipeline differences:
   - **Replace** `"No text, no words, no letters, no numbers."` (already present in every pattern) with the stronger directive `"Transparent background. No text, no words, no letters. The text zone region must be left fully transparent — no painted background, no parchment, no light wash. Illustration elements only."`
   - **Replace** any `"warm cream tone"` / `"soft white page"` text-zone language with `"this region is transparent"` so gpt-image-2 doesn't paint the text-zone background.
   - **Append** a reference-image preamble: `"Use the character and art style from these reference images. Match the characters' appearance exactly across all generated pages."` — gpt-image-2 honours multi-image refs differently from Gemini, and Phase 3's character sheets must be the dominant style anchor.

2. **Empirical generation log** — `layout-gen/generation-prompts-log.md` (259 lines). A record of which placeholder values worked for actual scenes (e.g. for full-bleed: `text_zone_side: RIGHT, bleed_elements: light rays + leaves`). Ported into `skills/book-render/references/prompts-log.md` as a few-shot reference the Phase B1 planner reads when filling placeholders.

**Two-stage prompt assembly** (in `phase_book_plan.py` → consumed by `phase_book_render.py`):

- **Phase B1 picks the placeholders** for each page: it has the script context, character names, scene mood, and chosen template — so it's the right phase to fill `text_zone_side`, `vignette_position`, `bleed_elements`, `art_style_description`, etc. These are stored in `plan.json` per page under a `prompt_params` object.
- **Phase B2 assembles the final prompt** by loading the template pattern from `book-templates.md`, substituting `prompt_params`, appending the transparent-BG directive, and submitting to `fal-ai/gpt-image-2`. Phase B2 itself is mechanical — no creative decisions live there.

**QA prompt** (`skills/book-render/references/qa-prompt.md`) is authored fresh (not ported) because layout-gen has no QA pass. It asks Gemini 2.5 Pro to score four binary axes against the page PNG: `transparent_background`, `no_text_in_image`, `character_consistency_vs_refs`, `scene_matches_prompt`. Threshold = 4/4 to pass; anything less triggers retry.

---

## 12. Risks

1. **gpt-image-2 transparent-BG fidelity**: not guaranteed across all templates. Mitigation: birefnet fallback when QA flags opaque BG. Cost: ~$0.01/page + ~3s when triggered.
2. **Character drift across 12 pages**: video pipeline keeps ~6–8 keyframes consistent; 12 book pages stretches that. Mitigation: every page receives the full character-sheet pack as image refs; QA flags drift; up to 2 retries per page.
3. **Template-aware composing rules**: `book_canvas.py` encodes positioning for 9 templates; ~150 lines table-driven. Risk of mis-positioning for edge-case templates (illustrated-border, scattered-spots). Mitigation: visual smoke test on each template during implementation.
4. **gpt-image-2 reference-image count limits**: gpt-image-2 may cap input image count. If a page references 3 character sheets + a keyframe (4 refs), we may need to merge sheets into a single composite ref first. Mitigation: pre-build a "character ensemble" sheet during Phase 3 when book mode is enabled.
5. **Book-voice rewriting in B1**: requires a Claude prompt that holds the source script's facts steady while shifting voice. Risk of factual drift. Mitigation: each plan entry includes the source script line as `source_text` for traceability; QA can flag if `book_voice_copy` strays semantically.

---

## 13. Open questions for the implementation plan

These are intentionally unresolved in the spec; the impl plan's first sub-tasks resolve them:

1. **Reference image limits** for `fal-ai/gpt-image-2` — max `image_url` count. If <4, Phase 3 must produce a single "character ensemble" composite sheet when book mode is enabled.
2. **Static-image QA fal route** — clip QA uses `fal-ai/openrouter/router/video`; the static-image equivalent (likely `fal-ai/openrouter/router` or `fal-ai/any-llm`) needs confirmation before `phase_book_render.py` is written.
3. **Pillow dependency status** — whether already a transitive dep via existing video/stitch toolchain, or genuinely new.

---

## 14. Verification (manual, no automated tests yet)

1. Run `/edustack-video` with `page_count_target=0`. Confirm flow is byte-identical to current video-only flow.
2. Run with `page_count_target=6`, two templates selected. Confirm Gate B1 fires, plan.json has 6 pages, two templates distributed sensibly.
3. Approve plan. Confirm 6 pages render as RGBA PNGs, transparent backgrounds, no burnt-in text.
4. Confirm `book/print/page-NN.png` opens at A4P or A3L (per template) at 300 DPI with the illustration positioned per template rule.
5. Reply `regen page 3: make this a vignette` at Gate B1. Confirm only page 3 re-renders.
6. Confirm Supabase events emit `phase: book-*` rows; admin reader at EduStack-Platform `/admin/eduplugin/runs` lists them without code changes.
7. Verify `<run-dir>/logs/local.jsonl` carries fallback events when Supabase is down (kill network, rerun).
