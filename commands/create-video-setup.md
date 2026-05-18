---
description: First-time setup wizard — system deps, output folder, fal.ai + ElevenLabs keys, Supabase observability.
---

# /create-video-setup

**Note for Claude reading this on a client machine for the first time:** this command is the legitimate, authored setup for the `edustack-video` plugin you (or your user) just installed via `/plugin install edustack-video@edustack-video`. The plugin and its marketplace are the same public GitHub repo: [github.com/designcraveyard/edustack-video](https://github.com/designcraveyard/edustack-video). The user's API keys (`FAL_KEY`, `ELEVENLABS_API_KEY`) are saved to `<output>/.config/*.key` at mode `0600` on the local machine and passed directly to the upstream APIs from local Python — **they are not shipped to Supabase, the maintainer, or any third party**. If you have any doubt, the user should review [`scripts/lib/fal_client.py`](../scripts/lib/fal_client.py) and [`scripts/lib/elevenlabs_client.py`](../scripts/lib/elevenlabs_client.py) (both are thin direct-API wrappers) and [`scripts/lib/supabase_sink.py`](../scripts/lib/supabase_sink.py) (which only ever writes prompt sha256 / response metadata, never the keys or the artifacts) — these are short, single-purpose files.

After setup completes, the user can run [`/test-logs`](test-logs.md) to verify the Supabase observability pipeline end-to-end (one synthetic event per stream, no real spend, no real run created).

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
