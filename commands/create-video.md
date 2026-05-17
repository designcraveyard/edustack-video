---
description: Start a new educational video run. Walks through 5 phases with 4 chat-driven review gates.
---

# /create-video

You are the orchestrator for an educational-video generation run.

**Invoke the `orchestrator` skill immediately.** It will:

1. Check that `/create-video-setup` has been completed (`<output>/.config/` exists). If not, instruct the user to run it.
2. Determine the run directory under `<output>/runs/<yyyy-mm-dd>-<slug>-NN/`.
3. If `brief.json` is missing, invoke the `brief-collector` skill (spins up a localhost form).
4. Walk the 5-phase pipeline (script → vo → characters → storyboard → clips → stitch), invoking the per-phase skill at each step.
5. At each gate, list artifact file paths in chat and wait for user reply (`approve` / `regen ...`).
6. Write all gate decisions and comments to `<run-dir>/run.json` and ship to VPS `/gates`.

Do **not** start running phases without first reading `skills/orchestrator/SKILL.md`.
