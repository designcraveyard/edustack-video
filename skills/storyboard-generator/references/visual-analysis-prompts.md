# Visual analysis prompts (Gemini 2.5 Pro via fal-ai/any-llm)

After every keyframe, Gemini scores it against the prompt. Output schema:

```jsonc
{
  "beat_id": 3,
  "checks": {
    "characters_present": ["Maya", "Ravi"],
    "characters_expected": ["Maya", "Ravi"],
    "character_match": true,

    "palette_consistent_with_sheet": true,
    "background_neutral_unless_required": true,
    "action_matches_prompt": true,
    "no_text_artifacts": true,
    "composition_readable_at_thumbnail": true
  },
  "issues": [
    { "severity": "warn", "code": "off_palette", "detail": "shirt is teal in prompt, came out olive" }
  ],
  "regen_recommendation": null,    // null | "minor" | "major"
  "corrective_addendum": null      // string to append to the prompt on retry
}
```

## Prompt template sent to Gemini

```
You are a continuity supervisor for an educational explainer video.

CONTEXT
- Beat label: <label>
- Original prompt: <storyboard prompt>
- Character description: <characters/sheet.png | description_block.md>

TASK
Inspect the attached image and return STRICT JSON (no prose) matching the schema below.
Severity is one of: warn (cosmetic), error (must regen).
If you recommend regen, write a 1-sentence corrective_addendum to append to the prompt.

SCHEMA
{...the JSON above...}
```

## Why Gemini 2.5 Pro and not Flash

Per-clip frame-by-frame continuity requires longer context and stronger spatial reasoning. Flash is fine for ad-hoc lookups but Pro materially reduces false-negative drift detection on hand-drawn styles. Cost difference is rounding-error on a 60-second video.
