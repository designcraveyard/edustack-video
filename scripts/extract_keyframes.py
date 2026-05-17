"""Slices a multi-panel storyboard PNG into per-beat keyframe PNGs.

Usage:
  python -m scripts.extract_keyframes --panel <run-dir>/storyboard/panel.png \\
         --grid 3x2 --out <run-dir>/storyboard/keyframes \\
         --beats <run-dir>/storyboard/storyboard.json
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
from PIL import Image


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--grid", required=True, help="ROWSxCOLS, e.g. 3x2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--beats", required=False, help="storyboard.json (for output filenames)")
    args = ap.parse_args()

    rows, cols = (int(x) for x in args.grid.split("x"))
    img = Image.open(args.panel)
    w, h = img.size
    cw, ch = w // cols, h // rows
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    beats = []
    if args.beats:
        beats = json.loads(Path(args.beats).read_text()).get("beats", [])

    i = 0
    for r in range(rows):
        for c in range(cols):
            box = (c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)
            crop = img.crop(box)
            beat_id = beats[i]["id"] if i < len(beats) else (i + 1)
            crop.save(out / f"beat_{beat_id:02d}.png")
            i += 1
    print(f"[extract_keyframes] wrote {i} beats to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
