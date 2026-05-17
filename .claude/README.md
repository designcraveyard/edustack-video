# `.claude/` — repo-local Claude Code config

Auto-loaded by Claude Code when a session opens with this repo as the working directory. Checked into git so every maintainer (and every Claude) gets the same setup.

## Files

| File | Purpose |
|---|---|
| `settings.json` | Hook registration. PostToolUse marks plugin edits, Stop blocks until docs are reviewed. |
| `hooks/track-plugin-edits.py` | PostToolUse hook on `Write\|Edit`. Records edited plugin paths in `.docs-stale`. |
| `hooks/check-docs-stale.py` | Stop hook. If `.docs-stale` is non-empty (and we're not already looping), returns `decision: block` so Claude updates docs before finishing. |
| `.docs-stale` | Runtime marker (gitignored). Line-per-path list of edited plugin sources awaiting doc review. |

## How the doc-freshness loop works

```
You edit skills/orchestrator/SKILL.md
        │
        ▼
PostToolUse fires → track-plugin-edits.py
        │
        ▼
appends "skills/orchestrator/SKILL.md" to .claude/.docs-stale
        │
   …more edits…
        │
        ▼
Claude tries to Stop
        │
        ▼
Stop hook fires → check-docs-stale.py
        │
        ▼
Marker non-empty → emits {"decision":"block","reason":"…paths…update CLAUDE.md/docs/…rm marker"}
        │
        ▼
Claude reads, reviews + updates docs, then `rm .claude/.docs-stale`
        │
        ▼
Claude tries to Stop again
        │
        ▼
Marker absent → Stop hook exits 0 → session ends cleanly
```

The Stop hook checks `stop_hook_active` in its input — if Claude is already running because of a prior Stop block, the hook returns silently so we never infinite-loop.

## What counts as a "plugin source file"

PostToolUse tracks edits inside:
- `plugin.json`, `package.json`, `requirements.txt`
- `commands/**`
- `skills/**`
- `scripts/**`
- `hooks/**`
- `vps/**`
- `seed/**`

It **ignores** edits to docs themselves (CLAUDE.md, README.md, CHANGELOG.md, `docs/**`, `.claude/**`) so the marker can't be triggered by doc updates.

## Disabling temporarily

If you genuinely need to stop the loop (e.g. running a one-off migration script that touches plugin files but doesn't deserve a doc update):

```bash
rm .claude/.docs-stale   # clears any pending review
```

…or comment out the relevant hook block in `settings.json` (don't commit that — it's a local workaround, not a default).
