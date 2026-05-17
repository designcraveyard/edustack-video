---
description: Resume an interrupted video run from the last completed gate.
---

# /create-video-resume

Invoke the `orchestrator` skill in resume mode.

1. Scan `<output>/runs/*/run.json` for runs with `status != complete`.
2. If multiple, list them and ask user to pick.
3. Open `run.json`, find the last completed phase + gate decision.
4. Resume from the next phase. Do not re-run completed phases.
5. If a phase was mid-flight (status `running`), restart only the items that didn't finish (consult `run.json`'s per-item progress list).
