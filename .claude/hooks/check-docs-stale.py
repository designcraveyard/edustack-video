#!/usr/bin/env python3
"""Stop hook: if any plugin source file was modified this session, block
Stop and ask Claude to review + update relevant docs first.

The PostToolUse hook (track-plugin-edits.py) populates .claude/.docs-stale.
This hook reads it, emits a structured `block` decision, and trusts Claude
to delete the marker once docs are up to date.

Loop guard: if Claude is already running because of a previous Stop block
(`stop_hook_active=true` in the hook payload), this hook stays silent —
otherwise it could trap forever.
"""
from __future__ import annotations
import json
import os
import sys


def main() -> int:
    try:
        hook = json.load(sys.stdin)
    except Exception:
        hook = {}

    if hook.get("stop_hook_active"):
        return 0  # Already in a Stop-driven re-run. Don't loop.

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    marker = os.path.join(root, ".claude", ".docs-stale")
    if not os.path.isfile(marker) or os.path.getsize(marker) == 0:
        return 0

    with open(marker, encoding="utf-8") as f:
        paths = sorted({line.strip() for line in f if line.strip()})
    if not paths:
        return 0

    bullet_paths = "\n  ".join(paths)
    reason = (
        "Plugin source files were modified this session. Before finishing, "
        "review the changes and update relevant documentation if needed.\n\n"
        f"Files changed ({len(paths)}):\n  {bullet_paths}\n\n"
        "Check & update as appropriate:\n"
        "  - CLAUDE.md (cross-file invariants, locked decisions, where-things-live)\n"
        "  - docs/architecture.md (phases, persistence layers, gate UX, trust boundaries)\n"
        "  - docs/developing.md (dev loop, release flow, gotchas)\n"
        "  - README.md (only for user-facing changes)\n"
        "  - CHANGELOG.md (add entry under [Unreleased])\n\n"
        "When the docs are up to date — or you've determined no doc update is needed for these "
        "changes — clear the marker so Stop can complete next time:\n"
        f"  rm {marker}\n\n"
        "If you genuinely don't need to update any docs, still rm the marker (with a one-line "
        "note in the commit body explaining why).\n\n"
        "This message is from .claude/hooks/check-docs-stale.py."
    )

    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
