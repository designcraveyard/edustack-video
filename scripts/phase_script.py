"""Phase 1 — Script writing.

Two modes:
- `standard`: produces a structured beat-format script via Gemini (fal-ai/any-llm
  with google/gemini-2.5-pro) sized for `brief.duration_seconds`.
- `word_to_word`: reads `source/chapter.*` (PDF / text / URL stash), normalizes
  it, and emits a verbatim script. `duration_seconds` is ignored — duration is
  derived from VO in Phase 2.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import textwrap
from dataclasses import asdict
from pathlib import Path

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.vps_logger import VPSLogger
from scripts.lib.paths import RunPaths
from scripts.lib.fal_client import FalClient
from scripts.lib import script_io


# ----- chapter source readers -----
def _read_pdf(p: Path) -> str:
    from pypdf import PdfReader
    pages = []
    for page in PdfReader(str(p)).pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n\n".join(pages)


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _read_url(url: str) -> str:
    import httpx
    r = httpx.get(url, timeout=30.0, follow_redirects=True)
    r.raise_for_status()
    return r.text


def load_chapter_source(rp: RunPaths, brief: dict) -> str:
    cs = brief.get("chapter_source") or {}
    kind = cs.get("kind")
    ref = cs.get("ref")
    if not kind or not ref:
        # Fall back to scanning source/
        candidates = list(rp.source_dir.glob("chapter.*"))
        if not candidates:
            raise SystemExit("word_to_word mode requires brief.chapter_source or a file at source/chapter.*")
        p = candidates[0]
        return _read_pdf(p) if p.suffix.lower() == ".pdf" else _read_text(p)

    if kind == "text":
        return ref
    if kind == "url":
        return _read_url(ref)
    if kind == "file":
        # Brief UI saves uploads to source/chapter.<ext>; ref is the basename
        candidates = list(rp.source_dir.glob("chapter.*"))
        if not candidates:
            # Maybe the ref itself is an absolute path
            p = Path(ref)
            if p.is_file():
                candidates = [p]
        if not candidates:
            raise SystemExit(f"word_to_word: chapter file not found (ref={ref})")
        p = candidates[0]
        return _read_pdf(p) if p.suffix.lower() == ".pdf" else _read_text(p)
    raise SystemExit(f"unknown chapter_source.kind: {kind}")


# ----- script construction -----
WORDS_PER_SECOND = {"English": 2.5, "Hindi": 2.2, "Hinglish": 2.4,
                    "Tamil": 2.0, "Bengali": 2.1, "Marathi": 2.1}


def estimate_seconds(text: str, language: str = "English") -> float:
    wps = WORDS_PER_SECOND.get(language, 2.5)
    n = len(re.findall(r"\b[\w'-]+\b", text))
    return round(n / wps, 1)


def build_word_to_word(brief: dict, raw_text: str) -> script_io.Script:
    # Normalize whitespace
    text = re.sub(r"\r\n?", "\n", raw_text)
    text = re.sub(r"[ \t]+", " ", text)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if not paragraphs:
        raise SystemExit("word_to_word: chapter has no text after normalization")
    beats: list[script_io.Beat] = []
    for i, para in enumerate(paragraphs, start=1):
        # Strip stray header glyphs / page numbers
        para = re.sub(r"^\s*(\d+)\s*$", "", para).strip()
        if not para:
            continue
        beats.append(script_io.Beat(
            id=len(beats) + 1,
            label="paragraph",
            estimate_seconds=estimate_seconds(para, brief.get("language", "English")),
            narration=para,
        ))
    title = (paragraphs[0][:80] or "Chapter").strip().replace("\n", " ")
    return script_io.Script(
        title=title,
        duration_estimate_seconds=sum(b.estimate_seconds or 0 for b in beats),
        mode="word_to_word",
        class_level=int(brief.get("class_level") or 6),
        language=brief.get("language", "English"),
        beats=beats,
    )


STANDARD_SYSTEM = textwrap.dedent("""\
    You are a senior educational scriptwriter for short explainer videos.
    Strict output format: JSON with keys {title, beats:[{id,label,seconds,narration,visual}]}.
    Beat labels are short tags (hook/setup/mechanism/consequence/recap).
    Each beat is ONE concept, animatable, with verbs and concrete nouns.
    Sum of seconds must equal the target duration within ±10%.
    Use class-appropriate vocabulary; do not introduce a term before defining it visually.
    Hindi/Tamil/Bengali/Marathi/Hinglish output should use native script when the language is set to that.
""")


def build_standard(brief: dict, fal: FalClient) -> script_io.Script:
    target = int(brief.get("duration_seconds") or 60)
    lang = brief.get("language", "English")
    level = int(brief.get("class_level") or 6)
    style = brief.get("style", "2D Flat")
    topic = brief["topic"]

    user = textwrap.dedent(f"""\
        TOPIC: {topic}
        TARGET DURATION: {target} seconds
        CLASS LEVEL: {level}
        LANGUAGE: {lang}
        STYLE (visual): {style}
        NOTES: {brief.get('notes') or '(none)'}

        Return STRICT JSON only — no markdown fences, no prose. Five to seven beats.""")
    out = fal.any_llm(
        "google/gemini-2.5-pro",
        prompt=user, system_prompt=STANDARD_SYSTEM, phase="script",
    )
    text = (out or {}).get("output") or (out or {}).get("text") or ""
    if not text and isinstance(out, dict):
        ch = (out.get("choices") or [{}])[0]
        text = ((ch.get("message") or {}).get("content")) or ""
    # Lenient JSON extract
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    data = json.loads(m.group(0)) if m else {}
    raw_beats = data.get("beats") or []
    beats: list[script_io.Beat] = []
    for i, b in enumerate(raw_beats, start=1):
        beats.append(script_io.Beat(
            id=int(b.get("id") or i),
            label=str(b.get("label") or "beat"),
            estimate_seconds=float(b.get("seconds") or estimate_seconds(b.get("narration") or "", lang)),
            narration=str(b.get("narration") or "").strip(),
            visual=str(b.get("visual") or "").strip() or None,
        ))
    if not beats:
        raise SystemExit("script generation returned no beats")
    return script_io.Script(
        title=str(data.get("title") or topic),
        duration_estimate_seconds=sum(b.estimate_seconds or 0 for b in beats),
        mode="standard",
        class_level=level,
        language=lang,
        beats=beats,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    rp = RunPaths(Path(args.run_dir))
    rp.ensure_dirs()
    cfg = load_config(rp.dir.parent.parent)
    state = RunState.load_or_init(rp.dir)
    log = VPSLogger(cfg.supabase_url, cfg.supabase_anon, cfg.user_id, rp.dir)
    log.heartbeat(state.run_id, "script", "started")

    brief = json.loads(rp.brief.read_text())
    mode = brief.get("script_mode", "standard")
    log.log(state.run_id, "script", "info", f"mode={mode} lang={brief.get('language')}")

    if mode == "word_to_word":
        chapter = load_chapter_source(rp, brief)
        script = build_word_to_word(brief, chapter)
    else:
        fal = FalClient(cfg.fal_key, logger=log, run_id=state.run_id)
        script = build_standard(brief, fal)

    script_io.dump(script, rp.script)
    log.log(state.run_id, "script", "info",
            f"wrote {rp.script} beats={len(script.beats)} dur≈{script.duration_estimate_seconds:.0f}s")
    state.mark_phase("script", "pending_review")
    log.heartbeat(state.run_id, "script", "complete")
    print(f"[script] {rp.script}  beats={len(script.beats)}  dur≈{script.duration_estimate_seconds:.0f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
