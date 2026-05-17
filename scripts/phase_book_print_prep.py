"""Phase B3 — book-print-prep.

Pillow-only. For each book/pages/page-NN.png, look up the template from
book/plan.json, call book_canvas.compose() to get an RGBA A4P (2480x3508) or
A3L (4961x3508) canvas at 300 DPI, save it, and emit a sidecar .txt with the
intended book-voice copy.

No external calls. Deterministic. Fast.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from scripts.lib.book_canvas import compose
from scripts.lib.run_state import RunState


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--only-page", type=int, default=0)
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()

    plan_path = run_dir / "book" / "plan.json"
    if not plan_path.exists():
        print("[book-print-prep] book/plan.json missing.", file=sys.stderr)
        return 2
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    src_dir = run_dir / "book" / "pages"
    dst_dir = run_dir / "book" / "print"
    dst_dir.mkdir(parents=True, exist_ok=True)

    n_ok = 0
    n_total = 0
    for page in plan.get("pages") or []:
        page_no = int(page["page_no"])
        if args.only_page and page_no != args.only_page:
            continue
        n_total += 1
        src = src_dir / f"page-{page_no:02d}.png"
        if not src.exists():
            print(f"[book-print-prep] page {page_no}: missing source {src.name}", file=sys.stderr)
            continue
        try:
            with Image.open(src) as im:
                im.load()
                out = compose(im, page["template"])
            dst = dst_dir / f"page-{page_no:02d}.png"
            out.save(dst, format="PNG", dpi=(300, 300))
            sidecar = dst.with_suffix(".txt")
            sidecar.write_text((page.get("book_voice_copy") or "").strip() + "\n", encoding="utf-8")
            n_ok += 1
            print(f"[book-print-prep] page {page_no}: {dst.name} ({out.size[0]}x{out.size[1]})")
        except Exception as e:  # noqa: BLE001
            print(f"[book-print-prep] page {page_no} failed: {e}", file=sys.stderr)

    rs = RunState.load_or_init(run_dir)
    rs.phases.setdefault("book_print_prep", {})["status"] = "complete" if n_ok == n_total else "partial"
    rs.next_phase = "done"
    rs.save()
    print(f"[book-print-prep] done: {n_ok}/{n_total} pages.")
    return 0 if n_ok == n_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
