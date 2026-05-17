from scripts.lib.aspect import parse_wh, size_for, grid_for_beats, ASPECT_DEFAULTS


def test_parse_wh():
    assert parse_wh("1920x1080") == (1920, 1080)
    assert parse_wh("1080X1920") == (1080, 1920)


def test_size_for_defaults():
    # No models.yaml → use ASPECT_DEFAULTS
    assert size_for("16:9", "per_keyframe", None) == (1920, 1080)
    assert size_for("9:16", "per_keyframe", None) == (1080, 1920)
    assert size_for("1:1", "per_keyframe", None) == (1080, 1080)


def test_size_for_override():
    yaml = {"aspect_sizes": {"16:9": {"per_keyframe": "1280x720"}}}
    assert size_for("16:9", "per_keyframe", yaml) == (1280, 720)


def test_size_for_unknown_aspect_falls_back_to_16_9():
    assert size_for("21:9", "per_keyframe", None) == (1920, 1080)


def test_grid_for_beats_16_9_prefers_more_cols():
    rows, cols = grid_for_beats("16:9", 6)
    assert cols >= rows


def test_grid_for_beats_9_16_prefers_more_rows():
    rows, cols = grid_for_beats("9:16", 6)
    assert rows >= cols


def test_grid_for_beats_clamps():
    rows, cols = grid_for_beats("16:9", 0)
    assert rows * cols >= 1
    rows, cols = grid_for_beats("16:9", 100)
    assert rows * cols <= 16
