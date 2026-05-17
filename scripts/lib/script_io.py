"""Parse and emit script.md — the canonical beat-structured script.

Format (see skills/script-writer/references/educational-script-structure.md):
  ---
  title: ...
  duration_estimate_seconds: 58
  mode: standard | word_to_word
  class_level: 6
  language: English
  ---

  [BEAT 1] hook (≈5s)
  Narration paragraph...
  <!-- visual: ... -->

  [BEAT 2] ...
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re
import yaml


@dataclass
class Beat:
    id: int
    label: str
    estimate_seconds: float | None
    narration: str
    visual: str | None = None

    @property
    def narration_plain(self) -> str:
        """Narration with HTML comments stripped — what we send to TTS."""
        return re.sub(r"<!--.*?-->", "", self.narration, flags=re.DOTALL).strip()


@dataclass
class Script:
    title: str
    duration_estimate_seconds: float
    mode: str = "standard"
    class_level: int = 6
    language: str = "English"
    beats: list[Beat] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def narration_text(self) -> str:
        """All beats' plain narration, separated by blank lines.
        This is what gets sent to ElevenLabs as a single TTS call."""
        return "\n\n".join(b.narration_plain for b in self.beats if b.narration_plain)


_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_BEAT_HDR = re.compile(
    r"^\[BEAT\s+(\d+)\][ \t]*(.*?)?(?:[ \t]*\(≈?\s*([\d.]+)\s*s\))?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
_VISUAL = re.compile(r"<!--\s*visual\s*:\s*(.*?)-->", re.DOTALL | re.IGNORECASE)


def load(path: Path) -> Script:
    text = Path(path).read_text(encoding="utf-8")
    fm_match = _FRONTMATTER.search(text)
    if not fm_match:
        raise ValueError(f"{path}: missing YAML frontmatter")
    fm = yaml.safe_load(fm_match.group(1)) or {}
    body = text[fm_match.end():]
    # Slice the body into beats by header positions.
    headers = list(_BEAT_HDR.finditer(body))
    beats: list[Beat] = []
    for i, m in enumerate(headers):
        bid = int(m.group(1))
        label = (m.group(2) or "").strip()
        est = float(m.group(3)) if m.group(3) else None
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(body)
        chunk = body[start:end].strip()
        vis_m = _VISUAL.search(chunk)
        visual = vis_m.group(1).strip() if vis_m else None
        beats.append(Beat(id=bid, label=label, estimate_seconds=est, narration=chunk, visual=visual))
    return Script(
        title=fm.get("title", "Untitled"),
        duration_estimate_seconds=float(fm.get("duration_estimate_seconds", 60)),
        mode=fm.get("mode", "standard"),
        class_level=int(fm.get("class_level", 6)),
        language=fm.get("language", "English"),
        beats=beats,
        extra={k: v for k, v in fm.items() if k not in {
            "title", "duration_estimate_seconds", "mode", "class_level", "language"}},
    )


def dump(s: Script, path: Path) -> None:
    fm = {
        "title": s.title,
        "duration_estimate_seconds": round(s.duration_estimate_seconds, 1),
        "mode": s.mode,
        "class_level": s.class_level,
        "language": s.language,
        **s.extra,
    }
    out = ["---", yaml.safe_dump(fm, sort_keys=False).strip(), "---", ""]
    for b in s.beats:
        hdr = f"[BEAT {b.id}]" + (f" {b.label}" if b.label else "")
        if b.estimate_seconds is not None:
            hdr += f" (≈{b.estimate_seconds:.0f}s)"
        out.append(hdr)
        out.append(b.narration.strip())
        if b.visual and "<!--" not in b.narration:
            out.append(f"<!-- visual: {b.visual} -->")
        out.append("")
    Path(path).write_text("\n".join(out), encoding="utf-8")
