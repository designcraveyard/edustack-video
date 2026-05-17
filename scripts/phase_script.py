"""Phase 1 — Script writing. STUB: orchestrator/skill is expected to drive Claude; this script is a thin entrypoint for headless/CI use."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import sys
from scripts.lib.config import load
from scripts.lib.run_state import RunState
from scripts.lib.vps_logger import VPSLogger


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    cfg = load(run_dir.parent.parent)
    state = RunState.load_or_init(run_dir)
    log = VPSLogger(cfg.vps_url, cfg.vps_token, run_dir)
    log.heartbeat(state.run_id, "script", "started")

    brief = json.loads((run_dir / "brief.json").read_text())
    mode = brief.get("script_mode", "standard")

    # The actual script-writing happens inside Claude (via the script-writer skill).
    # This entrypoint exists for /create-video-resume bookkeeping + future headless mode.
    log.log(state.run_id, "script", "info", f"phase_script entrypoint hit (mode={mode})")
    print(f"[script] mode={mode} run_dir={run_dir}", file=sys.stderr)
    print("[script] NOTE: invoke the script-writer skill from Claude to generate script.md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
