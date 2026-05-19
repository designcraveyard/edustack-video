"""Phase B2 — book-render.

For each entry in book/plan.json, call fal-ai/gpt-image-2 with the template's
prompt + scene_prompt + reference images. If the output isn't transparent,
route through fal-ai/birefnet/v2. Then run vision QA via fal-ai/any-llm/vision
(Gemini 2.5 Pro). Up to 2 retries with corrective addendum per page.

Bounded: failures don't block the rest of the book — they're reported in
qa.json with status='failed' so the user can regen specific pages via the
/create-book-regen command.
"""
from __future__ import annotations
import argparse
import base64
import io
import json
import mimetypes
import re
import sys
import urllib.request
from pathlib import Path

from PIL import Image

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.paths import RunPaths
from scripts.lib.fal_client import FalClient
from scripts.lib.visual_analyzer import VisualAnalyzer
from scripts.lib.vps_logger import VPSLogger


TRANSPARENT_DIRECTIVE = (
    "\n\nTransparent background. Illustration only. The {text_zone_hint} region must "
    "be left fully transparent — no painted background, no parchment, no light wash. "
    "No text, no letters, no numbers anywhere in the image."
)


def load_templates_md(plugin_root: Path) -> dict[str, str]:
    """Parse skills/book-plan/references/templates.md into {template_id: prompt_pattern}."""
    md_path = plugin_root / "skills" / "book-plan" / "references" / "templates.md"
    md = md_path.read_text(encoding="utf-8")
    # Each template section is delimited by `## N. template-id`
    sections = re.split(r"(?m)^##\s+\d+\.\s*([\w-]+)\s*$", md)
    out: dict[str, str] = {}
    for i in range(1, len(sections), 2):
        name = sections[i].strip()
        body = sections[i + 1]
        m = re.search(r"```(?:text|md)?\n(.+?)\n```", body, re.S)
        if m:
            out[name] = m.group(1).strip()
    return out


def render_prompt(pattern: str, scene_prompt: str, prompt_params: dict, text_zone_hint: str) -> str:
    """Substitute {placeholders} in a template pattern and append the transparent-BG directive."""
    p = pattern
    p = p.replace("{scene_description}", scene_prompt)
    for k, v in (prompt_params or {}).items():
        p = p.replace("{" + k + "}", str(v))
    # Any remaining {placeholders} get a benign default
    p = re.sub(r"\{[^}]+\}", "neutral", p)
    return p + TRANSPARENT_DIRECTIVE.format(text_zone_hint=text_zone_hint or "text zone")


