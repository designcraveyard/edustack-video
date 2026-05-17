from pathlib import Path
from scripts.lib.script_io import load, dump, Script, Beat


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
