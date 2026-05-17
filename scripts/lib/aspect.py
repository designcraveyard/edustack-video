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


def fal_image_payload(
    aspect: str,
    model: str | None = None,
    models_cfg: dict | None = None,
    stage: str | None = None,
) -> dict:
    """Return a dict of size-related params to merge into a fal payload.

    Different fal models accept different parameter shapes — verified
    against the live fal.ai OpenAPI on 2026-05-17:

      - nano-banana-2: `aspect_ratio` (enum: 21:9, 16:9, 3:2, 4:3, 5:4, 1:1,
        4:5, 3:4, 2:3, 9:16, 4:1, 1:4, 8:1, 1:8, auto) + `resolution` (enum:
        0.5K, 1K, 2K, 4K). Does NOT have `image_size`.
      - gpt-image-2: `image_size` (preset enum OR ImageSize object).
      - flux/dev, imagen, ideogram: `image_size` (preset enum only).
      - seedance / video i2v: `resolution` (enum: 480p, 720p, 1080p).

    Override precedence (highest first):
      1. `models_cfg[stage]._payload` — raw merge-in dict (advanced).
      2. `models_cfg[stage]` keys matching the model's native shape
         (e.g. aspect_ratio + resolution for nano-banana, image_size for
         gpt-image-2).
      3. Model-based default from `aspect`.

    Returns a dict ready to spread into a fal payload:
        payload = {"prompt": p, **fal_image_payload("9:16", model, cfg.models, "per_keyframe")}
    """
    m = (model or "").lower()

    # 1. Raw override
    if models_cfg and stage:
        stage_cfg = models_cfg.get(stage) or {}
        raw = stage_cfg.get("_payload")
        if isinstance(raw, dict):
            return dict(raw)

        # 2. Targeted per-key override for the model's native shape
        override: dict = {}
        if "nano-banana" in m:
            if stage_cfg.get("aspect_ratio"):
                override["aspect_ratio"] = stage_cfg["aspect_ratio"]
            if stage_cfg.get("resolution"):
                override["resolution"] = stage_cfg["resolution"]
            if override:
                # Fill any missing field with model-default for the aspect.
                override.setdefault("aspect_ratio", _nano_banana_aspect(aspect))
                override.setdefault("resolution", "2K")
                return override
        else:
            if "image_size" in stage_cfg:
                size = stage_cfg["image_size"]
                if isinstance(size, str) and size.strip():
                    return {"image_size": size}
                if isinstance(size, dict) and "width" in size and "height" in size:
                    return {"image_size": {"width": int(size["width"]),
                                            "height": int(size["height"])}}

    # 3. Model-based default
    if "nano-banana" in m:
        return {"aspect_ratio": _nano_banana_aspect(aspect), "resolution": "2K"}
    if "gpt-image" in m:
        return {"image_size": {
            "16:9": {"width": 1536, "height": 864},
            "9:16": {"width": 864, "height": 1536},
            "1:1":  {"width": 1024, "height": 1024},
        }.get(aspect, {"width": 1536, "height": 864})}
    if "flux" in m or "imagen" in m or "ideogram" in m:
        return {"image_size": FAL_PRESET_FOR_ASPECT.get(aspect, "landscape_16_9")}
    # Unknown model — assume preset image_size.
    return {"image_size": FAL_PRESET_FOR_ASPECT.get(aspect, "landscape_16_9")}


def _nano_banana_aspect(aspect: str) -> str:
    """nano-banana-2 accepts the brief.aspect string directly; default to auto."""
    valid = {"21:9", "16:9", "3:2", "4:3", "5:4", "1:1",
             "4:5", "3:4", "2:3", "9:16", "4:1", "1:4", "8:1", "1:8"}
    return aspect if aspect in valid else "auto"


def fal_image_size(
    aspect: str,
    model: str | None = None,
    models_cfg: dict | None = None,
    stage: str | None = None,
) -> str | dict:
    """Return the image_size value to send to a fal.ai image model.

    Override precedence (first match wins):
      1. `models_cfg[stage].image_size` — user / Claude-supplied override in
         <output>/.config/models.yaml. May be either a preset string
         (e.g. "portrait_hd") or {"width": W, "height": H}.
      2. Model-based default: nano-banana / flux / imagen / ideogram → preset
         name keyed by aspect; gpt-image-2 → explicit {width, height}.
      3. Fallback: landscape_16_9.

    The return value is meant to be dropped into a fal payload as-is:
        payload["image_size"] = fal_image_size(aspect, model, cfg.models, "per_keyframe")
    """
    # 1. Stage-level override
    if models_cfg and stage:
        stage_cfg = models_cfg.get(stage) or {}
        override = stage_cfg.get("image_size")
        if isinstance(override, str) and override.strip():
            return override
        if isinstance(override, dict) and "width" in override and "height" in override:
            return {"width": int(override["width"]), "height": int(override["height"])}

    # 2. Model-based default
    aspect = aspect or "16:9"
    preset = FAL_PRESET_FOR_ASPECT.get(aspect, "landscape_16_9")
    if not model:
        return preset
    m = model.lower()
    if "nano-banana" in m or "flux" in m or "imagen" in m or "ideogram" in m:
        return preset
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
