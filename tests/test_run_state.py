import json
from pathlib import Path

from scripts.lib.run_state import RunState, PHASES


def test_phase_order():
    assert PHASES == ["script", "vo", "characters", "storyboard", "clips", "stitch"]


def test_load_or_init_creates_run_json(tmp_path: Path):
    run_dir = tmp_path / "2026-05-17-test-run"
    run_dir.mkdir()
    rs = RunState.load_or_init(run_dir)
    assert rs.run_id == run_dir.name
    assert rs.status == "running"
    assert (run_dir / "run.json").is_file()


def test_mark_phase_approved_advances_next_phase(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    rs = RunState.load_or_init(run_dir)
    rs.mark_phase("script", "approved")
    assert rs.next_phase == "vo"
    rs.mark_phase("vo", "approved")
    assert rs.next_phase == "characters"


def test_mark_phase_records_comment(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    rs = RunState.load_or_init(run_dir)
    rs.mark_phase("script", "regen_requested", comment="rewrite hook")
    saved = json.loads((run_dir / "run.json").read_text())
    assert saved["phases"]["script"]["gate_comments"][0]["text"] == "rewrite hook"


def test_completing_last_phase_marks_run_complete(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    rs = RunState.load_or_init(run_dir)
    for p in PHASES:
        rs.mark_phase(p, "approved")
    assert rs.status == "complete"
    assert rs.next_phase == "done"
