"""Phase 4 — Clip generation.

Seedance 1.5 Pro image-to-video per beat, seeded by its keyframe, timed by
vo_timeline.beats[N].duration_ms. Each clip is analyzed by Gemini 2.5 Pro
frame-by-frame; up to 2 auto-corrective regens before escalating to Gate 4.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import textwrap
from pathlib import Path
from typing import Any

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.vps_logger import VPSLogger
from scripts.lib.paths import RunPaths
from scripts.lib.fal_client import FalClient
from scripts.lib.visual_analyzer import VisualAnalyzer
from scripts.lib import script_io


AUTO_RETRY_BUDGET = 2
SEEDANCE_MIN_S = 3   # the model's lower bound; we clamp short beats up
SEEDANCE_MAX_S = 10  # and clamp long beats down (stitcher will retime)


CLIP_PROMPT = textwrap.dedent("""\
    Animated video clip for an educational explainer. Style: {style}. Aspect: {aspect}.

    BEAT {beat_id} — {label} ({duration_s:.1f}s):
    {narration}
    Visual: {visual}

    CAMERA + MOTION:
    Static medium shot unless the visual hint demands movement. If movement is
    needed, prefer gentle parallax / push-in (≤10% over the whole clip).
    Hold characters' identities and palette identical to the keyframe.

    SPLIT-SCREEN RULE (only if the scene contains a comparison or before/after):
    - 16:9 (horizontal canvas): split VERTICALLY into left | right halves.
    - 9:16 (vertical canvas)  : split HORIZONTALLY into top / bottom halves.
                                NEVER split a 9:16 frame down the middle vertically.
    - 1:1                    : prefer top/bottom.

    CHARACTERS:
    {chars}

    Constraints: no text overlays, no captions, no logos, smooth motion, no
    sudden cuts within the clip.""")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--auto-retries", type=int, default=AUTO_RETRY_BUDGET)
    ap.add_argument("--smoke", action="store_true",
                    help="Limit to one short clip at low res (for end-to-end smoke).")
    args = ap.parse_args()
    rp = RunPaths(Path(args.run_dir))
    rp.ensure_dirs()
    cfg = load_config(rp.dir.parent.parent)
    state = RunState.load_or_init(rp.dir)
    log = VPSLogger(cfg.supabase_url, cfg.supabase_anon, cfg.user_id, rp.dir)
    log.heartbeat(state.run_id, "clips", "started")

    brief = json.loads(rp.brief.read_text())
    script = script_io.load(rp.script)
    aspect = brief.get("aspect", "16:9")
    style = brief.get("style", "2D Flat")
    character_mode = brief.get("character_mode", "abstract")
    chars_brief = (rp.description_block.read_text() if (character_mode == "none" and rp.description_block.is_file())
                   else "(see characters/analysis.json)")

    timeline = json.loads(rp.vo_timeline.read_text())
    beats_by_id = {b["id"]: b for b in timeline.get("beats", [])}

    fal = FalClient(cfg.fal_key, logger=log, run_id=state.run_id)
    va = VisualAnalyzer(fal, logger=log, run_id=state.run_id)
    model = (cfg.models.get("video_i2v") or {}).get("model") \
        or "fal-ai/bytedance/seedance/v1.5/pro/image-to-video"

    target_beats = script.beats[:1] if args.smoke else script.beats
    summary: list[dict] = []
    for b in target_beats:
        keyframe = rp.keyframe(b.id)
        if not keyframe.is_file():
            log.log(state.run_id, "clips", "error",
                    f"missing keyframe for beat {b.id}: {keyframe}")
            continue

        tl_beat = beats_by_id.get(b.id) or {}
        target_ms = int(tl_beat.get("duration_ms") or int((b.estimate_seconds or 5) * 1000))
        duration_s = max(SEEDANCE_MIN_S, min(SEEDANCE_MAX_S, math.ceil(target_ms / 1000)))
        if args.smoke:
            duration_s = 4  # small live test

        attempt = 0
        addendum = ""
        ana: dict[str, Any] = {}
        clip_path = rp.clip(b.id)
        while attempt <= args.auto_retries:
            prompt = CLIP_PROMPT.format(
                style=style, aspect=aspect, beat_id=b.id, label=b.label,
                duration_s=duration_s, narration=b.narration_plain,
                visual=(b.visual or "(none)"), chars=chars_brief,
            )
            if addendum:
                prompt += f"\n\nADDITIONAL GUIDANCE (regen):\n{addendum}"

            # upload local keyframe to fal so the i2v model can fetch it
            import fal_client  # type: ignore
            image_url = fal_client.upload_file(str(keyframe))

            payload = {
                "prompt": prompt,
                "image_url": image_url,
                "duration": duration_s,
                "resolution": "720p" if args.smoke else "1080p",
            }
            result = fal.run(model, payload, phase="clips")
            video_url = (result.get("video") or {}).get("url") if isinstance(result.get("video"), dict) \
                else result.get("video_url")
            if not video_url:
                raise SystemExit(f"clip response missing video url: {list(result.keys())}")
            fal.download(video_url, str(clip_path))

            ana = va.analyse_clip(clip_path, prompt_used=prompt,
                                  character_brief=chars_brief, clip_id=b.id)
            if ana.get("regen_recommendation") in (None, "minor"):
                break
            addendum = ana.get("corrective_addendum") or "Improve character consistency and reduce drift."
            log.log(state.run_id, "clips", "warn",
                    f"clip {b.id} auto-regen attempt {attempt+1}: {addendum}")
            attempt += 1

        rp.clip_analysis(b.id).write_text(json.dumps(ana, indent=2))
        summary.append({
            "id": b.id, "clip": str(clip_path),
            "analysis": str(rp.clip_analysis(b.id)),
            "motion": ana.get("motion_intensity"),
            "needs_review": ana.get("regen_recommendation") == "major",
        })

    (rp.dir / "clips" / "summary.json").write_text(json.dumps(summary, indent=2))
    log.log(state.run_id, "clips", "info",
            f"clips={len(summary)} needs_review={sum(1 for s in summary if s['needs_review'])}")
    state.mark_phase("clips", "pending_review")
    log.heartbeat(state.run_id, "clips", "complete")
    print(f"[clips] generated {len(summary)} clip(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
