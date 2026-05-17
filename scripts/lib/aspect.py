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


# fal.ai-style preset names accepted by nano-banana-2, gpt-image-2's "auto",
# flux, imagen, etc. Many fal image models reject arbitrary {width, height}
# pairs (HTTP 422 on non-canonical dimensions) but accept these presets.
FAL_PRESET_FOR_ASPECT = {
    "16:9": "landscape_16_9",
    "9:16": "portrait_16_9",
    "1:1":  "square_hd",
}


def fal_image_size(aspect: str, model: str | None = None) -> str | dict:
    """Return the image_size value to send to a fal.ai image model.

    Some models (nano-banana-2, flux) prefer named presets; others
    (gpt-image-2) accept explicit {width, height}. Default: preset name when
    the model is nano-banana / flux-family; explicit dimensions otherwise.

    The return value is meant to be dropped into a fal payload as-is:
        payload["image_size"] = fal_image_size(aspect, model)
    """
    aspect = aspect or "16:9"
    preset = FAL_PRESET_FOR_ASPECT.get(aspect, "landscape_16_9")
    if not model:
        return preset
    m = model.lower()
    # nano-banana, flux, imagen all 422 on arbitrary {w,h} → use preset
    if "nano-banana" in m or "flux" in m or "imagen" in m or "ideogram" in m:
        return preset
    # gpt-image-2 and any-llm-derived ones accept explicit dimensions
    if "gpt-image" in m:
        w, h = parse_wh({
            "16:9": "1536x864",
            "9:16": "864x1536",
            "1:1":  "1024x1024",
        }.get(aspect, "1536x864"))
        return {"width": w, "height": h}
    return preset


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
