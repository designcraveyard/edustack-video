#!/usr/bin/env python3
"""PostToolUse hook: when a plugin source file is written/edited, record its
relative path in .claude/.docs-stale so the Stop hook can ask Claude to
update CLAUDE.md / docs before finishing.

Silent on every code path. Exits 0 unconditionally.
"""
from __future__ import annotations
import fnmatch
import json
import os
import sys


def main() -> int:
    try:
        hook = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = hook.get("tool_input") or {}
    fp = tool_input.get("file_path") or ""
    if not fp:
        return 0

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        rel = os.path.relpath(fp, root)
    except Exception:
        return 0
    if rel.startswith(".."):
        return 0  # edit outside repo — ignore

    # Skip docs themselves, .claude internals, and noise.
    skip = [
        "CLAUDE.md", "README.md", "CHANGELOG.md", ".gitignore", ".gitattributes",
        "docs/*", "docs/**/*",
        ".claude/*", ".claude/**/*",
        "*.lock", "*.log",
    ]
    if any(fnmatch.fnmatch(rel, pat) for pat in skip):
        return 0
    # Glob recursion: fnmatch doesn't do ** — also check prefix.
    if rel.startswith(("docs/", ".claude/")):
        return 0

    # Track edits inside these areas.
    watch_prefixes = ("commands/", "skills/", "scripts/", "hooks/", "vps/", "seed/")
    watch_files = {"plugin.json", "package.json", "requirements.txt"}
    tracked = rel.startswith(watch_prefixes) or rel in watch_files
    if not tracked:
        return 0

    marker = os.path.join(root, ".claude", ".docs-stale")
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    with open(marker, "a", encoding="utf-8") as f:
        f.write(rel + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
