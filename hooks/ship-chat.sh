#!/usr/bin/env bash
# PostToolUse + Stop hook: ships a delta of the Claude Code chat transcript to the user's VPS.
# Opt-in via <output>/.config/chat_capture. Never blocks the agent loop (POST runs in the background).
set -euo pipefail

# Read stdin JSON (Claude Code hook contract).
HOOK_JSON="$(cat || true)"
[ -z "$HOOK_JSON" ] && exit 0

python3 - "$HOOK_JSON" <<'PY' &
import json, os, subprocess, sys
from pathlib import Path

hook = json.loads(sys.argv[1])
transcript_path = hook.get("transcript_path")
session_id      = hook.get("session_id") or ""
cwd             = hook.get("cwd") or os.getcwd()

if not transcript_path or not Path(transcript_path).exists():
    sys.exit(0)

# Find the output root by walking up from cwd looking for .config/chat_capture.
def find_output_root(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(8):
        if (cur / ".config" / "chat_capture").exists():
            return cur
        if cur.parent == cur: break
        cur = cur.parent
    return None

root = find_output_root(Path(cwd))
if not root: sys.exit(0)

if (root / ".config" / "chat_capture").read_text().strip() != "on":
    sys.exit(0)

# Find active run.
active = None
for rj in (root / "runs").glob("*/run.json") if (root / "runs").exists() else []:
    try:
        d = json.loads(rj.read_text())
        if d.get("status") != "complete":
            active = rj.parent; break
    except Exception:
        pass
if not active:
    sys.exit(0)

run_id = active.name
offset_p = active / ".last_chat_offset"
offset = int(offset_p.read_text().strip()) if offset_p.exists() else 0
size = Path(transcript_path).stat().st_size
if size <= offset:
    sys.exit(0)

delta_file = active / f".chat_delta_{session_id}_{size}.jsonl"
with Path(transcript_path).open("rb") as src, delta_file.open("wb") as dst:
    src.seek(offset)
    dst.write(src.read())

vps_url   = (root / ".config" / "vps.url").read_text().strip() if (root / ".config" / "vps.url").exists() else None
vps_token = (root / ".config" / "vps.token").read_text().strip() if (root / ".config" / "vps.token").exists() else None
if not vps_url or not vps_token:
    sys.exit(0)

# Read delta lines into a JSON payload (whole-file POST keeps the server simple).
delta_lines = []
for line in delta_file.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip():
        try: delta_lines.append(json.loads(line))
        except Exception: pass

import urllib.request
payload = json.dumps({"run_id": run_id, "session_id": session_id, "delta": delta_lines}).encode()
req = urllib.request.Request(
    f"{vps_url.rstrip('/')}/chat-transcripts",
    data=payload,
    headers={"Authorization": f"Bearer {vps_token}", "Content-Type": "application/json"},
    method="POST",
)
try:
    urllib.request.urlopen(req, timeout=5)
    offset_p.write_text(str(size))
except Exception:
    pass
finally:
    try: delta_file.unlink()
    except Exception: pass
PY

exit 0
