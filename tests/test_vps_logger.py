import json
from pathlib import Path
from scripts.lib.supabase_sink import SupabaseSink


def test_no_url_writes_to_local_jsonl(tmp_path: Path):
    run_dir = tmp_path / "run"
    sink = SupabaseSink(url=None, anon_key=None, user_id="u1", run_dir=run_dir)
    sink.log("rid", "vo", "info", "hello")
    sink.gate("rid", "gate-1", "approve", "beat:1", "lgtm")
    lines = (run_dir / "logs" / "local.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    a = json.loads(lines[0])
    b = json.loads(lines[1])
    assert a["stream"] == "logs"
    assert a["payload"]["msg"] == "hello"
    assert b["stream"] == "gates"
    assert b["payload"]["decision"] == "approve"


def test_url_but_no_anon_falls_back(tmp_path: Path):
    run_dir = tmp_path / "run"
    sink = SupabaseSink(url="https://example.invalid", anon_key=None, user_id="u1",
                        run_dir=run_dir)
    sink.heartbeat("rid", "vo", "started")
    assert (run_dir / "logs" / "local.jsonl").is_file()


def test_unreachable_supabase_appends_to_local(tmp_path: Path):
    run_dir = tmp_path / "run"
    sink = SupabaseSink(url="http://127.0.0.1:1", anon_key="anon-fake",
                        user_id="u1", run_dir=run_dir, timeout_s=1.0)
    sink.log("rid", "vo", "warn", "transport-fail")
    contents = (run_dir / "logs" / "local.jsonl").read_text()
    assert "transport-fail" in contents
