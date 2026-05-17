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
