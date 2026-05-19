"""Video-less book run.

When the user wants a book WITHOUT making a video first. The book skill
(invoked via /create-book) walks the user through:

  1. Topic / class / language / style (mini-brief, saved to brief.json).
  2. Source content — chapter text (paste / file path / URL) AND optional
     reference images (uploaded by the user; saved under <run-dir>/sources/).
  3. Page count (1-12) and templates picked from the 9 (each template's
     ref images are previewable from seed/template-references/).
  4. Book voice and storyboard text per page (drafted by the skill,
     reviewed in chat, saved in book/plan.json).

This script then:
  - Reads <run-dir>/book/plan.json (written by the skill or by the user
    after iteration).
  - For each page, invokes the shared two-image-prompting renderer with
    the picked source-content reference + the template's layout ref +
    any user-uploaded character references.
  - Saves <run-dir>/book/pages/page-NN.png (RGBA, gpt-image-2 native size).
  - With --run-print-prep, auto-invokes phase_book_print_prep for A4P/A3L
    300 DPI canvases.

Differences from phase_book_render.py
-------------------------------------
- phase_book_render.py assumes a finished video run (reads keyframes,
  character sheets, descriptions.json). This script makes none of those
  assumptions — sources are wherever the user puts them, declared in
  plan.json per page.
- No QA loop (no VisualAnalyzer.analyse_book_page). Standalone book runs
  are reviewer-driven via the chat gate, not Gemini-validated.
- Same renderer, same output shape — phase_book_print_prep works on
  either output.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.paths import RunPaths
from scripts.lib.fal_client import FalClient
from scripts.lib.vps_logger import VPSLogger
from scripts.lib.book_layout_renderer import (
    RenderRequest, render_book_page_payload, download_and_open_rgba,
    extract_image_url,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--only-page", type=int, default=0)
    ap.add_argument("--run-print-prep", action="store_true")
    args = ap.parse_args()

    rp = RunPaths(Path(args.run_dir).resolve())
    rp.ensure_dirs()
    run_dir = rp.dir
    cfg = load_config(run_dir.parent.parent)
    state = RunState.load_or_init(run_dir)
    log = VPSLogger(cfg.supabase_url, cfg.supabase_anon, cfg.user_id, run_dir)
    log.heartbeat(state.run_id, "book-standalone", "started")

    plan_path = run_dir / "book" / "plan.json"
    if not plan_path.exists():
        print(f"[book-standalone] book/plan.json missing: {plan_path}", file=sys.stderr)
        return 2
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    pages_cfg = plan.get("pages") or []
    if args.only_page:
        pages_cfg = [p for p in pages_cfg if int(p["page_no"]) == args.only_page]
    if not pages_cfg:
        print("[book-standalone] no pages to render.", file=sys.stderr)
        return 2

    pages_dir = run_dir / "book" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    art_style = plan.get("art_style") or ""
    if not art_style and (run_dir / "brief.json").exists():
        try:
            art_style = json.loads((run_dir / "brief.json").read_text()).get("style") or ""
        except Exception:
            pass

    # Character refs may be paths declared at plan-level (apply to every page)
    # or per-page. Aggregate per call.
    global_char_refs: list[Path] = []
    for p in plan.get("character_refs") or []:
        cp = (run_dir / p).resolve() if not Path(p).is_absolute() else Path(p)
        if cp.exists():
            global_char_refs.append(cp)

    fal = FalClient(cfg.fal_key, logger=log, run_id=state.run_id)
    n_ok = 0
    n_fail = 0
    for entry in pages_cfg:
        page_no = int(entry["page_no"])
        template = entry["template"]
        scene = entry.get("scene_description") or entry.get("book_voice_copy") or ""
        content_refs: list[Path] = []
        for ref in entry.get("content_refs") or []:
            cp = (run_dir / ref).resolve() if not Path(ref).is_absolute() else Path(ref)
            if cp.exists():
                content_refs.append(cp)
        char_refs = list(global_char_refs)
        for cref in entry.get("character_refs") or []:
            cp = (run_dir / cref).resolve() if not Path(cref).is_absolute() else Path(cref)
            if cp.exists() and cp not in char_refs:
                char_refs.append(cp)

        try:
            req = RenderRequest(
                template=template,
                scene_description=scene,
                art_style=art_style,
                content_refs=content_refs,
                character_refs=char_refs,
                transparent_bg=True,
            )
            prompt, image_urls, size, meta = render_book_page_payload(req)
            result = fal.gpt_image_2_book_page(
                prompt=prompt, image_urls=image_urls, size=size,
            )
            url = extract_image_url(result)
            if not url:
                raise RuntimeError(f"no image url in fal response: {list(result.keys())}")
            img = download_and_open_rgba(url)
            dst = pages_dir / f"page-{page_no:02d}.png"
            img.save(dst, format="PNG")
            print(f"[book-standalone] page {page_no}: {dst.name} ({meta.canvas})")
            n_ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[book-standalone] page {page_no} failed: {e}", file=sys.stderr)
            log.log(state.run_id, "book-standalone", "error",
                    f"page {page_no} failed: {e}")
            n_fail += 1

    state.mark_phase("book-standalone", "pending_review")
    log.heartbeat(state.run_id, "book-standalone", "complete")
    print(f"[book-standalone] {n_ok}/{n_ok + n_fail} pages rendered.", file=sys.stderr)

    if args.run_print_prep and n_ok > 0:
        print("[book-standalone] auto-invoking phase_book_print_prep", file=sys.stderr)
        rc = subprocess.call([
            sys.executable, "-m", "scripts.phase_book_print_prep",
            "--run-dir", str(run_dir),
        ])
        if rc != 0:
            return rc

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
