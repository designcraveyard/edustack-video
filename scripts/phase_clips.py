"""Phase 4 — Clip generation.

Per-beat image-to-video, seeded by each beat's keyframe and timed by
vo_timeline.beats[N].duration_ms. Each clip is generated ONCE and analyzed by
Gemini 2.5 Pro frame-by-frame. Clips are never auto-regenerated; a `major`
verdict is flagged via `needs_review` in summary.json and surfaced at Gate 4
for the user to decide.

Model routing (set in <output>/.config/models.yaml):
  brief.character_mode == "human"  → models.yaml `video_i2v_human` (Wan 2.7, 720p via config)
  brief.character_mode != "human"  → Seedance 1.5 Pro, resolution HARDCODED to 720p

Sequencing: clips are generated strictly sequentially (no parallelism). fal
job ids are persisted to run.json (items.clip_jobs) the instant each clip is
enqueued, so a long-running or interrupted generation can be recovered by
request_id rather than losing the thread.

Dialogue suppression: when `brief.dialogues_enabled` is falsy (default), the
clip prompt explicitly forbids speech / mouth-movement-for-speech. Without
this, Seedance hallucinates Mandarin or random-language dialogue and Wan 2.7
sometimes invents lip-sync motion. Ambient music + SFX still flow through
the stitcher; this only suppresses spoken audio at the clip level.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import textwrap
from pathlib import Path

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.vps_logger import VPSLogger
from scripts.lib.paths import RunPaths
from scripts.lib.fal_client import FalClient
from scripts.lib.visual_analyzer import VisualAnalyzer
from scripts.lib import script_io


DURATION_MIN_S = 3   # lower clamp shared by Seedance + Wan 2.7
DURATION_MAX_S = 10  # upper clamp; stitcher will retime if VO is longer

# Seedance is pinned to 720p in code (see _resolution_for). Per request, this
# is a hard pin — a models.yaml `video_i2v.resolution` override is ignored.
SEEDANCE_MODEL = "fal-ai/bytedance/seedance/v1.5/pro/image-to-video"

# Verbatim — Seedance hallucinates Mandarin dialogue when this is missing,
# and Wan 2.7 occasionally invents lip-sync motion. Inject only when
# brief.dialogues_enabled is falsy (the default).
DIALOGUE_SUPPRESSION = (
    "Audio: ambient and environmental SFX only. No dialogue, no speech, "
    "no voice-over, no humming, no singing. Characters remain silent "
    "throughout the clip — no mouth movement for speech."
)


CLIP_PROMPT = textwrap.dedent("""\
    Animated video clip for an educational explainer. Style: {style}. Aspect: {aspect}.

    BEAT {beat_id} — {label} ({duration_s:.1f}s):
    {narration}
    Visual: {visual}
    {anchors_block}

    CAMERA + MOTION:
    Static medium shot unless the visual hint demands movement. If movement is
    needed, prefer gentle parallax / push-in (≤10% over the whole clip).
    Hold characters' identities and palette identical to the keyframe.

    SPLIT-SCREEN RULE (only if the scene contains a comparison or before/after):
    - 16:9 (horizontal canvas): split VERTICALLY into left | right halves.
    - 9:16 (vertical canvas)  : split HORIZONTALLY into top / bottom halves.
                                NEVER split a 9:16 frame down the middle vertically.
    - 1:1                    : prefer top/bottom.

    SPATIAL ANCHORING (when ANCHORS are listed above):
    - Each anchor names an element, a side (left | right | top | bottom |
      center), and the label that goes WITH it. The element MUST appear on
      the named side from t=0 to t=duration. NEVER swap sides mid-clip.
    - Labels are anchored to their referent. Do not detach a label from
      its element. Do not introduce extra labels.

    CHARACTERS:
    {chars}
    {audio_block}
    Constraints: no text overlays, no captions, no logos, smooth motion, no
    sudden cuts within the clip. NO decorative icons or symbols animating
    into or out of frame unless explicitly listed in the visual hint or
    anchors above. Anything that appears at t=0 should still be present at
    t=duration in the same spatial position (with the camera allowance noted
    above).""")


def _resolve_video_stage(cfg, brief: dict) -> tuple[str, dict]:
    """Pick the i2v model stanza based on character_mode. Returns (model_slug, stanza)."""
    if brief.get("character_mode") == "human":
        stage = cfg.models.get("video_i2v_human") or {}
        model = stage.get("model") or "fal-ai/wan/v2.7/image-to-video"
    else:
        stage = cfg.models.get("video_i2v") or {}
        model = stage.get("model") or SEEDANCE_MODEL
    return model, stage


def _resolution_for(model: str, stage: dict, smoke: bool) -> str:
    if smoke:
        return "720p"
    # Seedance is hard-pinned to 720p regardless of any models.yaml override.
    if model == SEEDANCE_MODEL:
        return "720p"
    return stage.get("resolution") or "1080p"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
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
    dialogues_enabled = bool(brief.get("dialogues_enabled", False))

    # Character descriptions for the clip prompt. Same precedence as
    # storyboard: descriptions.json (verbatim per-character paragraphs from
    # Phase 3a) → description_block.md (none-mode equivalent) → legacy
    # analysis.json reference. Pasting the same verbatim block into every
    # clip prompt is what keeps the model from drifting between clips.
    chars_brief = "(see characters/analysis.json)"
    if rp.character_descriptions.is_file():
        try:
            _desc = json.loads(rp.character_descriptions.read_text(encoding="utf-8"))
            _blocks = [f"{c['name']}: {c['verbatim_description']}"
                       for c in _desc.get("characters", []) if c.get("verbatim_description")]
            if _blocks:
                chars_brief = "\n\n".join(_blocks)
        except Exception:
            pass
    elif character_mode == "none" and rp.description_block.is_file():
        chars_brief = rp.description_block.read_text()

    timeline = json.loads(rp.vo_timeline.read_text())
    beats_by_id = {b["id"]: b for b in timeline.get("beats", [])}

    # Load structured anchors from storyboard.json (one entry per beat may
    # carry an `anchors` list: [{element, side, label}, ...]). When present,
    # phase_clips bakes them into the clip prompt so left/right or top/bottom
    # icons stay anchored — avoids the HERBA/CARNI-swap class of bug.
    storyboard_by_beat: dict[int, dict] = {}
    if rp.storyboard_json.is_file():
        try:
            sb = json.loads(rp.storyboard_json.read_text())
            for e in (sb.get("beats") or []):
                storyboard_by_beat[int(e.get("id"))] = e
        except Exception:
            pass

    def _anchors_block(beat_id: int) -> str:
        entry = storyboard_by_beat.get(beat_id) or {}
        anchors = entry.get("anchors") or []
        if not anchors:
            return ""
        rows = []
        for a in anchors:
            element = a.get("element", "?")
            side = a.get("side", "center")
            label = a.get("label", "")
            label_part = f' (label: "{label}")' if label else ""
            rows.append(f"  - {element} on the {side.upper()} side{label_part}")
        return "ANCHORS (lock these in place for the full clip):\n" + "\n".join(rows)

    audio_block = "" if dialogues_enabled else f"\nAUDIO DIRECTION:\n{DIALOGUE_SUPPRESSION}\n"

    fal = FalClient(cfg.fal_key, logger=log, run_id=state.run_id)
    va = VisualAnalyzer(fal, logger=log, run_id=state.run_id)
    model, stage = _resolve_video_stage(cfg, brief)
    resolution = _resolution_for(model, stage, args.smoke)

    log.log(state.run_id, "clips", "info",
            f"model={model} resolution={resolution} sequential=true "
            f"character_mode={character_mode} dialogues_enabled={dialogues_enabled}")

    target_beats = script.beats[:1] if args.smoke else script.beats

    def _process_beat(b) -> dict | None:
        keyframe = rp.keyframe(b.id)
        if not keyframe.is_file():
            log.log(state.run_id, "clips", "error",
                    f"missing keyframe for beat {b.id}: {keyframe}")
            return None

        tl_beat = beats_by_id.get(b.id) or {}
        target_ms = int(tl_beat.get("duration_ms") or int((b.estimate_seconds or 5) * 1000))
        duration_s = max(DURATION_MIN_S, min(DURATION_MAX_S, math.ceil(target_ms / 1000)))
        if args.smoke:
            duration_s = 4

        clip_path = rp.clip(b.id)
        prompt = CLIP_PROMPT.format(
            style=style, aspect=aspect, beat_id=b.id, label=b.label,
            duration_s=duration_s, narration=b.narration_plain,
            visual=(b.visual or "(none)"), chars=chars_brief,
            anchors_block=_anchors_block(b.id),
            audio_block=audio_block,
        )

        image_url = fal.upload_file(str(keyframe))

        payload = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": duration_s,
            "resolution": resolution,
        }
        # Persist the fal job id the instant the request is enqueued — before
        # the (possibly long) generation wait — so an interrupted run can be
        # recovered by request_id instead of losing the thread.
        captured: dict = {"request_id": None}

        def _on_enqueue(request_id, _bid=b.id) -> None:
            captured["request_id"] = request_id
            state.record_clip_job(_bid, model, request_id, status="enqueued")
            log.log(state.run_id, "clips", "info",
                    f"clip {_bid} enqueued: request_id={request_id}")

        result = fal.run(model, payload, phase="clips", on_enqueue=_on_enqueue)
        video_url = (result.get("video") or {}).get("url") if isinstance(result.get("video"), dict) \
            else result.get("video_url")
        if not video_url:
            state.record_clip_job(b.id, model, captured["request_id"], status="failed")
            raise SystemExit(f"clip response missing video url: {list(result.keys())}")
        fal.download(video_url, str(clip_path))
        state.record_clip_job(b.id, model, captured["request_id"], status="complete")

        validation_prompt_path = rp.clip_validation_prompt(b.id)
        validation_prompt = (
            validation_prompt_path.read_text(encoding="utf-8")
            if validation_prompt_path.is_file() else None
        )
        if validation_prompt:
            log.log(state.run_id, "clips", "info",
                    f"clip {b.id} QA using Claude-authored validation prompt "
                    f"({len(validation_prompt)} chars)")
        ana = va.analyse_clip(
            clip_path, prompt_used=prompt,
            character_brief=chars_brief, clip_id=b.id,
            validation_prompt=validation_prompt,
        )

        needs_review = ana.get("regen_recommendation") == "major"
        if needs_review:
            log.log(state.run_id, "clips", "warn",
                    f"clip {b.id} flagged for review (major drift): "
                    f"{ana.get('corrective_addendum') or 'see analysis'}")

        rp.clip_analysis(b.id).write_text(json.dumps(ana, indent=2))
        return {
            "id": b.id, "clip": str(clip_path),
            "analysis": str(rp.clip_analysis(b.id)),
            "motion": ana.get("motion_intensity"),
            "needs_review": needs_review,
        }

    # Clips are generated strictly sequentially — no parallelism. Beats are
    # processed in order; a failure on one beat aborts the phase (the partial
    # run.json + clips/ on disk preserve progress and job ids for recovery).
    summary: list[dict] = []
    for b in target_beats:
        row = _process_beat(b)
        if row is not None:
            summary.append(row)

    (rp.dir / "clips" / "summary.json").write_text(json.dumps(summary, indent=2))
    log.log(state.run_id, "clips", "info",
            f"clips={len(summary)} needs_review={sum(1 for s in summary if s['needs_review'])}")
    state.mark_phase("clips", "pending_review")
    log.heartbeat(state.run_id, "clips", "complete")
    print(f"[clips] generated {len(summary)} clip(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
