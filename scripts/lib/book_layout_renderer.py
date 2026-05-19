"""Shared book-page renderer used by Phase B2 (the default book branch) and
the `/create-book-from-keyframes` path (the standalone reuse-keyframes path).

Ported from layout-gen's two-image-prompting approach. Three principles:

1. ALWAYS send the layout reference image FIRST. seed/template-references/
   has 1–3 reference images per template; the manifest picks the "best" one
   per template. gpt-image-2 follows visual layout exemplars much better
   than text descriptions alone.

2. Send the source content image SECOND. For from-video runs this is a
   storyboard keyframe; for standalone book runs it's a user-uploaded
   reference image. Up to 2 character-sheet refs may follow, capped at the
   model's 4-image limit.

3. The prompt explicitly names the references: "IMAGE 1 = layout
   reference (use this LAYOUT)" / "IMAGE 2 = content reference (use this
   character & scene CONTENT)". gpt-image-2 disambiguates roles much
   better when references are explicitly named.

Used by:
- scripts/phase_book_render.py — the default book branch's per-page render.
- scripts/phase_book_from_keyframes.py — the keyframe-reuse path.
- scripts/phase_book_standalone.py — the video-less book run.
"""
from __future__ import annotations
import base64
import io
import json
import mimetypes
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PLUGIN_ROOT / "seed" / "template-references" / "manifest.json"


@dataclass
class TemplateMeta:
    template: str
    aspect_ratio: str          # "16:9" | "3:4"
    canvas: str                # "A3L" | "A4P"
    content_type: str          # "narrative" | "educational" | "character-intro" | "process"
    best_ref_path: Path        # absolute path to the layout reference image
    alt_ref_paths: list[Path]


def load_manifest() -> dict[str, Any]:
    """Load and cache the template manifest."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def template_meta(template: str) -> TemplateMeta:
    """Look up canvas + content-type + best-ref absolute path for a template."""
    m = load_manifest()
    t = m["templates"].get(template)
    if not t:
        raise KeyError(
            f"unknown template '{template}'. Valid: {sorted(m['templates'].keys())}"
        )
    base = PLUGIN_ROOT / "seed" / "template-references"
    return TemplateMeta(
        template=template,
        aspect_ratio=t["aspect_ratio"],
        canvas=t["canvas"],
        content_type=t["content_type"],
        best_ref_path=base / t["best_ref"],
        alt_ref_paths=[base / p for p in (t.get("alt_refs") or [])],
    )


def templates_for_content_type(content_type: str) -> list[str]:
    """Decision-framework lookup: which templates fit a given content type."""
    m = load_manifest()
    return m["content_type_to_templates"].get(content_type, [])


def to_data_url(path: Path) -> str:
    """Convert a local image file to a base64 data URL fal can accept inline."""
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


# Two-image prompting wrapper. Wraps a template-specific scene description
# with explicit IMAGE 1 / IMAGE 2 framing and the layout-gen prompting
# principles (named text zone, bleed elements, no-text instruction).
TWO_IMAGE_PROMPT = """\
Two reference images attached.

IMAGE 1 (FIRST) is the LAYOUT REFERENCE — study the spatial composition,
the position of the text zone, the relationship between illustration and
white/light space, the bleed of illustrated elements into the text zone.
Match this layout exactly. Ignore the IMAGE 1 characters, palette, and
style — they are not the subject.

IMAGE 2 (SECOND) is the CONTENT REFERENCE — use these characters, palette,
and art style EXACTLY. The characters' appearance, clothing, colors, and
art style must be carried verbatim into the generated page. Ignore the
IMAGE 2 layout — only borrow content/style.

{character_refs_note}

Generate a children's book page ({aspect_ratio}, {canvas} dimensions) using
LAYOUT from IMAGE 1 and CONTENT/STYLE from IMAGE 2:

{scene_description}

LAYOUT-GEN PRINCIPLES (apply all):
- Match IMAGE 1's text-zone position and proportions. The text zone is
  where book voice copy will be placed LATER by the designer — leave it
  visually quiet (no detailed illustration in the zone).
