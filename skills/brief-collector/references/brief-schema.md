# brief.json schema

Mirrors the Edustack `runs.brief` JSONB column so projects can be cross-ported between the web platform and this plugin.

```jsonc
{
  "topic": "How photosynthesis works",
  "class_level": 6,                    // 1..12
  "language": "English",               // "English" | "Hindi" | ...
  "style": "2D animated",              // "Pixar" | "2D animated" | "cinematic" | "whiteboard" | ...
  "aspect": "16:9",                    // "16:9" | "9:16" | "1:1"

  "script_mode": "standard",           // "standard" | "word_to_word"
  "duration_seconds": 60,              // 15|30|45|60|90|120 — omitted when script_mode == word_to_word
  "chapter_source": null,              // { "kind": "file" | "text" | "url", "ref": "<path or url or inline text>" } when word_to_word

  "character_mode": "human",           // "human" | "abstract" | "none"
  "image_mode": "per_keyframe",        // "storyboard_panel" | "per_keyframe"

  "ambient_category": "ambient_calm",  // "ambient_calm" | "ambient_playful" | "ambient_drama" | "none"
  "subtitles_enabled": true,
  "annotations_enabled": false,
  "voice_id": "21m00Tcm4TlvDq8ikWAM",  // ElevenLabs voice id; fetched from EL on form load
  "notes": ""                          // free-text stylistic guidance
}
```

## Validation rules

- `script_mode == "word_to_word"` REQUIRES `chapter_source` and IGNORES `duration_seconds`.
- `character_mode == "none"` → Phase 3a is **skipped**; `characters/description_block.md` is written instead.
- `image_mode == "storyboard_panel"` → uses gpt-image-2 to produce one multi-panel sheet, then slices locally.
- `image_mode == "per_keyframe"` → uses Nano Banana 2 per beat (recommended for character consistency).

## Seed values

Dropdown values come from `seed/form-options.json` (lifted from Edustack `generate_form_options` table). Defaults come from `seed/generation-defaults.json`.

## `book` (optional)

When present and `book.page_count_target > 0`, the orchestrator runs Phase B1–B3 after the video branch completes. The Edustack web platform must mirror this shape exactly when porting.

```json
{
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

| Field | Type | Notes |
|---|---|---|
| `page_count_target` | int 0–12 | `0` skips book phases. `1..12` = exact page count. |
| `templates` | string[] 2–4 | Subset of: `full-bleed-with-text-zone`, `vignette-on-page`, `split-layout`, `scattered-spots`, `full-spread-no-text`, `illustrated-border`, `character-text-pocket`, `connected-infographic`, `spread-scene-plus-spots`. |
| `voice` | enum | `storybook_narrator` \| `factual_calm` \| `playful_rhyming`. |
| `deliverable.format` | const | `png_rgba` (v1). |
| `deliverable.canvas_portrait` | const | `A4` (2480×3508 @ 300 DPI). |
| `deliverable.canvas_landscape` | const | `A3` (4961×3508 @ 300 DPI). |
| `deliverable.dpi` | int | `300` (v1). |
