from scripts.make_subtitles import chunk_words, chunk_words_grouped, fmt


def _w(text, s, e): return {"text": text, "start_ms": s, "end_ms": e}


def test_fmt_milliseconds():
    assert fmt(0) == "00:00:00,000"
    assert fmt(1_500) == "00:00:01,500"
    assert fmt(3_661_001) == "01:01:01,001"


def test_chunk_words_punctuation_breaks_line():
    words = [
        _w("Why", 0, 300),
        _w("does", 300, 500),
        _w("it.", 500, 900),     # ends with '.'
        _w("Photosynthesis", 1100, 1900),
    ]
    cues = chunk_words(words)
    assert len(cues) == 2
    assert cues[0][2] == "Why does it."
    assert cues[1][2] == "Photosynthesis"


def test_chunk_words_max_words_breaks_line():
    # Each word is ~250ms wide so the chunks comfortably clear the
    # min_duration_ms tail-merge threshold (default 800ms).
    words = [_w(f"w{i}", i * 300, i * 300 + 250) for i in range(15)]
    cues = chunk_words(words, max_words=5)
    # 15 words / 5 max words = 3 cues
    assert len(cues) == 3


def test_chunk_words_grouped_preserves_word_objects():
    words = [_w("Hello", 0, 200), _w("world!", 200, 600), _w("Bye", 800, 1100)]
    groups = chunk_words_grouped(words)
    # Hello + world! ends with !, then Bye stands alone (merged into prev due to short tail)
    # Either way: total words covered == 3
    assert sum(len(g["words"]) for g in groups) == 3
    # Each group preserves dict structure with start/end_ms
    for g in groups:
        assert g["start_ms"] <= g["end_ms"]
        for w in g["words"]:
            assert "text" in w and "start_ms" in w and "end_ms" in w