- {text_zone_directive}
- Bleed elements: have some illustrated elements ({bleed_elements}) extend
  gently from the main illustration into the text zone, creating an
  organic transition. Do not let them fill or clutter the text zone.
- TEXT ZONE FILL: paint the text zone as a SOFT LIGHT AREA in a single
  pale colour appropriate to the scene (light cream, light pastel sky,
  soft warm beige, light grey-white, OR the natural sky / wall / paper
  colour of the scene). The fill must be one quiet flat-to-gradient tone
  — NO checker pattern, NO transparency indicator, NO dappled noise, NO
  busy texture. Think of a sunlit sky or a creamy paper background.
- BACKGROUND: opaque, full-page coverage. Every pixel painted. No
  transparent regions anywhere — the designer overlays text on top of
  this painted page later.

Art-style fidelity: hold IMAGE 2's exact characters, palette, and rendering
style. No style drift. If IMAGE 2 is photoreal, the page is photoreal. If
IMAGE 2 is 2D animated, the page is 2D animated.

ABSOLUTE: No text, no words, no letters, no numbers, no captions, no
labels anywhere in the image. No checker pattern. No grid pattern. The
page is illustration-only — text is added later by the designer.
"""


@dataclass
class RenderRequest:
    """Inputs to render_book_page.

    `content_refs` is the source content (keyframes, user-uploaded scene refs).
    `character_refs` is character sheets / consistency anchors.

    The renderer always prepends the LAYOUT REFERENCE from the template's
    manifest entry, so the final image_urls order is:
        [layout_ref, content_ref[0], content_ref[1?], character_ref[0?], ...]
    capped at the gpt-image-2 4-image limit.
    """
    template: str                   # one of the 9 ids
    scene_description: str          # what to show in the page — e.g., a beat narration adapted into book voice copy
    art_style: str                  # brief.style ("Pixar", "2D animated", "watercolour", etc.)
    content_refs: list[Path]        # source content images; will be data-URL'd
    character_refs: list[Path]      # optional character sheets / refs; will be data-URL'd
    text_zone_directive: str = ""   # template-specific text-zone language. Auto-filled if empty.
    bleed_elements: str = ""        # template-specific bleed elements. Auto-filled if empty.
    # Note: transparent backgrounds are off by default since 0.6.2 — gpt-image-2
    # paints a literal checker pattern when asked to "leave transparent". The
    # text zone is painted as a soft light area instead and book_canvas.compose()
    # flattens any residual alpha onto solid white at print time.
    transparent_bg: bool = False


_DEFAULT_TEXT_ZONE_DIRECTIVE = {
    "full-bleed-with-text-zone": "The RIGHT 35–40% of the page is the text zone — lighter, simpler, lower visual density than the rest. The sky or background opens up there.",
    "vignette-on-page": "The TOP 40–45% of the page is the text zone — pure white space, no illustration. The vignette illustration sits at the BOTTOM-CENTER.",
    "split-layout": "The page is split vertically. The LEFT 55% holds the illustration. The RIGHT 40% is the text zone — quiet, low visual density.",
    "scattered-spots": "Multiple small sticker-like illustration spots on a white background. The text zones are the gaps between the spots — keep ~50% of the page as quiet white space.",
    "full-spread-no-text": "No dedicated text zone — this is a full-bleed dramatic spread. The whole page is illustration.",
    "illustrated-border": "The illustration forms a frame around the page. The CENTER 60% is the text zone — quiet, low visual density.",
    "character-text-pocket": "A character's pose creates negative space (e.g., a C-shape, an arc). The negative space is the text zone — keep it visually quiet.",
    "connected-infographic": "A single connected labeled diagram. Leave clean white space around each labeled element so labels can be added later.",
    "spread-scene-plus-spots": "The LEFT half is a full-bleed scene. The RIGHT half has 3–5 scattered illustrated spots on white. Text zones are the gaps on the right.",
}

_DEFAULT_BLEED_ELEMENTS = {
    "full-bleed-with-text-zone": "leaves, petals, particles, dust motes, soft light rays",
    "vignette-on-page": "small floating elements (flower petals, leaves, sparkles) drifting from the vignette into the white space",
    "split-layout": "leaves, branches, ribbon-like elements extending from the illustration into the text zone",
    "scattered-spots": "no bleed — spots stay self-contained",
    "full-spread-no-text": "no bleed — full-bleed is the whole page",
    "illustrated-border": "tendrils of the border foliage / motifs trailing inward toward the text zone",
    "character-text-pocket": "subtle particles or motifs from the character's environment drifting into the negative space",
    "connected-infographic": "thin connecting lines between elements (these become the diagram's structure)",
    "spread-scene-plus-spots": "small elements from the main scene echoed in the spot illustrations on the right",
}


def build_prompt(req: RenderRequest, meta: TemplateMeta) -> str:
    text_zone = req.text_zone_directive or _DEFAULT_TEXT_ZONE_DIRECTIVE.get(req.template, "Keep the text zone visually quiet.")
    bleed = req.bleed_elements or _DEFAULT_BLEED_ELEMENTS.get(req.template, "no bleed elements")
    character_refs_note = (
        f"IMAGE 3+ (THIRD onward, if attached) are CHARACTER REFERENCE SHEETS. "
        f"Hold every character's appearance EXACTLY as shown on the sheet — "
        f"same face, same clothing, same palette, same proportions. Do not "
        f"redesign any character that appears on these sheets."
        if req.character_refs else ""
    )
    return TWO_IMAGE_PROMPT.format(
        aspect_ratio=meta.aspect_ratio,
        canvas=meta.canvas,
        scene_description=req.scene_description.strip(),
        text_zone_directive=text_zone,
        bleed_elements=bleed,
        character_refs_note=character_refs_note,
    )


def assemble_image_urls(req: RenderRequest, meta: TemplateMeta) -> list[str]:
    """Order: [layout_ref, content_ref[0], ...content_refs..., ...character_refs...]
    Capped at 4 (gpt-image-2 limit)."""
    urls = [to_data_url(meta.best_ref_path)]
    for p in req.content_refs:
        if p and Path(p).exists():
            urls.append(to_data_url(Path(p)))
    for p in req.character_refs:
        if p and Path(p).exists():
            urls.append(to_data_url(Path(p)))
    return urls[:4]


def gpt_image_2_size_for(template: str) -> str:
    """gpt-image-2 size string for a template's canvas.
    A3L (landscape 16:9) → 1456x1024
    A4P (portrait 3:4)   → 1024x1456
    Pillow + book_canvas.compose() then upscales to 300 DPI A4P/A3L (2480x3508 / 4961x3508).
    """
    meta = template_meta(template)
    return "1456x1024" if meta.canvas == "A3L" else "1024x1456"


def render_book_page_payload(req: RenderRequest) -> tuple[str, list[str], str, TemplateMeta]:
    """Build the prompt + image_urls + size string for a single page.

    Returned tuple is what callers pass to fal.gpt_image_2_book_page().
    Kept separate from the actual fal call so phase_book_render can keep
    its retry / QA loop, and the from-keyframes path can keep its lighter
    no-QA loop, but both use the same prompt + image-ordering logic.
    """
    meta = template_meta(req.template)
    prompt = build_prompt(req, meta)
    image_urls = assemble_image_urls(req, meta)
    size = "1456x1024" if meta.canvas == "A3L" else "1024x1456"
    return prompt, image_urls, size, meta


# Convenience helper for callers that want the full call inline.
def render_book_page(req: RenderRequest, fal) -> dict:
    prompt, image_urls, size, meta = render_book_page_payload(req)
    return fal.gpt_image_2_book_page(
        prompt=prompt, image_urls=image_urls, size=size,
    )


def download_and_open_rgba(url: str) -> Image.Image:
    with urllib.request.urlopen(url, timeout=120) as r:
        raw = r.read()
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


def extract_image_url(result: dict) -> str | None:
    """Standard extractor for gpt-image-2 / birefnet responses."""
    if not isinstance(result, dict):
        return None
    if "images" in result and result["images"]:
        first = result["images"][0]
        if isinstance(first, dict):
            return first.get("url") or first.get("image_url")
    if "image" in result and isinstance(result["image"], dict):
        return result["image"].get("url")
    return result.get("image_url") or result.get("url")
