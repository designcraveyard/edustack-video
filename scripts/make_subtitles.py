"""Build SRT from vo_timeline.json. Optional burn-in handled by phase_stitch.py."""
from __future__ import annotations
import argparse
from pathlib import Path
import json


def fmt(ms: int) -> str:
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    tl = json.loads(Path(args.timeline).read_text())
    words = tl.get("words", [])
    if not words:
        Path(args.out).write_text("")
        return 0

    lines: list[tuple[int, int, str]] = []
    buf, buf_start = [], None
    for w in words:
        if buf_start is None:
            buf_start = w["start_ms"]
        buf.append(w["text"])
        ends_chunk = w["text"].endswith((".", "?", "!", ",")) or len(buf) >= 7 or (w["end_ms"] - buf_start) >= 3000
        if ends_chunk:
            lines.append((buf_start, w["end_ms"], " ".join(buf)))
            buf, buf_start = [], None
    if buf:
        lines.append((buf_start, words[-1]["end_ms"], " ".join(buf)))

    out_lines = []
    for i, (s, e, t) in enumerate(lines, start=1):
        out_lines.append(f"{i}\n{fmt(s)} --> {fmt(e)}\n{t}\n")
    Path(args.out).write_text("\n".join(out_lines))
    print(f"[make_subtitles] wrote {len(lines)} cues to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
