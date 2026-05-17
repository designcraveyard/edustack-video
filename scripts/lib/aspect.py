"""Aspect-aware sizing. Single source of truth for image/video dimensions.

Reads <output>/.config/models.yaml > aspect_sizes[brief.aspect]. Falls back
to seeded defaults if the user hasn't customized.
"""
from __future__ import annotations

ASPECT_DEFAULTS = {
    "16:9": {"storyboard_panel": "1920x1080", "per_keyframe": "1920x1080"},
    "9:16": {"storyboard_panel": "1080x1920", "per_keyframe": "1080x1920"},
    "1:1":  {"storyboard_panel": "1080x1080", "per_keyframe": "1080x1080"},
}


def parse_wh(size: str) -> tuple[int, int]:
    w, h = size.lower().split("x", 1)
    return int(w), int(h)


def size_for(aspect: str, kind: str, models_yaml: dict | None) -> tuple[int, int]:
    """kind in {'storyboard_panel', 'per_keyframe'}."""
    sizes = (models_yaml or {}).get("aspect_sizes") or ASPECT_DEFAULTS
    bucket = sizes.get(aspect) or ASPECT_DEFAULTS.get(aspect) or ASPECT_DEFAULTS["16:9"]
    return parse_wh(str(bucket.get(kind, "1920x1080")))


def grid_for_beats(aspect: str, n_beats: int) -> tuple[int, int]:
    """Pick rows × cols so each cell roughly matches `aspect`.

    For 16:9 we favour more cols, for 9:16 more rows, for 1:1 a square-ish grid.
    n_beats clamps between 1 and 16.
    """
    n = max(1, min(int(n_beats), 16))
    if aspect == "16:9":
        # Prefer cols >= rows, target ratio ~16/9
        cols = max(1, min(4, n))
        rows = max(1, (n + cols - 1) // cols)
    elif aspect == "9:16":
        rows = max(1, min(4, n))
        cols = max(1, (n + rows - 1) // rows)
    else:  # 1:1 or anything else
        cols = max(1, int(n ** 0.5 + 0.5))
        rows = max(1, (n + cols - 1) // cols)
    return rows, cols
