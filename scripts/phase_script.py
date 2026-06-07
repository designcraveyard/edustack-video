"""Phase 1 — Script writing.

⚠️ LEGACY — NOT INVOKED. The live Phase 1 is the Claude-authored `script-writer`
skill (skills/script-writer/SKILL.md): Claude writes `script.md` directly (rich
Strategy/Cast/Sound/Scene-Timeline + tagged, native-script Beats). No skill or
command runs this module — unlike phase_clips / phase_characters / phase_book_*,
whose SKILL.md explicitly invoke `python -m scripts.phase_*`. Behaviour changes
to script CONTENT (language/Devanagari rules, tag density, structure) belong in
the SKILL.md, NOT here — edits to this file will not run. Kept for reference and
as a possible future deterministic path.

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


DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
TAMIL_RE      = re.compile(r"[஀-௿]")
BENGALI_RE    = re.compile(r"[ঀ-৿]")


def warn_script_mismatch(text: str, language: str, log) -> None:
    """word_to_word mode preserves the chapter verbatim — we can only warn if
    the source isn't in the script ElevenLabs needs for correct phonemes."""
    expected = {"Hindi": DEVANAGARI_RE, "Hinglish": DEVANAGARI_RE,
                "Marathi": DEVANAGARI_RE, "Tamil": TAMIL_RE, "Bengali": BENGALI_RE}.get(language)
    if not expected:
        return
    if not expected.search(text):
        log.log(getattr(log, "run_id", ""), "script", "warn",
                f"word_to_word source for language={language} contains no native-script "
                f"characters. ElevenLabs will likely mispronounce with English phonemes. "
                f"Re-source the chapter in native script or switch to script_mode=standard.")


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

    DURATION + WORD BUDGET — read carefully, this is the #1 reason runs fail.
    The TTS engine will not speed up to fit a too-long script. You must size
    the narration to the target word budget given to you in the user message:
      - Sum of beat `seconds` MUST equal target_duration_seconds within ±10%.
      - TOTAL word count across all `narration` fields MUST NOT exceed
        WORD_BUDGET. Going over means VO will overrun the timeline and
        clips will be retimed-up at stitch, degrading quality.
      - If a topic genuinely needs more, REDUCE the number of beats or
        shorten the recap — do not exceed the budget.

    Use class-appropriate vocabulary; do not introduce a term before defining it visually.

    SCRIPT (NARRATION) MUST BE IN NATIVE SCRIPT — this is non-negotiable because
    ElevenLabs phonemizes based on what is written, and Roman characters get
    pronounced with English phonemes:
      - language="Hindi"     → entire narration in Devanagari (देवनागरी).
                               Romanised Hindi like "yaar suno" is forbidden.
      - language="Hinglish"  → write Hindi words in Devanagari and English
                               LOANWORDS ALSO in Devanagari (transliterated):
                               "फोटोसिंथेसिस एक प्रोसेस है" — NOT
                               "photosynthesis ek process hai".
                               No Latin characters anywhere in narration.
      - language="Marathi"   → Devanagari.
      - language="Tamil"     → Tamil script (தமிழ்).
      - language="Bengali"   → Bengali script (বাংলা).
      - language="English"   → Latin/Roman script.
    `visual` (the hint comment) and `label` may stay in English in all cases —
    they aren't spoken, only the `narration` strings are.
""")


def build_standard(brief: dict, fal: FalClient) -> script_io.Script:
    target = int(brief.get("duration_seconds") or 60)
    lang = brief.get("language", "English")
    level = int(brief.get("class_level") or 6)
    style = brief.get("style", "2D Flat")
    topic = brief["topic"]
    wpm = WORDS_PER_SECOND.get(lang, 2.5)
    word_budget = int(target * wpm)

    user = textwrap.dedent(f"""\
        TOPIC: {topic}
        TARGET DURATION: {target} seconds
        WORD_BUDGET: {word_budget} words (computed as target × {wpm} words/sec for {lang})
        CLASS LEVEL: {level}
        LANGUAGE: {lang}
        STYLE (visual): {style}
        NOTES: {brief.get('notes') or '(none)'}

        Return STRICT JSON only — no markdown fences, no prose. Five to seven beats.
        Stay AT OR UNDER {word_budget} words total across all narration combined.""")
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

    # Post-generation word-count budget check (warn-only per user policy —
    # no auto-trim). Catches the case where Gemini ignores the WORD_BUDGET
    # hint and produces a script that will overrun the VO timeline.
    target_sec = brief.get("duration_seconds")
    if target_sec and script.mode == "standard":
        wpm = WORDS_PER_SECOND.get(script.language, 2.5)
        budget = int(target_sec * wpm)
        actual_words = sum(
            len(re.findall(r"\b[\w'-]+\b", b.narration_plain)) for b in script.beats
        )
        overrun_pct = (actual_words - budget) / budget * 100 if budget else 0
        if overrun_pct > 10:
            log.log(state.run_id, "script", "warn",
                    f"word-budget overrun: {actual_words} words vs budget {budget} "
                    f"({overrun_pct:+.1f}%). VO at {script.language} (~{wpm} wpm) will "
                    f"exceed the {target_sec}s target. Consider /create-video-regen "
                    f"script with a shorter target.")
        elif overrun_pct < -25:
            log.log(state.run_id, "script", "warn",
                    f"word-budget undershoot: {actual_words} words vs budget {budget} "
                    f"({overrun_pct:+.1f}%). Script may be too sparse for the target duration.")
        else:
            log.log(state.run_id, "script", "info",
                    f"word-budget OK: {actual_words} words vs budget {budget} ({overrun_pct:+.1f}%)")

    script_io.dump(script, rp.script)
    log.log(state.run_id, "script", "info",
            f"wrote {rp.script} beats={len(script.beats)} dur≈{script.duration_estimate_seconds:.0f}s")
    state.mark_phase("script", "pending_review")
    log.heartbeat(state.run_id, "script", "complete")
    print(f"[script] {rp.script}  beats={len(script.beats)}  dur≈{script.duration_estimate_seconds:.0f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
