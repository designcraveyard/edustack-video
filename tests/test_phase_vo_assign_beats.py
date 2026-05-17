from scripts.phase_vo import assign_beats, _alignment_to_words
from scripts.lib.script_io import Script, Beat


def _word(text, s_ms, e_ms): return {"text": text, "start_ms": s_ms, "end_ms": e_ms}


def test_alignment_to_words_groups_chars_into_words():
    alignment = {
        "characters":                    list("Hi there"),
        "character_start_times_seconds": [0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70],
        "character_end_times_seconds":   [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.85],
    }
    out = _alignment_to_words(alignment)
    assert [w["text"] for w in out] == ["Hi", "there"]
    assert out[0]["start_ms"] == 0
    assert out[0]["end_ms"] == 200
    assert out[1]["start_ms"] == 300
    assert out[1]["end_ms"] == 850


def test_assign_beats_splits_words_in_order():
    script = Script(title="t", duration_estimate_seconds=2, mode="standard",
                    class_level=1, language="English",
                    beats=[
                        Beat(id=1, label="a", estimate_seconds=1, narration="Hello world."),
                        Beat(id=2, label="b", estimate_seconds=1, narration="Bye now."),
                    ])
    words = [
        _word("Hello", 0, 400),
        _word("world", 400, 800),
        _word("Bye", 900, 1100),
        _word("now", 1100, 1400),
    ]
    beats = assign_beats(script, words)
    assert [b["id"] for b in beats] == [1, 2]
    assert beats[0]["word_range"] == [0, 2]
    assert beats[1]["word_range"] == [2, 4]
    assert beats[0]["duration_ms"] == 800
    assert beats[1]["duration_ms"] == 500
