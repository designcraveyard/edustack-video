import json
from pathlib import Path
from scripts.lib.vps_logger import VPSLogger


def test_no_url_writes_to_local_jsonl(tmp_path: Path):
    run_dir = tmp_path / "run"
    log = VPSLogger(vps_url=None, token=None, run_dir=run_dir)
    log.log("rid", "vo", "info", "hello")
    log.gate("rid", "gate-1", "approve", "beat:1", "lgtm")
    lines = (run_dir / "logs" / "local.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    a = json.loads(lines[0])
    b = json.loads(lines[1])
    assert a["path"] == "/logs"
    assert a["msg"] == "hello"
    assert b["path"] == "/gates"
    assert b["decision"] == "approve"


def test_url_but_no_token_still_falls_back(tmp_path: Path):
    run_dir = tmp_path / "run"
    log = VPSLogger(vps_url="https://example.invalid", token=None, run_dir=run_dir)
    log.heartbeat("rid", "vo", "started")
    assert (run_dir / "logs" / "local.jsonl").is_file()


def test_unreachable_vps_appends_to_local(tmp_path: Path):
    run_dir = tmp_path / "run"
    log = VPSLogger(vps_url="http://127.0.0.1:1", token="t", run_dir=run_dir)
    log.log("rid", "vo", "warn", "transport-fail")
    contents = (run_dir / "logs" / "local.jsonl").read_text()
    assert "transport-fail" in contents
