"""Build SRT from vo_timeline.json. Optional burn-in handled by phase_stitch.py.

Subtitle text rule
------------------
VO narration is kept in native script (Devanagari, Tamil, Bengali) so
ElevenLabs phonemizes correctly. Subtitle text, however, is transliterated
to Latin so learners and Hinglish viewers can read it. Transliteration runs
per word inside the chunker so timing alignment to the audio is preserved.

Schema robustness
-----------------
Word objects are accepted in two shapes:
  - canonical:  {text, start_ms, end_ms}
  - seconds:    {text, start, end}   ← some ElevenLabs response variants

`_normalize_word()` upcasts the seconds shape to ms before any chunker runs.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
from scripts.lib.transliterate import to_latin


def _normalize_word(w: dict) -> dict:
    """Accept either {text, start_ms, end_ms} OR {text, start, end} (seconds)
    and return the canonical ms shape."""
    if "start_ms" in w or "end_ms" in w:
        return {
            "text": w.get("text", ""),
            "start_ms": int(w.get("start_ms", 0)),
            "end_ms": int(w.get("end_ms", 0)),
        }
    return {
        "text": w.get("text", ""),
        "start_ms": int(float(w.get("start", 0)) * 1000),
        "end_ms": int(float(w.get("end", 0)) * 1000),
    }


def fmt(ms: int) -> str:
    s, ms = divmod(int(ms), 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunk_words_grouped(words: list[dict],
                         max_words: int = 7,
                         max_duration_ms: int = 3000,
                         min_duration_ms: int = 800) -> list[dict]:
    """Like chunk_words but keeps per-word objects intact — for karaoke burn-in.

    Returns [{start_ms, end_ms, words: [<word dict>, ...]}, ...].
    Word objects passed in are normalized (ms shape) and their `text` is
    transliterated to Latin so the karaoke burn-in shows readable subtitles.
    """
    words = [_normalize_word(w) for w in words]
    # Transliterate the display text per word; preserve timing.
    for w in words:
        w["text"] = to_latin(w["text"])

    groups: list[dict] = []
    cur: list[dict] = []
    cur_start: int | None = None
    last_end: int = 0
    for w in words:
        if cur_start is None:
            cur_start = w["start_ms"]
        cur.append(w)
        last_end = w["end_ms"]
        text_done = w["text"].rstrip().endswith((".", "?", "!", ","))
        long_enough = (w["end_ms"] - cur_start) >= max_duration_ms
        if text_done or len(cur) >= max_words or long_enough:
            groups.append({"start_ms": cur_start, "end_ms": last_end, "words": cur})
            cur, cur_start = [], None
    if cur and cur_start is not None:
        groups.append({"start_ms": cur_start, "end_ms": last_end, "words": cur})
    if len(groups) >= 2 and (groups[-1]["end_ms"] - groups[-1]["start_ms"]) < min_duration_ms:
        tail = groups.pop()
        groups[-1]["words"].extend(tail["words"])
        groups[-1]["end_ms"] = tail["end_ms"]
    return groups


def chunk_words(words: list[dict],
                max_words: int = 7,
                max_duration_ms: int = 3000,
                min_duration_ms: int = 800) -> list[tuple[int, int, str]]:
    words = [_normalize_word(w) for w in words]
    lines: list[tuple[int, int, str]] = []
    buf: list[str] = []
    buf_start: int | None = None
    last_end: int = 0
    for w in words:
        # Transliterate per word so timing stays aligned.
        text = to_latin(w["text"])
        if buf_start is None:
            buf_start = w["start_ms"]
        buf.append(text)
        last_end = w["end_ms"]
        text_done = text.rstrip().endswith((".", "?", "!", ","))
        long_enough = (w["end_ms"] - buf_start) >= max_duration_ms
        if text_done or len(buf) >= max_words or long_enough:
            lines.append((buf_start, w["end_ms"], " ".join(buf)))
            buf, buf_start = [], None
    if buf and buf_start is not None:
        lines.append((buf_start, last_end, " ".join(buf)))
    if len(lines) >= 2 and (lines[-1][1] - lines[-1][0]) < min_duration_ms:
        ps, pe, pt = lines[-2]
        s, e, t = lines.pop()
        lines[-1] = (ps, e, f"{pt} {t}")
    return lines


def build_srt(words: list[dict], out_path: Path) -> Path:
    lines = chunk_words(words)
    out_lines = []
    for i, (s, e, t) in enumerate(lines, start=1):
        out_lines.append(f"{i}\n{fmt(s)} --> {fmt(e)}\n{t}\n")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(out_lines), encoding="utf-8")
    return Path(out_path)


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
    p = build_srt(words, Path(args.out))
    print(f"[make_subtitles] wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
