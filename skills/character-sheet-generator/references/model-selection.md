# Model selection (Phase 3a)

Default per `seed/models.yaml`: **`fal-ai/nano-banana-2`** for both human and abstract sheets.

| Need | Model | Why |
|---|---|---|
| Default character sheet | `fal-ai/nano-banana-2` | Best Nano Banana 2 result for grid sheets; respects neutral background. |
| Photorealistic human | `fal-ai/flux/pro-v1.1-ultra` (override) | Tighter realism if `brief.style` is "cinematic". |
| Stylized 2D | `fal-ai/imagen4` (override) | Stronger style adherence on hand-drawn looks. |

Override via `<output>/.config/models.yaml`:

```yaml
character_sheet:
  model: fal-ai/flux/pro-v1.1-ultra
  cfg: 4
  size: 1024x1024
```

## Why not gpt-image-2 here

gpt-image-2 is our **storyboard panel** choice (Mode A) because it handles multi-cell consistency well. But for character sheets we want the cleanest single-subject render, which Nano Banana 2 nails out of the box. Reserving gpt-image-2 for storyboards also lets us throttle a single endpoint.
