# Character description block (mode: none)

When `character_mode: none`, we don't generate a character sheet. Instead we generate a structured **description block** that is prepended verbatim to every storyboard prompt and every clip prompt — so the generator sees the same character descriptions every time, eliminating drift.

## Template

```
## Characters

- **<name or role>** (recurring): <species/age> · <build/height> · <hair: color, style, length> · <eyes: shape, color> · <skin/coat: tone, texture> · <signature outfit: top, bottom, accessory> · <key prop or expression>.
- **<name or role>**: <same fields>.
- ...

## Crowd / extras

- <describe the crowd's collective character: e.g., "village children, mixed skin tones, simple cotton clothes, ages 6–10">.

## Consistency notes

- All character heights are consistent across shots: <character X> is taller than <character Y> by ~1 head.
- Lighting on faces is soft, three-quarter front-lit.
- No reflective sunglasses (Nano Banana 2 tends to embed weird reflections).
```

## Rules

1. **Concrete, visual nouns only.** "Confident" is not visual. "Hands on hips, chin up" is.
2. **Locked palette** — once a color is named for hair/outfit, never restate it differently elsewhere.
3. **Limit to 6 named features per character.** More invites drift.
4. **End every entry with a comma-separated tag list** so the generator can fall back on tags if it misreads the prose.
