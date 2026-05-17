"""Read/write <run-dir>/run.json — the per-run state machine."""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
import json


PHASES = ["script", "vo", "characters", "storyboard", "clips", "stitch"]


@dataclass
class RunState:
    run_dir: Path
    run_id: str = ""
    status: str = "running"          # running | complete | failed
    next_phase: str = "script"
    phases: dict = field(default_factory=dict)
    items: dict = field(default_factory=dict)

    @classmethod
    def load_or_init(cls, run_dir: Path) -> "RunState":
        p = run_dir / "run.json"
        if p.exists():
            data = json.loads(p.read_text())
            return cls(run_dir=run_dir, **data)
        rs = cls(run_dir=run_dir, run_id=run_dir.name)
        rs.save()
        return rs

    def save(self) -> None:
        p = self.run_dir / "run.json"
        body = {k: v for k, v in asdict(self).items() if k != "run_dir"}
        p.write_text(json.dumps(body, indent=2, default=str))

    def mark_phase(self, phase: str, status: str, comment: str | None = None) -> None:
        entry = self.phases.setdefault(phase, {"gate_comments": []})
        entry["status"] = status
        entry["updated_at"] = datetime.now(UTC).isoformat()
        if comment:
            entry["gate_comments"].append({"ts": entry["updated_at"], "text": comment})
        if status == "approved":
            idx = PHASES.index(phase)
            self.next_phase = PHASES[idx + 1] if idx + 1 < len(PHASES) else "done"
            if self.next_phase == "done":
                self.status = "complete"
        self.save()
