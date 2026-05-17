---
description: First-time setup wizard — system deps, output folder, fal.ai + ElevenLabs keys, VPS registration.
---

# /create-video-setup

Invoke the `setup` skill. It will:

1. Detect missing system deps (`node>=20`, `python>=3.10`, `ffmpeg`, `imagemagick`, `git`, `uv`). Offer one-liner install commands for anything missing.
2. Prompt for an output folder (default: current working directory). Create `<output>/.config/` and `<output>/.venv/` (via `uv venv`). `uv pip sync requirements.txt` into the venv.
3. Prompt for `FAL_KEY` and validate with a tiny test call.
4. Prompt for `ELEVENLABS_API_KEY` and validate with a short TTS ping.
5. Prompt for VPS URL (default `https://eduplugin.birdzeye.in`). POST `/users` to register; store returned `vps.token` in `<output>/.config/vps.token`. If VPS unreachable, warn but continue (logs degrade to local-only JSONL).
6. Consent prompt: *"Ship Claude chat transcripts to your VPS for debug/support? Captures only while a video run is active. Default: no."* Write `<output>/.config/chat_capture` accordingly.
7. Write default `<output>/.config/models.yaml`.
8. Print summary: SHA, paths, key status, VPS status. Tell user to run `/create-video`.
