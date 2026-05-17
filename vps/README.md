# eduplugin VPS (`eduplugin.birdzeye.in`)

FastAPI observability sink. Receives logs, prompts, analyses, gate decisions, heartbeats, and (opt-in) chat transcripts from edustack-video plugin instances.

## Stack
- FastAPI + uvicorn (single container)
- Caddy (auto-TLS via Let's Encrypt)
- JSONL on disk, partitioned by date + stream
- Bearer-token auth (per-user, generated at `/create-video-setup`)

## Deploy

```bash
ssh root@157.173.222.220  # or use srv749816.hstgr.cloud
mkdir -p /opt/eduplugin && cd /opt/eduplugin
# Clone or rsync this vps/ subtree here.
docker compose pull
docker compose up -d --build
docker compose logs -f --tail=50
```

DNS prerequisite: `eduplugin.birdzeye.in` A record → `157.173.222.220` (created via Hostinger MCP or panel).

## Endpoints
See `app/main.py`. All write endpoints are auth-gated; bearer tokens are minted by `POST /users` (currently anonymous; lock down in a future iteration).

## Retention
JSONL files live under `/var/lib/eduplugin/<yyyy-mm-dd>/<stream>/<run_id>.jsonl`. A cron purge for files older than 30 days is **not yet wired** — add a system cron entry on the host:

```
0 3 * * * find /var/lib/eduplugin -type f -mtime +30 -delete
```

## Status
Scaffold complete. **Not yet deployed** — deferred to a follow-up session per the scaffold-only scope decision.
