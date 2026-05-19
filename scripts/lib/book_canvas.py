"""Template-aware composition rules for Phase B3 (book-print-prep).

For each layout template, given the gpt-image-2 output (RGBA, native dims)
and the target A4P (2480x3508) or A3L (4961x3508) transparent canvas at 300
DPI, decide where the illustration sits and how it scales.

A rule answers four questions:
  canvas:   "A4P" | "A3L"
  scale:    fraction of the canvas long-side the illustration's long-side occupies
  position: "full" | "left" | "right" | "center" | "lower-center" | "upper-center"
  margin:   inner padding (px) when not full-bleed

Per spec invariant #3 (in CLAUDE.md additions): book pages use A4P or A3L based
on each template's natural aspect — never derive from brief.aspect.
"""
from __future__ import annotations
from dataclasses import dataclass
from PIL import Image
from PIL.ImageFilter import UnsharpMask
from PIL.ImageOps import autocontrast


CANVAS_DIMS: dict[str, tuple[int, int]] = {
    "A4P": (2480, 3508),   # 210×297mm @ 300 DPI
    "A3L": (4961, 3508),   # 420×297mm @ 300 DPI
}


@dataclass(frozen=True)
class ComposeRule:
    canvas: str
    scale: float
    position: str
    margin: int = 80


RULES: dict[str, ComposeRule] = {
    "full-bleed-with-text-zone":  ComposeRule("A3L", 1.00, "full",          margin=0),
    "vignette-on-page":           ComposeRule("A4P", 0.60, "lower-center",  margin=120),
    "split-layout":               ComposeRule("A3L", 0.60, "left",          margin=120),
    "scattered-spots":            ComposeRule("A4P", 0.90, "center",        margin=120),
    "full-spread-no-text":        ComposeRule("A3L", 1.00, "full",          margin=0),
    "illustrated-border":         ComposeRule("A4P", 0.95, "center",        margin=120),
    "character-text-pocket":      ComposeRule("A4P", 0.70, "upper-center",  margin=120),
    "connected-infographic":      ComposeRule("A4P", 0.95, "center",        margin=120),
    "spread-scene-plus-spots":    ComposeRule("A3L", 1.00, "full",          margin=0),
}


def _position_xy(canvas_w: int, canvas_h: int, art_w: int, art_h: int,
                 position: str, margin: int) -> tuple[int, int]:
    if position == "full":
        return (0, 0)
    if position == "left":
        return (margin, (canvas_h - art_h) // 2)
    if position == "right":
        return (canvas_w - art_w - margin, (canvas_h - art_h) // 2)
    if position == "center":
        return ((canvas_w - art_w) // 2, (canvas_h - art_h) // 2)
    if position == "lower-center":
        return ((canvas_w - art_w) // 2, canvas_h - art_h - margin)
    if position == "upper-center":
        return ((canvas_w - art_w) // 2, margin)
    return ((canvas_w - art_w) // 2, (canvas_h - art_h) // 2)


def compose(image: Image.Image, template: str, flatten_to_white: bool = True) -> Image.Image:
    """Scale the gpt-image-2 output to fully cover the template's print canvas
    (A4P 2480×3508 or A3L 4961×3508 @ 300 DPI), then flatten any transparency
    onto a solid white page background.

    Since 0.6.1 the gpt-image-2 output IS already the composed page layout
    (the renderer's two-image prompting includes layout + text-zone composition
    inside the generated image). The previous behaviour — scaling the image to
    a fraction of the canvas and positioning it left/right/center with margins
    — produced redundant blank space because the image's own internal text
    zone was being placed inside ANOTHER positional offset on the canvas.

    What this function does now:
      1. Auto-level + mild unsharp on RGB (preserve any alpha).
      2. Aspect-correct COVER scale to the canvas dims (slightly crop the
         long edge if gpt-image-2's preset aspect doesn't match A3L/A4P
         exactly — the mismatch is ~0.5% so the crop is invisible).
      3. Flatten transparent regions onto solid white (RGB output). Designer
         can then place voice copy directly on the white text zone in
         InDesign — no checker-pattern confusion when previewed.

    flatten_to_white=False keeps the alpha channel intact (RGBA output) for
    workflows that want true transparency. Default is True per user feedback.

    The legacy per-template position/scale/margin rules in RULES are kept
    only for `canvas_for()` lookups (A4P vs A3L). Their geometry fields are
    no longer consulted in compose().
    """
    rule = RULES.get(template)
    if rule is None:
        raise KeyError(f"unknown book template: {template}")

    canvas_w, canvas_h = CANVAS_DIMS[rule.canvas]

    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Mild auto-level + unsharp on RGB channels (preserve alpha untouched).
    r, g, b, a = image.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = autocontrast(rgb, cutoff=1)
    rgb = rgb.filter(UnsharpMask(radius=1.5, percent=70, threshold=2))
    r2, g2, b2 = rgb.split()
    image = Image.merge("RGBA", (r2, g2, b2, a))

    # Cover-scale: pick the larger of two scale factors so the image fully
    # covers the canvas; the slight aspect mismatch crops a few pixels off
    # the over-long edge.
    sx = canvas_w / image.width
    sy = canvas_h / image.height
    scale = max(sx, sy)
    scaled_w = int(round(image.width * scale))
    scaled_h = int(round(image.height * scale))
    scaled = image.resize((scaled_w, scaled_h), Image.LANCZOS)

    # Center-crop to the canvas.
    crop_x = (scaled_w - canvas_w) // 2
    crop_y = (scaled_h - canvas_h) // 2
    cropped = scaled.crop((crop_x, crop_y, crop_x + canvas_w, crop_y + canvas_h))

    if flatten_to_white:
        white = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
        # alpha_composite expects RGBA on RGBA; do it on RGBA then convert.
        bg = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
        bg.alpha_composite(cropped)
        return bg.convert("RGB")

    return cropped


def canvas_for(template: str) -> str:
    """Return the canvas label ('A4P' | 'A3L') for a template id."""
    return RULES[template].canvas
