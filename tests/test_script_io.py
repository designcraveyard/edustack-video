from pathlib import Path
from scripts.lib.script_io import load, dump, parse_cast, Script, Beat, CastMember


SAMPLE = """---
title: How photosynthesis works
duration_estimate_seconds: 18
mode: standard
class_level: 6
language: English
---

[BEAT 1] hook (≈6s)
Why does a plant in a dark closet droop?
<!-- visual: plant on a sunny windowsill -->

[BEAT 2] mechanism (≈12s)
Chloroplasts catch sunlight and bake glucose for the leaf.
"""


def test_load_roundtrip(tmp_path: Path):
    p = tmp_path / "s.md"
    p.write_text(SAMPLE)
    s = load(p)
    assert s.title == "How photosynthesis works"
    assert s.duration_estimate_seconds == 18
    assert s.mode == "standard"
    assert s.class_level == 6
    assert len(s.beats) == 2
    assert s.beats[0].id == 1
    assert s.beats[0].label == "hook"
    assert s.beats[0].estimate_seconds == 6
    assert s.beats[0].visual == "plant on a sunny windowsill"
    assert s.beats[1].id == 2
    assert s.beats[1].label == "mechanism"


def test_narration_plain_strips_visual_hint(tmp_path: Path):
    p = tmp_path / "s.md"
    p.write_text(SAMPLE)
    s = load(p)
    assert "<!--" not in s.beats[0].narration_plain
    assert "plant in a dark closet" in s.beats[0].narration_plain


def test_narration_text_joins_beats(tmp_path: Path):
    p = tmp_path / "s.md"
    p.write_text(SAMPLE)
    s = load(p)
    out = s.narration_text()
    assert "Why does a plant" in out
    assert "Chloroplasts catch" in out
    # Has blank line between beats
    assert "\n\n" in out


# ── Cast parser ────────────────────────────────────────────────────────────
CAST_SAMPLE = """---
title: Road Safety
duration_estimate_seconds: 45
mode: standard
class_level: 5
language: English
---

## Cast

### Jay

- **Role in the video**: Class-5 hockey player who cuts across the road
- **Personality**: Determined, easily distracted by hockey daydreams, warm and well-meaning
- **Voice and tone**: Casual Hinglish, energetic, mid-paced
- **Looks**: A slightly taller child silhouette with determined eyebrows, warm brown skin, dark hair, and a clear hockey-stick pose that reads instantly.

### Scooterist

- **Role in the video**: Unaware adult riding a scooter
- **Personality**: Calm, slightly tired, focused on the road ahead
- **Voice and tone**: Steady, mid-paced
- **Looks**: A simple, readable adult silhouette on a scooter, wearing a proper helmet, modest everyday clothes, and warm neutral colours.

## Sound

- Ambient music: light orchestral

[BEAT 1] hook (5s)
Jay is daydreaming about a winning goal.
"""


CAST_OFF_SAMPLE = """---
title: x
duration_estimate_seconds: 30
mode: standard
class_level: 5
language: English
---

## Cast

Character mode: OFF — narration only.

[BEAT 1]
Hello
"""


def test_parse_cast_extracts_two_characters(tmp_path: Path):
    p = tmp_path / "s.md"
    p.write_text(CAST_SAMPLE)
    s = load(p)
    assert len(s.cast) == 2
    jay, scooterist = s.cast
    assert jay.name == "Jay"
    assert jay.slug == "jay"
    assert "hockey-stick pose" in jay.looks
    assert "Determined" in jay.personality
    assert "Hinglish" in jay.voice_tone
    assert "Class-5 hockey player" in jay.role
    assert scooterist.name == "Scooterist"
    assert scooterist.slug == "scooterist"
    assert "warm neutral colours" in scooterist.looks


def test_cast_verbatim_description_includes_all_fields(tmp_path: Path):
    """verbatim_description is the paragraph downstream prompts paste IDENTICALLY.
    It must surface looks (load-bearing) plus role / personality / voice tags
    so the model has rich grounding."""
    p = tmp_path / "s.md"
    p.write_text(CAST_SAMPLE)
    s = load(p)
    jay_desc = s.cast[0].verbatim_description
    # looks comes first, unprefixed
    assert jay_desc.startswith("A slightly taller child silhouette")
    # subsequent fields appear prefixed
    assert "Role: Class-5 hockey player" in jay_desc
    assert "Personality: Determined" in jay_desc
    assert "Voice & tone: Casual Hinglish" in jay_desc


def test_parse_cast_off_returns_empty(tmp_path: Path):
    """`Character mode: OFF — narration only.` in the Cast section means
    no characters in this video; parse_cast() returns []."""
    p = tmp_path / "s.md"
    p.write_text(CAST_OFF_SAMPLE)
    s = load(p)
    assert s.cast == []


def test_parse_cast_no_section_returns_empty():
    """Bodies without a `## Cast` section return [] — callers fall back to
    a synthesised CastMember (see phase_characters.fallback_cast_from_script)."""
    assert parse_cast("just some narration\n\n[BEAT 1] x\n") == []


def test_cast_slug_handles_special_chars():
    m = CastMember(name="Leafy Grazer (the herbivore)", looks="watercolour mascot")
    assert m.slug == "leafy-grazer-the-herbivore"


def test_dump_then_load_is_stable(tmp_path: Path):
    s1 = Script(
        title="T", duration_estimate_seconds=12, mode="standard",
        class_level=4, language="English",
        beats=[
            Beat(id=1, label="hook", estimate_seconds=6, narration="Hello there."),
            Beat(id=2, label="recap", estimate_seconds=6, narration="Bye now."),
        ],
    )
    p = tmp_path / "s.md"
    dump(s1, p)
    s2 = load(p)
    assert s2.title == "T"
    assert len(s2.beats) == 2
    assert s2.beats[0].narration.strip().startswith("Hello")
