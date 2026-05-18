# Developing on `edustack-video`

A short, opinionated guide for the people (and Claudes) who edit this repo.

## Local dev loop

This plugin doesn't have a traditional "run the app" flow. Two things you can do locally:

### 1. Run the brief-collector server standalone

```bash
node skills/brief-collector/server/server.mjs --run-dir /tmp/edustack-test
```

Opens `http://127.0.0.1:<random>/`. Submitting writes `/tmp/edustack-test/brief.json` and exits. Fast feedback loop for the form HTML/CSS/JS.

### 2. Run the VPS observability service standalone

```bash
cd vps && docker compose up --build
# Then probe:
curl http://localhost/healthz                              # via Caddy (TLS will fail on localhost — that's fine)
curl http://localhost:8000/healthz                         # direct to FastAPI in the app container
```

For real deploy: `ssh root@157.173.222.220`, rsync `vps/` to `/opt/eduplugin/`, then `docker compose up -d --build`.

## Install the plugin locally for end-to-end testing

Inside a Claude Code session (the install is slash-command only — `claude plugin add` isn't a real CLI):

```text
/plugin marketplace add ~/Documents/GitHub/edustack-video
/plugin install edustack-video@edustack-video
/reload-plugins

/create-video-setup
/test-logs
/create-video
```

The local-path marketplace picks up your live edits — useful for iterating on a SKILL.md or phase script and seeing the effect immediately. After non-trivial changes, run `/reload-plugins` again.

## Editing skills

A skill's behavior is its SKILL.md. When you change one:

1. Keep the description short and trigger-focused. Test by asking Claude in a new window "what skill should I use to X?" — if it doesn't pick yours, the description needs work.
2. Use `@references/<file>.md` to link supporting docs — Claude loads them on demand (progressive disclosure).
3. Embed a TodoWrite checklist for any multi-step skill — the orchestrator does this for each gate.
4. Run the `plugin-dev:skill-reviewer` agent on the updated SKILL.md for a structured pass.

## Editing the Python lib

```bash
cd /tmp/edustack-test && uv venv .venv && uv pip sync ~/Documents/GitHub/edustack-video/requirements.txt
.venv/bin/python -c "from scripts.lib.config import load; print(load('/tmp/edustack-test'))"
```

`scripts/lib/_api-errors.md` (ported from edu-vid-gen-cloud) has the retry/backoff vocabulary we want for `fal_client.py` and `elevenlabs_client.py` when they grow past stubs.

## Editing the VPS

The FastAPI app is a single `main.py` by design — easy to read in one sitting. JSONL on disk; new streams = new directories under `/var/lib/eduplugin/<date>/<stream>/`. If you need indexed queries, switch the storage layer in one function (`_collect`) — the wire format stays the same.

## Releasing

1. Bump `plugin.json.version`.
2. Append to `CHANGELOG.md` under `[Unreleased]`; rename the section to the new version.
3. Commit + push to `main`. End users get the change on next `/plugin-update`.

For breaking changes (file layout, brief schema), bump the minor version and write a migration note in `CHANGELOG.md`.

## Common gotchas

- **`brief.aspect` and image sizes are coupled.** Don't hardcode 1920×1080 in a phase script — read `models.yaml.aspect_sizes[brief.aspect]`.
- **`vo_timeline.json` is the timing canon.** Don't compute durations from `brief.duration_seconds` after Phase 2.
- **The hook is non-blocking.** Anything in `hooks/ship-chat.sh` that could hang must be backgrounded (`&`). The hook's `timeout: 10` in `plugin.json` is a safety net, not a budget.
- **VPS calls swallow exceptions.** Don't depend on the VPS for control flow. If you need a thing to fail loudly, raise locally.
- **Frontmatter typos kill skills silently.** Run `plugin-dev:plugin-validator` after editing SKILL.md frontmatter.
