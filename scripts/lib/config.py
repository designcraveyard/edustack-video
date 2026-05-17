"""Load run-time config from <output>/.config/."""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import os
import yaml


@dataclass(frozen=True)
class Config:
    output_root: Path
    fal_key: str
    elevenlabs_key: str
    vps_url: str | None
    vps_token: str | None
    chat_capture: bool
    models: dict

    @property
    def config_dir(self) -> Path:
        return self.output_root / ".config"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip()


def load(output_root: str | os.PathLike | None = None) -> Config:
    root = Path(output_root or os.environ.get("EDUSTACK_VIDEO_OUTPUT") or os.getcwd()).resolve()
    cfg = root / ".config"
    if not cfg.is_dir():
        raise SystemExit(f"No .config/ at {cfg}. Run /create-video-setup first.")
    vps_url_p = cfg / "vps.url"
    vps_tok_p = cfg / "vps.token"
    cap_p = cfg / "chat_capture"
    models_p = cfg / "models.yaml"
    return Config(
        output_root=root,
        fal_key=_read(cfg / "fal.key"),
        elevenlabs_key=_read(cfg / "elevenlabs.key"),
        vps_url=_read(vps_url_p) if vps_url_p.exists() else None,
        vps_token=_read(vps_tok_p) if vps_tok_p.exists() else None,
        chat_capture=(_read(cap_p) == "on") if cap_p.exists() else False,
        models=yaml.safe_load(models_p.read_text()) if models_p.exists() else {},
    )
