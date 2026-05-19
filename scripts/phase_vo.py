"""Phase 2 — Voiceover + vo_timeline.json.

ElevenLabs direct, with word-level timestamps. We strip visual hints from the
script first so they aren't spoken. Beat boundaries are inferred by anchoring
each beat's leading words inside the alignment table.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.vps_logger import VPSLogger
from scripts.lib.paths import RunPaths
from scripts.lib.elevenlabs_client import ElevenLabsClient
from scripts.lib import script_io


def _alignment_to_words(alignment: dict) -> list[dict]:
    """ElevenLabs returns per-character alignment. Re-bucket into words.

    Schema (from EL): {characters: [...], character_start_times_seconds: [...],
                       character_end_times_seconds: [...]}
    """
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    n = min(len(chars), len(starts), len(ends))
    words: list[dict] = []
    buf, w_start = [], None
    for i in range(n):
        c = chars[i]
        if c.isspace() or c in {"\n", "\r", "\t"}:
            if buf:
                words.append({"text": "".join(buf),
                              "start_ms": int((w_start or 0) * 1000),
                              "end_ms": int(ends[i - 1] * 1000)})
                buf, w_start = [], None
            continue
        if not buf:
            w_start = starts[i]
        buf.append(c)
    if buf:
        words.append({"text": "".join(buf),
                      "start_ms": int((w_start or 0) * 1000),
                      "end_ms": int(ends[n - 1] * 1000)})
    return words


_WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)


def _norm(w: str) -> str:
    return re.sub(r"[^\w]+", "", w).lower()


def assign_beats(script: script_io.Script, words: list[dict]) -> list[dict]:
    """Walk through the script beat-by-beat, claiming consecutive words from
    `words` until each beat is satisfied. Order-preserving with normalized
    comparison; non-matches advance the cursor (handles EL occasionally
    swallowing a word or splitting a hyphenated token)."""
    cursor = 0
    beats_out: list[dict] = []
    for b in script.beats:
        tokens = [_norm(t) for t in _WORD_RE.findall(b.narration_plain)]
        if not tokens:
            continue
        start_idx: int | None = None
        end_idx: int = cursor
        ti = 0
        c = cursor
        while c < len(words) and ti < len(tokens):
            cw = _norm(words[c]["text"])
            if cw.startswith(tokens[ti]) or tokens[ti].startswith(cw):
                if start_idx is None:
                    start_idx = c
                end_idx = c
                ti += 1
            c += 1
            if start_idx is not None and c - start_idx > len(tokens) * 4:
                break
        if start_idx is None:
            start_idx = cursor
            end_idx = min(cursor + len(tokens) - 1, len(words) - 1)
        beats_out.append({
            "id": b.id,
            "label": b.label,
            "start_ms": words[start_idx]["start_ms"],
            "end_ms": words[end_idx]["end_ms"],
            "duration_ms": words[end_idx]["end_ms"] - words[start_idx]["start_ms"],
            "word_range": [start_idx, end_idx + 1],
        })
        cursor = end_idx + 1
    return beats_out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    rp = RunPaths(Path(args.run_dir))
    rp.ensure_dirs()
    cfg = load_config(rp.dir.parent.parent)
    state = RunState.load_or_init(rp.dir)
    log = VPSLogger(cfg.supabase_url, cfg.supabase_anon, cfg.user_id, rp.dir)
    log.heartbeat(state.run_id, "vo", "started")

    brief = json.loads(rp.brief.read_text())
    script = script_io.load(rp.script)
    narration = script.narration_text()

    el = ElevenLabsClient(cfg.elevenlabs_key, logger=log, run_id=state.run_id)
    voice_id = brief.get("voice_id") or "21m00Tcm4TlvDq8ikWAM"
    voice_name = brief.get("voice_name") or ""
    output_format = ((cfg.models.get("vo") or {}).get("output_format")) or "mp3_44100_192"

    # eleven_v3 is REQUIRED — audio tags (`[curious]`, `[pause]`, etc.) only
    # work with this model. Older models (multilingual_v2, flash_v2_5) speak
    # the tags literally, which is what produced the "I'm hearing the word
    # curious / pause" regression. We force-override any other value in the
    # user's models.yaml because the failure mode (tag words spoken aloud in
    # the final video) is bad enough to justify ignoring the config.
    configured_model = ((cfg.models.get("vo") or {}).get("model_id")) or "eleven_v3"
    model_id = "eleven_v3"
    if configured_model != model_id:
        log.log(state.run_id, "vo", "warn",
                f"models.yaml vo.model_id={configured_model!r} is not eleven_v3; "
                f"forcing eleven_v3 because audio tags only work with v3. "
                f"Update <output>/.config/models.yaml to silence this warning.")
        print(f"[vo] WARN: configured model_id={configured_model!r} overridden "
              f"to eleven_v3 (audio tags only work with v3)", file=sys.stderr)

    # Persist the audio prompt locally BEFORE the API call, so a failed run still
    # leaves the user with the exact text that was about to be sent.
    rp.audio_dir.mkdir(parents=True, exist_ok=True)
    prompt_txt_path = rp.audio_dir / "full-vo.prompt.txt"
    prompt_meta_path = rp.audio_dir / "full-vo.prompt.json"
    prompt_txt_path.write_text(narration, encoding="utf-8")
    prompt_meta_path.write_text(json.dumps({
        "voice_id": voice_id,
        "voice_name": voice_name,
        "model_id": model_id,
        "output_format": output_format,
        "language": script.language,
        "character_count": len(narration),
        "endpoint": f"/v1/text-to-speech/{voice_id}/with-timestamps",
    }, indent=2))

    result = el.tts_with_timestamps(
        voice_id=voice_id, text=narration,
        model_id=model_id, output_format=output_format,
    )
    el.save_audio(result["audio_mp3"], rp.vo_mp3)

    alignment = result.get("normalized_alignment") or result.get("alignment") or {}
    words = _alignment_to_words(alignment)
    beats = assign_beats(script, words)
    timeline = {
        "total_duration_ms": (words[-1]["end_ms"] if words else 0),
        "voice_id": voice_id,
        "model_id": model_id,
        "language": script.language,
        "words": words,
        "beats": beats,
    }
    rp.vo_timeline.write_text(json.dumps(timeline, indent=2))

    log.log(state.run_id, "vo", "info",
            f"vo={rp.vo_mp3.name} words={len(words)} beats={len(beats)} "
            f"dur={timeline['total_duration_ms']/1000:.1f}s")
    state.mark_phase("vo", "pending_review")
    log.heartbeat(state.run_id, "vo", "complete")
    print(f"[vo] {rp.vo_mp3}  words={len(words)} dur={timeline['total_duration_ms']/1000:.1f}s",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
