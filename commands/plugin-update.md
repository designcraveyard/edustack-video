---
description: Pull latest edustack-video from main, sync deps (uv pip sync + npm ci), print changelog. Equivalent to /plugin marketplace update edustack-video but ALSO syncs Python and Node deps when requirements files change.
---

# /plugin-update

**Equivalent native command:** `/plugin marketplace update edustack-video` then `/reload-plugins`. This `/plugin-update` does the same `git pull` under the hood and additionally:

- Refuses to update while a video run is in flight (so you don't pull a code change mid-run).
- Refuses to update when the working tree is dirty (handles `--force` with a `git stash` fallback).
- Syncs `requirements.txt` (via `uv pip sync`) and `package.json` (via `npm ci`) if either changed since the previous SHA. The native command doesn't do this — if you used it, run `uv pip sync requirements.txt` and `npm ci` yourself.

Walkthrough:

`cd $CLAUDE_PLUGIN_ROOT`. Then:

1. **Refuse** if any run is in flight — scan `<output>/runs/*/run.json` for `status != complete`. Show paths and exit code 20.
2. **Refuse** if working tree dirty (`git status --porcelain`). Show dirty paths and exit 20. If user passes `--force`, `git stash push -u -m "plugin-update-$(date +%s)"` first.
3. `git fetch origin main` (no apply yet).
4. `git log HEAD..origin/main --oneline` + `git diff --stat HEAD..origin/main`. Show user.
5. Print the diff slice of `CHANGELOG.md` between local and remote HEAD.
6. `git merge --ff-only origin/main`. If conflicts, abort and point user to manual reconciliation.
7. If `requirements.txt` changed since old SHA → `uv pip sync requirements.txt` in `<output>/.venv`.
8. If `package.json` changed → `npm ci`.
9. Print new SHA + one-line commit summary. Exit code: 0 updated, 10 already current.
