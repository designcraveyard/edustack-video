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
class CastMember:
    """One character pulled from the script's `## Cast` block.

    The script-writer skill produces a Cast block with a `### {name}` header
    per character, followed by bullet sub-sections: Role / Personality /
    Voice and tone / Looks. This object is the parsed form, and it's what
    Phase 3a (character sheets) and downstream prompts consume verbatim.
    """
    name: str
    role: str = ""
    personality: str = ""
    voice_tone: str = ""
    looks: str = ""

    @property
    def slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-") or "character"

    @property
    def verbatim_description(self) -> str:
        """The block that gets pasted into every downstream image/clip prompt.

        Looks is the load-bearing piece (it determines what the model draws).
        Role + Personality + Voice add context that helps the model pick poses
        and expressions. We compose them into ONE paragraph because that's how
        gpt-image-2 reads CHARACTERS sections (paragraph per character).
        """
        parts = []
        if self.looks:
            parts.append(self.looks.strip())
        if self.role:
            parts.append(f"Role: {self.role.strip()}")
        if self.personality:
            parts.append(f"Personality: {self.personality.strip()}")
        if self.voice_tone:
            parts.append(f"Voice & tone: {self.voice_tone.strip()}")
        return " ".join(parts)


@dataclass
class Script:
    title: str
    duration_estimate_seconds: float
    mode: str = "standard"
    class_level: int = 6
    language: str = "English"
    beats: list[Beat] = field(default_factory=list)
    cast: list[CastMember] = field(default_factory=list)
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

# Cast block lives BEFORE the first [BEAT N] header. Format follows
# seed/prompts/script-writer.md:141-:
#   ## Cast
#   ### {character name}
#   - **Role in the video**: ...
#   - **Personality**: ...
#   - **Voice and tone**: ...
#   - **Looks**: ...
_CAST_BLOCK = re.compile(
    r"^##\s+Cast\s*\n(.+?)(?=^##\s|\Z|^\[BEAT\s+\d+\])",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)
_CAST_HEADER = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
_CAST_FIELD = re.compile(
    r"^\s*[-*]\s*\*\*([^*]+)\*\*\s*[:—–-]?\s*(.+?)(?=^\s*[-*]\s*\*\*|\Z|^###)",
    re.MULTILINE | re.DOTALL,
)


def parse_cast(body: str) -> list[CastMember]:
    """Extract the `## Cast` block from the body and return parsed members.

    Tolerates missing fields and out-of-order sub-bullets. When there is no
    Cast section (or the script_writer wrote `Character mode: OFF — narration
    only.`), returns an empty list — callers must handle that.
    """
    block = _CAST_BLOCK.search(body)
    if not block:
        return []
    text = block.group(1)
    if re.search(r"character\s+mode:\s*OFF", text, flags=re.IGNORECASE):
        return []
    headers = list(_CAST_HEADER.finditer(text))
    members: list[CastMember] = []
    for i, h in enumerate(headers):
        name = h.group(1).strip()
        seg_start = h.end()
        seg_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        seg = text[seg_start:seg_end]
        fields = {
            k.strip().lower(): v.strip()
            for k, v in _CAST_FIELD.findall(seg)
        }
        m = CastMember(
            name=name,
            role=fields.get("role in the video") or fields.get("role") or "",
            personality=fields.get("personality") or "",
            voice_tone=fields.get("voice and tone") or fields.get("voice") or "",
            looks=fields.get("looks") or "",
        )
        members.append(m)
    return members


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
    cast = parse_cast(body)
    return Script(
        title=fm.get("title", "Untitled"),
        duration_estimate_seconds=float(fm.get("duration_estimate_seconds", 60)),
        mode=fm.get("mode", "standard"),
        class_level=int(fm.get("class_level", 6)),
        language=fm.get("language", "English"),
        beats=beats,
        cast=cast,
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
