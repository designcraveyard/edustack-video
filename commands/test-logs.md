---
description: Self-test the Supabase observability pipeline. Emits one synthetic event per stream (logs, prompts, analyses, gates, heartbeat, chat) + exercises the chat hook end-to-end, then SELECTs each row back to prove it landed.
---

# /test-logs

Run after `/create-video-setup` (or any time you suspect telemetry has drifted) to confirm:

1. The Supabase `eduplugin_events` table is reachable from this machine with the configured anon key.
2. All six event streams (`logs`, `prompts`, `analyses`, `gates`, `heartbeat`, `chat`) round-trip — POST then SELECT.
3. The PostToolUse / Stop hook (`hooks/ship-chat.sh`) ships chat transcripts correctly. Tested by piping a synthetic Claude Code hook payload into the script and verifying the resulting `stream=chat` row appears in Supabase.

## What this command does (step by step)

You are the runner for an observability self-test. Walk through these steps in order — do not skip the verification because "the test passed last week".

1. **Confirm setup is complete.** Read `<output>/.config/`. If `supabase.anon` or `user_id` is missing, instruct the user to run `/create-video-setup` first. Do not proceed.
2. **Invoke the test script.** Run:

   ```bash
   cd <output> && uv run --python <output>/.venv/bin/python python -m scripts.test_logs --output <output>
   ```

   (If `uv` is not on PATH, fall back to `<output>/.venv/bin/python -m scripts.test_logs --output <output>`.)

3. **Surface the result to the user.** Stream stdout to chat verbatim — the script's per-stream PASS/FAIL table is the answer. Do not summarise it away.

4. **On failure, explain the most likely cause** based on what the script printed:
   - `GET 401` / `GET 403` → anon key is wrong or rotated. Re-run `/create-video-setup`.
   - `GET 400` with "column does not exist" → table schema drift. The expected columns are `id, ts, user_id, run_id, stream, phase, payload`. Everything event-specific lives inside `payload` (jsonb). Compare against the [setup skill](../skills/setup/SKILL.md) example payload.
   - "no row + no fallback" → the POST silently failed. Check network, then re-run with verbose logging by exporting `HTTPX_LOG_LEVEL=debug` and re-running the bash command above.
   - "hook returned cleanly … no row" → the hook ran but Supabase rejected the chat row. Check `<output>/runs/test-logs-hook-*/logs/local.jsonl` for the fallback line — it will contain the HTTP status the hook saw.

5. **On success, share the discovery URLs.** The script prints:
   - The Supabase project URL with the filter shown (user_id + run_id) so the user can verify rows visually.
   - The EduStack admin viewer URL (when deployed) for the same run id.

## What this command does NOT do

- Does **not** spend any fal.ai or ElevenLabs credit. Every prompt/analysis row is synthetic.
- Does **not** create or modify any real video run. The hook test creates a temporary `test-logs-hook-*` run directory and deletes it on exit.
- Does **not** clean up the synthetic Supabase rows. They're namespaced by `user_id` + `run_id` and the payloads are marked `test_marker: true` so analytics queries can filter them out trivially.

## When this command is useful

- **Right after `/create-video-setup`** — verify the wiring before the user spends fal credit on a real run.
- **After installing on a new client machine** — confirms the anon key + network path before handing off.
- **After bumping plugin or Supabase schema** — proves the new event shape still round-trips.
- **When debugging "why aren't my chats showing up"** — narrows the failure down to setup / network / hook / table / RLS.

## Reference

- Script: [`scripts/test_logs.py`](../scripts/test_logs.py)
- Hook tested: [`hooks/ship-chat.sh`](../hooks/ship-chat.sh)
- Setup skill (Supabase config + table shape): [`skills/setup/SKILL.md`](../skills/setup/SKILL.md)
- Sink implementation: [`scripts/lib/supabase_sink.py`](../scripts/lib/supabase_sink.py)
