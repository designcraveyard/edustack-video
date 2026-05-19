"""Standalone path — build a book directly from existing storyboard keyframes
of a completed video run. Skips Phase B1 (book-plan / gpt-image-2 generation)
and Phase B2 (book-render) entirely. Pipes through fal-ai/birefnet/v2 for
background removal when requested, then writes book/plan.json in the same
shape phase_book_print_prep.py expects.

Why this exists
---------------
Video runs already produce 4–12+ keyframes at <run-dir>/storyboard/keyframes/.
Re-generating those scenes through gpt-image-2 for the book branch (the
default phase_book_plan + phase_book_render flow) is expensive and loses
visual continuity with the video. This script reuses the keyframes verbatim.

Workflow
--------
The skill (skills/book-from-keyframes) walks the user through a chat-driven
page assignment in three steps:
  1. List available keyframes in <run-dir>/storyboard/keyframes/.
  2. Map keyframes -> pages -> templates -> book voice copy.
  3. Write the assignment to <run-dir>/book/from_keyframes.config.json.
This script then:
  1. Reads the config.
  2. For each page, either copies the keyframe to RGBA (no BG removal) or
     runs fal-ai/birefnet/v2 to produce a transparent-BG cutout. Saves to
     <run-dir>/book/pages/page-NN.png.
  3. Writes <run-dir>/book/plan.json in the same shape Phase B3 expects.
  4. Optionally auto-invokes phase_book_print_prep to compose the final
     A4P / A3L canvases at 300 DPI.

Usage
-----
    "$OUTPUT/.venv/bin/python" -m scripts.phase_book_from_keyframes \
        --run-dir <run-dir> [--config <path>] [--run-print-prep]

Config schema (book/from_keyframes.config.json)
-----------------------------------------------
{
  "title": "...",                # optional, copied into plan.json
  "voice": "storybook_narrator", # optional, copied into plan.json
  "pages": [
    {
      "page_no": 1,
      "source_keyframe": "storyboard/keyframes/beat_01.png",  # relative to run-dir
      "template": "split-layout",
      "book_voice_copy": "...",
      "remove_background": true   # default true
    },
    ...
  ]
}
"""
from __future__ import annotations
import argparse
import io
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from PIL import Image

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.paths import RunPaths
from scripts.lib.fal_client import FalClient
from scripts.lib.vps_logger import VPSLogger


def _extract_image_url(result: dict) -> str | None:
    if not isinstance(result, dict):
        return None
    img = result.get("image")
    if isinstance(img, dict) and img.get("url"):
        return img["url"]
    images = result.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict) and first.get("url"):
            return first["url"]
    return result.get("image_url")


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def _to_rgba_copy(src: Path, dst: Path) -> None:
    with Image.open(src) as im:
        im.load()
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        im.save(dst, format="PNG")


def _birefnet_to_rgba(fal: FalClient, src: Path, dst: Path) -> None:
    import fal_client  # type: ignore
    url = fal_client.upload_file(str(src))
    result = fal.birefnet_remove_bg(image_url=url)
    out_url = _extract_image_url(result)
    if not out_url:
        raise RuntimeError(f"birefnet response missing image url: {list(result.keys())}")
    raw = _download(out_url)
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img.save(dst, format="PNG")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--config", default=None,
                    help="Path to from_keyframes.config.json. "
                         "Default: <run-dir>/book/from_keyframes.config.json.")
    ap.add_argument("--run-print-prep", action="store_true",
                    help="After producing book/pages/ and book/plan.json, auto-invoke "
                         "phase_book_print_prep to compose the final canvases.")
    args = ap.parse_args()

    rp = RunPaths(Path(args.run_dir).resolve())
    rp.ensure_dirs()
    run_dir = rp.dir
    cfg = load_config(run_dir.parent.parent)
    state = RunState.load_or_init(run_dir)
    log = VPSLogger(cfg.supabase_url, cfg.supabase_anon, cfg.user_id, run_dir)
    log.heartbeat(state.run_id, "book-from-keyframes", "started")

    config_path = Path(args.config) if args.config else run_dir / "book" / "from_keyframes.config.json"
    if not config_path.exists():
        print(f"[book-from-keyframes] config missing: {config_path}", file=sys.stderr)
        return 2

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"[book-from-keyframes] config parse error: {e}", file=sys.stderr)
        return 2

    pages_cfg = config.get("pages") or []
    if not pages_cfg:
        print("[book-from-keyframes] config has no pages.", file=sys.stderr)
        return 2

    pages_dir = run_dir / "book" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    fal = FalClient(cfg.fal_key, logger=log, run_id=state.run_id)

    plan_pages: list[dict] = []
    n_ok = 0
    n_fail = 0
    for entry in pages_cfg:
        page_no = int(entry["page_no"])
        src_rel = entry["source_keyframe"]
        template = entry["template"]
        copy_text = entry.get("book_voice_copy") or ""
        remove_bg = bool(entry.get("remove_background", True))

        src = (run_dir / src_rel).resolve()
        if not src.is_file():
            print(f"[book-from-keyframes] page {page_no}: source missing: {src}", file=sys.stderr)
            n_fail += 1
            continue

        dst = pages_dir / f"page-{page_no:02d}.png"
        try:
            if remove_bg:
                _birefnet_to_rgba(fal, src, dst)
                method = "birefnet"
            else:
                _to_rgba_copy(src, dst)
                method = "copy"
        except Exception as e:  # noqa: BLE001
            print(f"[book-from-keyframes] page {page_no}: {e}", file=sys.stderr)
            log.log(state.run_id, "book-from-keyframes", "error",
                    f"page {page_no} failed: {e}")
            n_fail += 1
            continue

        plan_pages.append({
            "page_no": page_no,
            "template": template,
            "book_voice_copy": copy_text,
            "source_keyframe": src_rel,
            "method": method,
        })
        n_ok += 1
        print(f"[book-from-keyframes] page {page_no}: {dst.name} via {method}")

    plan = {
        "title": config.get("title") or "",
        "voice": config.get("voice") or "storybook_narrator",
        "origin": "from-keyframes",
        "pages": sorted(plan_pages, key=lambda p: p["page_no"]),
    }
    plan_path = run_dir / "book" / "plan.json"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    log.log(state.run_id, "book-from-keyframes", "info",
            f"pages_ok={n_ok} pages_failed={n_fail} plan={plan_path}")
    state.mark_phase("book-from-keyframes", "pending_review")
    log.heartbeat(state.run_id, "book-from-keyframes", "complete")
    print(f"[book-from-keyframes] {n_ok}/{n_ok + n_fail} pages, plan -> {plan_path}",
          file=sys.stderr)

    if args.run_print_prep and n_ok > 0:
        print("[book-from-keyframes] auto-invoking phase_book_print_prep", file=sys.stderr)
        rc = subprocess.call([
            sys.executable, "-m", "scripts.phase_book_print_prep",
            "--run-dir", str(run_dir),
        ])
        if rc != 0:
            return rc

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
