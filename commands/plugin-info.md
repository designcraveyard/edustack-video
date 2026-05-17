---
description: Show current edustack-video version, commits behind origin/main, and recent changelog.
---

# /plugin-info

`cd $CLAUDE_PLUGIN_ROOT`. Print:

```
Plugin:    edustack-video
Path:      $CLAUDE_PLUGIN_ROOT
Remote:    $(git remote get-url origin)
Branch:    $(git rev-parse --abbrev-ref HEAD)
SHA:       $(git rev-parse --short HEAD) ($N commits behind origin/main)
Updated:   $(git log -1 --format=%ci HEAD)
Changelog (recent):
  $(git log -5 --oneline)
```

Do `git fetch origin main --quiet` first so the "commits behind" count is fresh.
