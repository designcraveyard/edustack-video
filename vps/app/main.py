"""eduplugin observability sink. JSONL on disk, partitioned by date and stream."""
from __future__ import annotations
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, UTC
from typing import Any
import hashlib
import json
import os
import secrets

DATA_DIR = Path(os.environ.get("EDUPLUGIN_DATA_DIR", "/var/lib/eduplugin"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_FILE = DATA_DIR / "users.jsonl"

app = FastAPI(title="eduplugin observability", version="0.1.0")


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _stream_path(stream: str, run_id: str) -> Path:
    p = DATA_DIR / _today() / stream
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{run_id}.jsonl"


def _append(stream: str, run_id: str, payload: dict) -> None:
    payload.setdefault("ts", datetime.now(UTC).isoformat())
    _stream_path(stream, run_id).open("a").write(json.dumps(payload, default=str) + "\n")


def _load_users() -> dict[str, dict]:
    if not USERS_FILE.exists():
        return {}
    users: dict[str, dict] = {}
    for line in USERS_FILE.read_text().splitlines():
        if line.strip():
            u = json.loads(line)
            users[u["token_hash"]] = u
    return users


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _require_auth(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer")
    token = authorization.removeprefix("Bearer ").strip()
    users = _load_users()
    user = users.get(_hash(token))
    if not user:
        raise HTTPException(401, "invalid token")
    return user


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "ts": datetime.now(UTC).isoformat()}


@app.post("/users")
def create_user() -> dict:
    token = secrets.token_urlsafe(32)
    rec = {"token_hash": _hash(token), "created_at": datetime.now(UTC).isoformat()}
    USERS_FILE.open("a").write(json.dumps(rec) + "\n")
    return {"token": token}


class LogIn(BaseModel):
    run_id: str
    phase: str
    level: str
    msg: str
    ts: str | None = None


@app.post("/logs")
def post_log(body: LogIn, authorization: str | None = Header(default=None)) -> dict:
    _require_auth(authorization)
    _append("logs", body.run_id, body.model_dump())
    return {"ok": True}


class PromptIn(BaseModel):
    run_id: str
    phase: str
    kind: str
    endpoint: str
    prompt: str
    response_meta: dict | None = None
    latency_ms: int = 0
    status: str = "ok"
    cost_cents: float = 0.0
    ts: str | None = None


@app.post("/prompts")
def post_prompt(body: PromptIn, authorization: str | None = Header(default=None)) -> dict:
    _require_auth(authorization)
    _append("prompts", body.run_id, body.model_dump())
    return {"ok": True}


class AnalysisIn(BaseModel):
    run_id: str
    target: str
    target_id: str
    analysis_json: dict
    ts: str | None = None


@app.post("/analyses")
def post_analysis(body: AnalysisIn, authorization: str | None = Header(default=None)) -> dict:
    _require_auth(authorization)
    _append("analyses", body.run_id, body.model_dump())
    return {"ok": True}


class GateIn(BaseModel):
    run_id: str
    gate: str
    decision: str
    item_ref: str
    comment: str = ""
    ts: str | None = None


@app.post("/gates")
def post_gate(body: GateIn, authorization: str | None = Header(default=None)) -> dict:
    _require_auth(authorization)
    _append("gates", body.run_id, body.model_dump())
    return {"ok": True}


class HeartbeatIn(BaseModel):
    run_id: str
    phase: str
    status: str
    ts: str | None = None


@app.post("/heartbeat")
def post_heartbeat(body: HeartbeatIn, authorization: str | None = Header(default=None)) -> dict:
    _require_auth(authorization)
    _append("heartbeat", body.run_id, body.model_dump())
    return {"ok": True}


@app.post("/chat-transcripts")
async def post_chat(req: Request, authorization: str | None = Header(default=None)) -> dict:
    _require_auth(authorization)
    body = await req.json()
    run_id = body.get("run_id") or "unknown"
    _append("chat", run_id, body)
    return {"ok": True}


def _collect(run_id: str) -> list[dict]:
    rows: list[dict] = []
    for day_dir in sorted(DATA_DIR.iterdir()):
        if not day_dir.is_dir() or day_dir.name in {"users"}:
            continue
        for stream_dir in day_dir.iterdir():
            f = stream_dir / f"{run_id}.jsonl"
            if f.exists():
                for line in f.read_text().splitlines():
                    if line.strip():
                        d = json.loads(line)
                        d["_stream"] = stream_dir.name
                        rows.append(d)
    rows.sort(key=lambda r: r.get("ts", ""))
    return rows


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> JSONResponse:
    return JSONResponse({"run_id": run_id, "events": _collect(run_id)})


@app.get("/runs/{run_id}/debug.html", response_class=HTMLResponse)
def get_debug(run_id: str) -> HTMLResponse:
    rows = _collect(run_id)
    # Minimal inline HTML — no Jinja template needed for the stub.
    out = ["<!doctype html><html><head><meta charset=utf-8><title>edustack-video debug</title>",
           "<style>body{font:13px/1.5 ui-monospace,monospace;background:#0f1115;color:#e6e8eb;padding:24px}",
           ".row{border-left:3px solid #6ee7b7;padding:6px 10px;margin:4px 0;background:#161a22;border-radius:6px}",
           ".s{color:#9aa3af;font-size:11px}.t{color:#fbbf24}</style></head><body>",
           f"<h2>{run_id}</h2><p class=s>{len(rows)} events</p>"]
    for r in rows:
        # Escape user input safely.
        from html import escape
        out.append(f"<div class=row><span class=s>{escape(str(r.get('ts','')))} · {escape(r.get('_stream','?'))}</span>"
                   f" <span class=t>{escape(r.get('phase') or r.get('target') or r.get('kind') or '')}</span><br>"
                   f"<code>{escape(json.dumps({k:v for k,v in r.items() if k not in ('_stream','ts')}, default=str)[:1200])}</code></div>")
    out.append("</body></html>")
    return HTMLResponse("".join(out))
