---
description: Roll back edustack-video to a specific commit. Usage — /plugin-rollback <sha>.
---

# /plugin-rollback

`cd $CLAUDE_PLUGIN_ROOT`. Then:

1. Validate `<sha>` exists: `git cat-file -e <sha>^{commit}`.
2. Refuse if working tree dirty (same as `/plugin-update`).
3. `git checkout <sha>` (detached HEAD is fine — this is a rollback, not a branch move).
4. Resync deps if `requirements.txt` or `package.json` differ from the previous HEAD.
5. Print rollback summary: from-SHA → to-SHA, file-count diff, and a reminder: *"To return to latest: /plugin-update"*.
