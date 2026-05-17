---
description: First-time setup wizard — system deps, output folder, fal.ai + ElevenLabs keys, Supabase observability.
---

# /create-video-setup

Invoke the `setup` skill. It will:

1. Detect missing system deps (`node>=20`, `python>=3.10`, `ffmpeg`, `imagemagick`, `git`, `uv`). Offer one-liner install commands for anything missing.
2. Prompt for an output folder (default: current working directory). Create `<output>/.config/` and `<output>/.venv/` (via `uv venv`). `uv pip sync requirements.txt` into the venv.
3. Prompt for `FAL_KEY` and validate with a tiny `fal-ai/any-llm` call.
4. Prompt for `ELEVENLABS_API_KEY` and validate with `GET /v1/user` (no TTS spend).
5. **Observability — Supabase**:
   - Default URL: `https://ulyzimrayfzhbltpxbaj.supabase.co` (Edustack project).
   - Prompt for the anon key (`NEXT_PUBLIC_SUPABASE_ANON_KEY` — same public key the Edustack web bundle ships).
   - Validate with one test write to `eduplugin_events`.
   - Save to `<output>/.config/supabase.url` and `<output>/.config/supabase.anon`.
   - Generate `<output>/.config/user_id` (UUID) if absent.
   - If the validate-write fails, warn but continue — the sink falls back to `<run-dir>/logs/local.jsonl`.
6. Consent prompt: *"Ship Claude chat transcripts to Supabase for debug/support? Captures only while a video run is active. Default: no."* Write `<output>/.config/chat_capture`.
7. Copy default `<output>/.config/models.yaml` if absent.
8. Print summary: SHA, paths, key validation status, Supabase status, debug viewer URL (`<edustack-web-root>/admin/eduplugin/runs/<your-user-id>`). Tell the user to run `/create-video`.