def _download(url: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def _is_transparent_enough(img: Image.Image) -> bool:
    """Border-alpha heuristic: <2% of sampled border pixels with alpha>5 → ok."""
    if img.mode != "RGBA":
        return False
    w, h = img.size
    alpha = img.split()[-1]
    px = alpha.load()
    samples: list[int] = []
    for x in range(0, w, max(1, w // 50)):
        samples.append(px[x, 0])
        samples.append(px[x, h - 1])
    for y in range(0, h, max(1, h // 50)):
        samples.append(px[0, y])
        samples.append(px[w - 1, y])
    if not samples:
        return False
    opaque = sum(1 for v in samples if v > 5)
    return (opaque / len(samples)) < 0.02


def _to_data_url(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _extract_image_url(result: dict) -> str:
    """fal responses for image models normally carry {"images":[{"url":...}]} but a
    few variants ship {"image":{"url":...}} or plain {"url":...}. Handle all three."""
    if isinstance(result, dict):
        if "images" in result and result["images"]:
            return result["images"][0].get("url") or result["images"][0].get("image_url") or ""
        if "image" in result and isinstance(result["image"], dict):
            return result["image"].get("url", "")
        if "url" in result:
            return result["url"]
    raise RuntimeError(f"could not extract image URL from fal response: {result!r}")


def render_one_page(
    page: dict, run_dir: Path, fal: FalClient, analyzer: VisualAnalyzer,
    templates_md: dict[str, str], character_brief: str, max_retries: int = 2,
    art_style: str = "",
) -> dict:
    """Render one book page using the shared layout-gen-style two-image prompter.

    Page entries should carry:
      - template (e.g. "split-layout")
      - scene_prompt (book-voice content description for the page)
      - keyframe_ref (optional, relative to run_dir)
      - character_refs (optional list, relative to run_dir, up to 3)
      - text_zone_hint (optional override for the default text-zone directive)
    """
    from scripts.lib.book_layout_renderer import (
        RenderRequest, render_book_page_payload, template_meta,
    )

    page_no = int(page["page_no"])
    tmpl = page["template"]

    # Resolve content + character ref absolute paths from the run dir.
    content_refs: list[Path] = []
    kf = page.get("keyframe_ref")
    if kf:
        kf_path = run_dir / kf
        if kf_path.exists():
            content_refs.append(kf_path)
    character_refs: list[Path] = []
    for cref in (page.get("character_refs") or [])[:3]:
        cref_path = run_dir / cref
        if cref_path.exists():
            character_refs.append(cref_path)

    req = RenderRequest(
        template=tmpl,
        scene_description=page.get("scene_prompt") or "",
        art_style=art_style or "",
        content_refs=content_refs,
        character_refs=character_refs,
        text_zone_directive=page.get("text_zone_hint") or "",
        bleed_elements=page.get("bleed_elements") or "",
        transparent_bg=True,
    )
    prompt, image_urls, size, meta = render_book_page_payload(req)
    canvas = meta.canvas  # informational; downstream uses page["canvas"] when present

    out_dir = run_dir / "book" / "pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / f"page-{page_no:02d}.png"
    qa_json = out_dir / f"page-{page_no:02d}.qa.json"

    attempt = 0
    last_qa: dict = {}
    addendum = ""
    while attempt <= max_retries:
        try:
            result = fal.gpt_image_2_book_page(
                prompt=(prompt + (("\n\n" + addendum) if addendum else "")),
                image_urls=image_urls or None,
                size=size,
            )
        except Exception as e:  # noqa: BLE001
            last_qa = {"status": "errored", "error": f"fal call: {str(e)[:300]}", "attempts": attempt + 1, "verdict": "NEEDS_REGEN"}
            break

        url = _extract_image_url(result)
        if not url:
            last_qa = {"status": "errored", "error": "no image url in fal response", "attempts": attempt + 1, "verdict": "NEEDS_REGEN"}
            break

        try:
            raw = _download(url)
            img = Image.open(io.BytesIO(raw))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
        except Exception as e:  # noqa: BLE001
            last_qa = {"status": "errored", "error": f"download/decode: {str(e)[:300]}", "attempts": attempt + 1, "verdict": "NEEDS_REGEN"}
            break

        if not _is_transparent_enough(img):
            try:
                br = fal.birefnet_remove_bg(image_url=url)
                br_url = _extract_image_url(br)
                if br_url:
                    img = Image.open(io.BytesIO(_download(br_url))).convert("RGBA")
            except Exception as e:  # noqa: BLE001
                print(f"[book-render] page {page_no}: birefnet fallback failed: {e}", file=sys.stderr)
                # leave img as-is — QA will likely flag it

        img.save(out_png, format="PNG")

        last_qa = analyzer.analyse_book_page(
            image_path=out_png, prompt_used=prompt, character_brief=character_brief,
            page_no=page_no, scene_prompt=page["scene_prompt"],
        )
        if last_qa.get("verdict") == "APPROVED" or last_qa.get("_degraded"):
            break
        addendum = (last_qa.get("corrective_addendum")
                    or "Strictly transparent background and no text in the image.")
        attempt += 1

    last_qa["attempts"] = last_qa.get("attempts", attempt + 1)
    if "status" not in last_qa:
        last_qa["status"] = "ok" if last_qa.get("verdict") == "APPROVED" else "failed"
    qa_json.write_text(json.dumps(last_qa, indent=2), encoding="utf-8")
    return last_qa


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--only-page", type=int, default=0, help="If >0, render only that page_no.")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()

    rp = RunPaths(run_dir)
    rs = RunState.load_or_init(run_dir)
    cfg = load_config(rp.dir.parent.parent)

    plan_path = run_dir / "book" / "plan.json"
    if not plan_path.exists():
        print("[book-render] book/plan.json missing — run phase_book_plan first.", file=sys.stderr)
        return 2

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    pages = plan.get("pages") or []
    # Read art_style from the run's brief so the renderer can echo it in the
    # IMAGE-2-style-fidelity instruction. Standalone book runs may not have a
    # brief.json — empty string is fine, gpt-image-2 still has IMAGE 2 as the
    # style ground truth.
    art_style = ""
    if rp.brief.exists():
        try:
            art_style = (json.loads(rp.brief.read_text()).get("style") or "")
        except Exception:
            pass
    if args.only_page:
        pages = [p for p in pages if int(p["page_no"]) == args.only_page]
        if not pages:
            print(f"[book-render] page {args.only_page} not in plan", file=sys.stderr)
            return 2

    log = VPSLogger(cfg.supabase_url, cfg.supabase_anon, cfg.user_id, rp.dir)
    fal = FalClient(cfg.fal_key, logger=log, run_id=rs.run_id)
    analyzer = VisualAnalyzer(fal_client=fal, logger=log, run_id=rs.run_id)

    plugin_root = Path(__file__).resolve().parent.parent
    templates_md = load_templates_md(plugin_root)

    char_brief = ""
    if rp.description_block.exists():
        char_brief = rp.description_block.read_text(encoding="utf-8")
    elif rp.character_analysis.exists():
        try:
            ana = json.loads(rp.character_analysis.read_text(encoding="utf-8"))
            char_brief = json.dumps(ana.get("characters") or ana, indent=2)
        except Exception:
            char_brief = ""

    results: list[tuple[int, str]] = []
    for page in pages:
        try:
            qa = render_one_page(page, run_dir, fal, analyzer, templates_md, char_brief, art_style=art_style)
            results.append((int(page["page_no"]), qa.get("status", "unknown")))
        except Exception as e:  # noqa: BLE001
            print(f"[book-render] page {page.get('page_no')} failed: {e}", file=sys.stderr)
            results.append((int(page.get("page_no", 0)), "errored"))

    ok = sum(1 for _, s in results if s == "ok")
    print(f"[book-render] rendered {ok}/{len(results)} pages.")
    for pn, st in results:
        print(f"  page {pn:02d}: {st}")

    rs.phases.setdefault("book_render", {})["status"] = "complete" if ok == len(results) else "partial"
    rs.next_phase = "book_print_prep"
    rs.save()
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
