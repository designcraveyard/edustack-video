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


from scripts.lib.aspect import fal_image_size


def test_fal_image_size_nano_banana_uses_preset():
    assert fal_image_size("9:16", "fal-ai/nano-banana-2") == "portrait_16_9"
    assert fal_image_size("16:9", "fal-ai/nano-banana-2") == "landscape_16_9"
    assert fal_image_size("1:1", "fal-ai/nano-banana-2") == "square_hd"


def test_fal_image_size_gpt_image_uses_dimensions():
    out = fal_image_size("9:16", "fal-ai/gpt-image-2")
    assert isinstance(out, dict)
    assert out["width"] == 864 and out["height"] == 1536


def test_fal_image_size_stage_override_preset_string():
    cfg = {"per_keyframe": {"image_size": "portrait_hd"}}
    assert fal_image_size("9:16", "fal-ai/nano-banana-2", cfg, "per_keyframe") == "portrait_hd"


def test_fal_image_size_stage_override_dimensions():
    cfg = {"per_keyframe": {"image_size": {"width": 720, "height": 1280}}}
    out = fal_image_size("9:16", "fal-ai/nano-banana-2", cfg, "per_keyframe")
    assert out == {"width": 720, "height": 1280}


def test_fal_image_size_stage_override_only_applies_to_named_stage():
    cfg = {"per_keyframe": {"image_size": "portrait_hd"}}
    # storyboard_panel has no override → falls back to gpt-image-2 default dims
    out = fal_image_size("9:16", "fal-ai/gpt-image-2", cfg, "storyboard_panel")
    assert out == {"width": 864, "height": 1536}


from scripts.lib.aspect import fal_image_payload


def test_payload_nano_banana_uses_aspect_ratio_and_resolution():
    """nano-banana-2 schema (fal.ai 2026-05-17): aspect_ratio + resolution.
    It DOES NOT have an image_size field at all — sending image_size was
    silently ignored by the server."""
    out = fal_image_payload("9:16", "fal-ai/nano-banana-2")
    assert "image_size" not in out
    assert out["aspect_ratio"] == "9:16"
    assert out["resolution"] in {"1K", "2K", "4K", "0.5K"}


def test_payload_nano_banana_default_resolution_is_high():
    out = fal_image_payload("16:9", "fal-ai/nano-banana-2")
    assert out["aspect_ratio"] == "16:9"
    assert out["resolution"] == "2K"


def test_payload_nano_banana_unknown_aspect_falls_back_to_auto():
    out = fal_image_payload("21:9", "fal-ai/nano-banana-2")
    # 21:9 IS valid for nano-banana-2; auto is fallback for truly unknown.
    assert out["aspect_ratio"] == "21:9"
    out2 = fal_image_payload("weird-aspect", "fal-ai/nano-banana-2")
    assert out2["aspect_ratio"] == "auto"


def test_payload_gpt_image_2_uses_image_size():
    out = fal_image_payload("16:9", "fal-ai/gpt-image-2")
    assert "image_size" in out
    assert out["image_size"] == {"width": 1536, "height": 864}
    assert "aspect_ratio" not in out


def test_payload_flux_uses_preset():
    out = fal_image_payload("9:16", "fal-ai/flux/dev")
    assert out == {"image_size": "portrait_16_9"}


def test_payload_nano_banana_override_aspect_ratio():
    cfg = {"per_keyframe": {"aspect_ratio": "4:3"}}
    out = fal_image_payload("16:9", "fal-ai/nano-banana-2", cfg, "per_keyframe")
    assert out["aspect_ratio"] == "4:3"
    assert out["resolution"] == "2K"  # missing → filled from default


def test_payload_nano_banana_override_resolution():
    cfg = {"per_keyframe": {"resolution": "4K"}}
    out = fal_image_payload("9:16", "fal-ai/nano-banana-2", cfg, "per_keyframe")
    assert out["aspect_ratio"] == "9:16"  # missing → filled from aspect
    assert out["resolution"] == "4K"


def test_payload_gpt_image_image_size_override():
    cfg = {"storyboard_panel": {"image_size": "portrait_16_9"}}
    out = fal_image_payload("9:16", "fal-ai/gpt-image-2", cfg, "storyboard_panel")
    assert out == {"image_size": "portrait_16_9"}


def test_payload_raw_underscore_payload_wins():
    cfg = {"per_keyframe": {"_payload": {"foo": "bar", "baz": 42}}}
    out = fal_image_payload("9:16", "fal-ai/nano-banana-2", cfg, "per_keyframe")
    assert out == {"foo": "bar", "baz": 42}
