"""Phase 5 — Stitch.

MoviePy + ffmpeg, all local. Reads clip analyses (not raw clips) to plan
transitions and audio mix. VO drives cut points: each beat ends at its last
word's end_ms in vo_timeline, regardless of the clip's natural duration.

Outputs:
  - <run-dir>/stitch_plan.json
  - <run-dir>/final.mp4
  - <run-dir>/final_subtitled.mp4 (if brief.subtitles_enabled)
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.vps_logger import VPSLogger
from scripts.lib.paths import RunPaths
from scripts.make_subtitles import build_srt


TRANSITION_DURATION_S = 0.24


def choose_transition(this_motion: str, next_motion: str | None) -> dict:
    if next_motion is None:
        return {"kind": "fade", "duration_s": 0.3}
    high = {"high"}
    if this_motion in high and next_motion in high:
        return {"kind": "cut", "duration_s": 0.0}
    if this_motion in ("calm", None) or next_motion in ("calm", None):
        return {"kind": "dissolve", "duration_s": TRANSITION_DURATION_S}
    return {"kind": "cut", "duration_s": 0.0}


def _beat_duration_ms(beat: dict) -> int:
    """Return beat duration robustly. Prefer explicit duration_ms; otherwise
    derive from end_ms - start_ms; otherwise default to 5000 (5s)."""
    if isinstance(beat.get("duration_ms"), (int, float)):
        return int(beat["duration_ms"])
    s = beat.get("start_ms")
    e = beat.get("end_ms")
    if isinstance(s, (int, float)) and isinstance(e, (int, float)) and e > s:
        return int(e - s)
    # Accept seconds-shape fallback too.
    s, e = beat.get("start"), beat.get("end")
    if isinstance(s, (int, float)) and isinstance(e, (int, float)) and e > s:
        return int((e - s) * 1000)
    return 5000


def build_plan(rp: RunPaths, brief: dict) -> dict:
    timeline = json.loads(rp.vo_timeline.read_text())
    beats = timeline.get("beats") or []
    analyses: dict[int, dict] = {}
    for p in sorted(rp.clips_dir.glob("clip_*_analysis.json")):
        try:
            bid = int(p.stem.split("_")[1])
            analyses[bid] = json.loads(p.read_text())
        except Exception:
            pass

    plan_clips = []
    for i, b in enumerate(beats):
        # Locate the clip whether it was saved zero-padded or not.
        clip = rp.find_clip(b["id"])
        if not clip:
            continue
        next_motion = (analyses.get(beats[i + 1]["id"]) if i + 1 < len(beats) else {}).get("motion_intensity") if (i + 1) < len(beats) else None
        this_motion = analyses.get(b["id"], {}).get("motion_intensity")
        target_ms = _beat_duration_ms(b)
        plan_clips.append({
            "clip_id": b["id"],
            "src": str(clip),
            "in_ms": 0,
            "out_ms": target_ms,
            "target_ms": target_ms,
            "transition_out": choose_transition(this_motion or "medium", next_motion),
        })

    total_ms = timeline.get("total_duration_ms")
    if not total_ms:
        # Compute from beats if missing.
        total_ms = sum(c["target_ms"] for c in plan_clips) or 0

    return {
        "total_duration_ms": int(total_ms),
        "aspect": brief.get("aspect", "16:9"),
        "clips": plan_clips,
        "audio": {
            "vo": {"src": str(rp.vo_mp3), "level_lufs": -16},
            "clip_mix": {"keep_clip_audio": True, "gain": 0.15,
                         "note": "Each clip's native SFX is mixed under VO at -16dB."},
            "ambient": {"category": brief.get("ambient_category", "none"),
                        "level_lufs": -24, "duck_during_vo": True},
        },
        "subtitles": {
            "enabled": bool(brief.get("subtitles_enabled")),
            "srt": str(rp.srt),
            "burn_in": True,
        },
    }


def _aspect_size(aspect: str) -> tuple[int, int]:
    return {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}.get(aspect, (1920, 1080))


def compose(plan: dict, rp: RunPaths, brief: dict) -> Path:
    """Compose final.mp4 via MoviePy 2.x. Returns the output path.

    Audio mix: native clip audio is preserved and attenuated under the VO so
    individual scene sound effects remain audible. Mix levels are taken from
    plan["audio"]["clip_mix"]["gain"] (default 0.15 = ~-16 dB).
    """
    from moviepy import (VideoFileClip, AudioFileClip, CompositeAudioClip,
                         concatenate_videoclips)

    out_w, out_h = _aspect_size(plan["aspect"])
    target_total_s = plan["total_duration_ms"] / 1000.0
    clip_mix = (plan.get("audio") or {}).get("clip_mix") or {}
    keep_clip_audio = bool(clip_mix.get("keep_clip_audio", True))
    clip_gain = float(clip_mix.get("gain", 0.15))

    video_segments = []
    for c in plan["clips"]:
        # Preserve the clip's native audio — the i2v model often bakes in
        # SFX or ambient that gives each scene its own sonic identity.
        src = VideoFileClip(c["src"])
        if not keep_clip_audio:
            src = src.without_audio()
        target_s = c["target_ms"] / 1000.0
        if abs(src.duration - target_s) / max(target_s, 0.01) > 0.01:
            factor = src.duration / target_s
            src = src.with_speed_scaled(factor)
        src = src.resized(new_size=(out_w, out_h))
        video_segments.append(src)
    if not video_segments:
        raise SystemExit("stitch: no clips to compose")

    video = concatenate_videoclips(video_segments, method="compose")
    if video.duration > target_total_s:
        video = video.subclipped(0, target_total_s)

    # Audio: VO on top, clip audio attenuated underneath.
    audio_tracks = []
    if keep_clip_audio and video.audio is not None:
        try:
            audio_tracks.append(video.audio.with_volume_scaled(clip_gain))
        except AttributeError:
            # Older MoviePy 2.x exposed volumex; try that as a fallback.
            try:
                audio_tracks.append(video.audio.volumex(clip_gain))  # type: ignore[attr-defined]
            except Exception:
                audio_tracks.append(video.audio)
    audio_tracks.append(AudioFileClip(str(rp.vo_mp3)))
    composite_audio = CompositeAudioClip(audio_tracks)
    video = video.with_audio(composite_audio)

    out_path = rp.final
    video.write_videofile(
        str(out_path),
        codec="libx264", audio_codec="aac",
        fps=24, preset="medium", threads=4,
        ffmpeg_params=["-movflags", "+faststart"],
        logger=None,
    )
    return out_path


def _find_default_font(language: str | None) -> str | None:
    """Pick a TTF that's likely to exist on macOS/Linux. Devanagari needs
    Mukta/NotoSansDevanagari; CJK / Tamil need their own fallbacks."""
    import os
    candidates = []
    if language in ("Hindi", "Marathi"):
        candidates += [
            "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
            "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        ]
    elif language == "Tamil":
        candidates += [
            "/System/Library/Fonts/Supplemental/Tamil Sangam MN.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf",
        ]
    elif language == "Bengali":
        candidates += [
            "/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf",
        ]
    candidates += [
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _parse_srt(srt_path: Path) -> list[tuple[float, float, str]]:
    """Return [(start_s, end_s, text), ...]."""
    import re
    text = Path(srt_path).read_text(encoding="utf-8", errors="replace")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        # find timing line
        timing = next((ln for ln in lines if "-->" in ln), None)
        if not timing:
            continue
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", timing)
        if not m:
            continue
        def _t(h, m_, s, ms): return int(h) * 3600 + int(m_) * 60 + int(s) + int(ms) / 1000.0
        start = _t(*m.groups()[:4])
        end = _t(*m.groups()[4:])
        body = " ".join(ln for ln in lines if ln != timing and not ln.strip().isdigit())
        if body:
            cues.append((start, end, body))
    return cues


def add_burn_in(in_video: Path, out_video: Path,
                vo_timeline_path: Path,
                font_name: str | None = None, language: str | None = None,
                highlight_color: tuple[int, int, int] = (255, 220, 80)) -> Path:
    """Burn karaoke-style subtitles via MoviePy + Pillow (no libass dependency).

    Reads word-level timestamps from vo_timeline.json. Words are re-chunked
    into subtitle lines (using the same chunker the SRT writer uses); within
    each line the currently-spoken word is highlighted (color + slight scale).
    """
    from moviepy import VideoFileClip, CompositeVideoClip, ImageClip
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    from scripts.make_subtitles import chunk_words_grouped

    font_path = font_name if (font_name and Path(font_name).is_file()) else _find_default_font(language)
    timeline = json.loads(Path(vo_timeline_path).read_text())
    words = timeline.get("words") or []
    if not words:
        shutil.copyfile(in_video, out_video)
        return out_video

    groups = chunk_words_grouped(words)
    base = VideoFileClip(str(in_video))
    W, H = base.size
    font_size = max(24, int(H * 0.045))
    margin_bottom = int(H * 0.06)
    max_width_px = int(W * 0.85)

    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    def wrap_words(word_texts: list[str]) -> list[list[int]]:
        """Return list of lines, each a list of word INDICES (into word_texts).
        Wrap at max_width_px."""
        scratch = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        lines: list[list[int]] = [[]]
        space_w = scratch.textbbox((0, 0), " ", font=font)[2]
        cur_width = 0
        for i, w in enumerate(word_texts):
            wlen = scratch.textbbox((0, 0), w, font=font)[2]
            extra = wlen + (space_w if lines[-1] else 0)
            if cur_width + extra > max_width_px and lines[-1]:
                lines.append([i])
                cur_width = wlen
            else:
                lines[-1].append(i)
                cur_width += extra
        return lines

    def render_with_highlight(word_texts: list[str], highlight_idx: int | None) -> Image.Image:
        """Render the line block with `highlight_idx` (if not None) drawn in
        accent color. Returns an RGBA Pillow image sized to the text plus
        a translucent background."""
        line_indices = wrap_words(word_texts)
        scratch = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        space_w = scratch.textbbox((0, 0), " ", font=font)[2]
        line_h = font_size + 6

        # Compute block size
        block_w = 0
        for ln in line_indices:
            ln_text = " ".join(word_texts[i] for i in ln)
            bbox = scratch.textbbox((0, 0), ln_text, font=font)
            block_w = max(block_w, bbox[2] - bbox[0])
        block_h = line_h * len(line_indices)
        pad_x, pad_y = 14, 8
        img = Image.new("RGBA", (block_w + pad_x * 2, block_h + pad_y * 2), (0, 0, 0, 170))
        d = ImageDraw.Draw(img)

        for li, ln in enumerate(line_indices):
            ln_text = " ".join(word_texts[i] for i in ln)
            bbox = d.textbbox((0, 0), ln_text, font=font)
            tw = bbox[2] - bbox[0]
            x = (img.width - tw) // 2
            y = pad_y + li * line_h
            for idx_in_line, w_idx in enumerate(ln):
                w_text = word_texts[w_idx]
                # Draw stroke (black outline) for legibility
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    d.text((x + dx, y + dy), w_text, font=font, fill=(0, 0, 0, 255))
                # Fill — accent for highlighted word, else white
                if w_idx == highlight_idx:
                    d.text((x, y), w_text, font=font,
                           fill=(*highlight_color, 255))
                else:
                    d.text((x, y), w_text, font=font, fill=(255, 255, 255, 255))
                w_bbox = d.textbbox((0, 0), w_text, font=font)
                x += (w_bbox[2] - w_bbox[0]) + space_w
        return img

    overlays = []
    for group in groups:
        word_texts = [w["text"] for w in group["words"]]
        group_words = group["words"]
        line_end_s = min(group["end_ms"], int(base.duration * 1000)) / 1000.0
        for i, w in enumerate(group_words):
            start_s = w["start_ms"] / 1000.0
            # Each highlighted state lives until the next word starts (or the
            # group ends, for the last word). This bridges any silent gap.
            if i + 1 < len(group_words):
                end_s = group_words[i + 1]["start_ms"] / 1000.0
            else:
                end_s = line_end_s
            if end_s <= start_s:
                continue
            rgba = render_with_highlight(word_texts, highlight_idx=i)
            arr = np.array(rgba)
            clip = ImageClip(arr, transparent=True) \
                .with_duration(end_s - start_s) \
                .with_start(start_s)
            cw, ch = arr.shape[1], arr.shape[0]
            x = (W - cw) // 2
            y = H - margin_bottom - ch
            clip = clip.with_position((x, y))
            overlays.append(clip)

    composite = CompositeVideoClip([base, *overlays], size=(W, H))
    composite.write_videofile(
        str(out_video),
        codec="libx264", audio_codec="aac",
        fps=base.fps or 24, preset="medium", threads=4,
        ffmpeg_params=["-movflags", "+faststart"],
        logger=None,
    )
    return out_video


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    rp = RunPaths(Path(args.run_dir))
    rp.ensure_dirs()
    cfg = load_config(rp.dir.parent.parent)
    state = RunState.load_or_init(rp.dir)
    log = VPSLogger(cfg.supabase_url, cfg.supabase_anon, cfg.user_id, rp.dir)
    log.heartbeat(state.run_id, "stitch", "started")

    brief = json.loads(rp.brief.read_text())
    plan = build_plan(rp, brief)
    rp.stitch_plan.write_text(json.dumps(plan, indent=2))

    # Subtitles SRT (always written if VO timeline has words)
    timeline = json.loads(rp.vo_timeline.read_text())
    if timeline.get("words"):
        build_srt(timeline["words"], rp.srt)

    final = compose(plan, rp, brief)
    log.log(state.run_id, "stitch", "info", f"wrote {final}")
    if brief.get("subtitles_enabled") and rp.vo_timeline.is_file():
        try:
            add_burn_in(final, rp.final_subtitled,
                        vo_timeline_path=rp.vo_timeline,
                        language=brief.get("language"))
            log.log(state.run_id, "stitch", "info",
                    f"wrote {rp.final_subtitled} (karaoke per-word highlight)")
        except Exception as e:  # noqa: BLE001
            log.log(state.run_id, "stitch", "warn",
                    f"burn-in failed: {e}; SRT still at {rp.srt}")

    state.mark_phase("stitch", "approved")  # last phase auto-completes
    log.heartbeat(state.run_id, "stitch", "complete")
    print(f"[stitch] {final}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
