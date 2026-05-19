---
name: setup
description: Use when running /create-video-setup for the first time on a machine. Detects system deps, prompts for fal.ai and ElevenLabs keys, picks an output folder, wires the Supabase observability sink, and writes <output>/.config/.
---

# Setup

Idempotent: safe to run multiple times. Already-set values are pre-filled and the user can press enter to keep them.

## Checklist (TodoWrite)

1. **System deps** — check `node -v` (≥20), `python3 -V` (≥3.10), `ffmpeg -version`, `convert -version` (imagemagick), `git --version`, `uv --version`. For each missing, offer a one-liner:
   - macOS: `brew install <pkg>`
   - Linux: `sudo apt install <pkg>` (or `curl -LsSf https://astral.sh/uv/install.sh | sh` for `uv`).
   - **ffmpeg note**: only required if you plan to use ffmpeg's `subtitles` filter elsewhere — our karaoke burn-in uses MoviePy + Pillow and works with any ffmpeg build.
2. **Output folder** — prompt; default to `$PWD`. Create `<output>/.config/` and `<output>/runs/`.
3. **Python venv** — `uv venv <output>/.venv` then `uv pip sync --python <output>/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/requirements.txt`.
4. **fal.ai key** — prompt for `FAL_KEY`. Validate by calling `fal-ai/any-llm` with a tiny `prompt`. Save to `<output>/.config/fal.key` (mode 0600).
5. **ElevenLabs key** — prompt for `ELEVENLABS_API_KEY`. Validate with `GET /v1/user`. Save to `<output>/.config/elevenlabs.key` (mode 0600).
6. **Observability sink (Supabase)** — there is exactly **one** table: `public.eduplugin_events`. The names `logs`, `prompts`, `analyses`, `gates`, `heartbeat`, `chat` are **values of the `stream` column**, NOT separate tables or REST endpoints. If you see a hallucinated warning like "the /prompts table doesn't exist", ignore it — only `eduplugin_events` is needed. Defaults to the Edustack shared project. Prompt with the default URL `https://ulyzimrayfzhbltpxbaj.supabase.co` (`NEXT_PUBLIC_SUPABASE_URL`) and prompt for the **anon key** (`NEXT_PUBLIC_SUPABASE_ANON_KEY`, public-by-design — same one shipped in the Edustack web bundle). Write `<output>/.config/supabase.url` and `<output>/.config/supabase.anon`. Validate with **one** test write — the payload MUST match the live schema, otherwise you'll see a `column does not exist` 400 and falsely conclude the table is wrong:

   ```bash
   curl -s -X POST "$SUPABASE_URL/rest/v1/eduplugin_events" \
     -H "apikey: $SUPABASE_ANON" \
     -H "Authorization: Bearer $SUPABASE_ANON" \
     -H "Content-Type: application/json" \
     -H "Prefer: return=minimal" \
     -d '{
       "user_id": "'"$USER_ID"'",
       "run_id":  "setup-validate",
       "stream":  "logs",
       "phase":   "setup",
       "payload": {"level": "info", "msg": "setup validate"}
     }'
   ```

   The table columns are exactly `id, ts, user_id, run_id, stream, phase, payload`. Everything event-specific (`level`, `msg`, `kind`, `endpoint`, `decision`, `comment`, …) goes **inside the `payload` jsonb**, never as top-level columns. `stream` must be one of `logs|prompts|analyses|gates|heartbeat|chat`.

   On HTTP 2xx: report success. On 401/403: report bad anon key. On 400 with `column X does not exist`: this is a payload-shape bug — re-check the curl above. On anything else: log it and let setup continue (the runtime sink falls back to local JSONL).
7. **User id** — automatically generated and saved to `<output>/.config/user_id` if missing (one uuid per plugin install; namespaces events in the table).
8. **Chat-capture consent** — prompt: *"Ship Claude chat transcripts to Supabase for debug/support? Captures only while a video run is active. Default: no."* Write `on` or `off` to `<output>/.config/chat_capture`.
9. **Models config** — copy `${CLAUDE_PLUGIN_ROOT}/seed/models.yaml` to `<output>/.config/models.yaml` if absent. NOTE: setup never overwrites an existing `.config/models.yaml`, so seed updates don't reach existing installs. The vo `model_id` is force-overridden to `eleven_v3` at runtime by `phase_vo.py` regardless — audio tags require v3 and older models speak them literally. For other stale-config issues, suggest the user `rm <output>/.config/models.yaml` and re-run setup to pick up the fresh seed.
10. **Print summary** — paths, key validation status, Supabase status (rows visible in https://[edustack web]/admin/eduplugin/runs), plugin SHA, next step (`/create-video`).

## References

- @references/system-requirements.md — install commands per OS, version matrix.
