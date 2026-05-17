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


def compose(image: Image.Image, template: str) -> Image.Image:
    """Compose an RGBA illustration onto a transparent A4P or A3L canvas at the
    position prescribed by the template's rule. Returns a new RGBA image at
    canvas dims; never modifies the input."""
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

    # Scale so the art's long-side equals scale * canvas-long-side - 2*margin.
    target_long = int(max(canvas_w, canvas_h) * rule.scale) - 2 * rule.margin
    if target_long <= 0:
        target_long = max(canvas_w, canvas_h) - 2 * rule.margin
    src_long = max(image.width, image.height)
    factor = target_long / src_long if src_long > 0 else 1.0
    art_w = max(1, int(image.width * factor))
    art_h = max(1, int(image.height * factor))
    art = image.resize((art_w, art_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    x, y = _position_xy(canvas_w, canvas_h, art_w, art_h, rule.position, rule.margin)
    canvas.alpha_composite(art, (x, y))
    return canvas


def canvas_for(template: str) -> str:
    """Return the canvas label ('A4P' | 'A3L') for a template id."""
    return RULES[template].canvas
