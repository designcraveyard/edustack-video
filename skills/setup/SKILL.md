---
name: setup
description: Use when running /create-video-setup for the first time on a machine. Detects system deps, prompts for fal.ai and ElevenLabs keys, picks an output folder, registers with the VPS, and writes <output>/.config/.
---

# Setup

Idempotent: safe to run multiple times. Already-set values are pre-filled and the user can press enter to keep them.

## Checklist (TodoWrite)

1. **System deps** — check `node -v` (≥20), `python3 -V` (≥3.10), `ffmpeg -version`, `convert -version` (imagemagick), `git --version`, `uv --version`. For each missing, offer one-liner:
   - macOS: `brew install <pkg>`
   - Linux: `sudo apt install <pkg>` (or note `uv` install via `curl -LsSf https://astral.sh/uv/install.sh | sh`).
2. **Output folder** — prompt; default to `$PWD`. Create `<output>/.config/` and `<output>/runs/`.
3. **Python venv** — `uv venv <output>/.venv` then `uv pip sync --python <output>/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/requirements.txt`.
4. **fal.ai key** — prompt for `FAL_KEY`. Validate by calling `fal-ai/any-llm` with a 1-token request. Save to `<output>/.config/fal.key` (mode 0600).
5. **ElevenLabs key** — prompt for `ELEVENLABS_API_KEY`. Validate with `GET /v1/user` (cheap, no TTS spend). Save to `<output>/.config/elevenlabs.key` (mode 0600).
6. **VPS URL** — prompt with default `https://eduplugin.birdzeye.in`. `POST /users` (anonymous registration). Persist returned token to `<output>/.config/vps.token` (mode 0600). If `/healthz` fails, warn user and continue (local-only mode).
7. **Chat-capture consent** — prompt: *"Ship Claude chat transcripts to your VPS for debug/support? Captures only while a video run is active. Default: no."* Write `on` or `off` to `<output>/.config/chat_capture`.
8. **Models config** — copy `${CLAUDE_PLUGIN_ROOT}/seed/models.yaml` to `<output>/.config/models.yaml` if absent.
9. **Print summary** — paths, key validation status, VPS status, plugin SHA, next step (`/create-video`).

## References

- @references/system-requirements.md — install commands per OS, version matrix.
