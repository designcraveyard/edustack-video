"""Phase entrypoint for vo. STUB — to be filled in next session."""
from __future__ import annotations
import argparse
from pathlib import Path
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
    log.heartbeat(state.run_id, "vo", "started")
    print("[vo] stub — implement me", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
