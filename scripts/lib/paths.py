"""Run-dir path conventions in one place. Every phase script imports from here.

A "run" is a directory under <output>/runs/. The directory is the single
unit of work — losing it loses the run; copying it preserves the run.
"""
from __future__ import annotations
from pathlib import Path


class RunPaths:
    def __init__(self, run_dir: Path):
        self.dir = Path(run_dir).resolve()

    # top-level
    @property
    def brief(self) -> Path: return self.dir / "brief.json"
    @property
    def state(self) -> Path: return self.dir / "run.json"
    @property
    def script(self) -> Path: return self.dir / "script.md"
    @property
    def stitch_plan(self) -> Path: return self.dir / "stitch_plan.json"
    @property
    def final(self) -> Path: return self.dir / "final.mp4"
    @property
    def final_subtitled(self) -> Path: return self.dir / "final_subtitled.mp4"

    # subdirs
    @property
    def source_dir(self) -> Path: return self.dir / "source"
    @property
    def logs_dir(self) -> Path: return self.dir / "logs"
    @property
    def prompts_dir(self) -> Path: return self.dir / "prompts"
    @property
    def audio_dir(self) -> Path: return self.dir / "audio"
    @property
    def characters_dir(self) -> Path: return self.dir / "characters"
    @property
    def storyboard_dir(self) -> Path: return self.dir / "storyboard"
    @property
    def keyframes_dir(self) -> Path: return self.storyboard_dir / "keyframes"
    @property
    def analysis_dir(self) -> Path: return self.storyboard_dir / "analysis"
    @property
    def clips_dir(self) -> Path: return self.dir / "clips"

    # files
    @property
    def vo_mp3(self) -> Path: return self.audio_dir / "full-vo.mp3"
    @property
    def vo_timeline(self) -> Path: return self.audio_dir / "vo_timeline.json"
    @property
    def srt(self) -> Path: return self.audio_dir / "subtitles.srt"
    @property
    def character_sheet(self) -> Path: return self.characters_dir / "sheet.png"
    @property
    def character_analysis(self) -> Path: return self.characters_dir / "analysis.json"
    @property
    def character_prompt(self) -> Path: return self.characters_dir / "sheet_prompt.md"
    @property
    def character_descriptions(self) -> Path: return self.characters_dir / "descriptions.json"
    @property
    def description_block(self) -> Path: return self.characters_dir / "description_block.md"
    @property
    def storyboard_json(self) -> Path: return self.storyboard_dir / "storyboard.json"
    @property
    def panel_png(self) -> Path: return self.storyboard_dir / "panel.png"

    def keyframe(self, beat_id: int) -> Path:
        return self.keyframes_dir / f"beat_{beat_id:02d}.png"

    def keyframe_analysis(self, beat_id: int) -> Path:
        return self.analysis_dir / f"beat_{beat_id:02d}.json"

    def clip(self, clip_id: int) -> Path:
        """Canonical zero-padded clip path."""
        return self.clips_dir / f"clip_{clip_id:02d}.mp4"

    def find_clip(self, clip_id: int) -> Path | None:
        """Locate a clip on disk whether it was saved zero-padded
        (`clip_01.mp4`, canonical) or non-padded (`clip_1.mp4`, occasionally
        produced by ad-hoc orchestration). Returns the first existing path
        or None.
        """
        candidates = [
            self.clips_dir / f"clip_{clip_id:02d}.mp4",
            self.clips_dir / f"clip_{clip_id}.mp4",
        ]
        for p in candidates:
            if p.is_file():
                return p
        return None

    def clip_analysis(self, clip_id: int) -> Path:
        return self.clips_dir / f"clip_{clip_id:02d}_analysis.json"

    def clip_validation_prompt(self, clip_id: int) -> Path:
        """Claude-authored, per-clip frame-by-frame validation prompt. Read by
        phase_clips and passed verbatim to visual_analyzer.analyse_clip. When
        missing, analyse_clip falls back to a generic template."""
        return self.clips_dir / f"clip_{clip_id:02d}.validation.txt"

    def ensure_dirs(self) -> None:
        for d in (self.logs_dir, self.prompts_dir, self.audio_dir,
                  self.characters_dir, self.storyboard_dir, self.keyframes_dir,
                  self.analysis_dir, self.clips_dir, self.source_dir):
            d.mkdir(parents=True, exist_ok=True)
