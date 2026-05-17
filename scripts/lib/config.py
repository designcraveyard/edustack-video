"""Load run-time config from <output>/.config/.

Fields:
  fal.key           : FAL_KEY (fal.ai)
  elevenlabs.key    : ELEVENLABS_API_KEY
  supabase.url      : Supabase project URL (defaults to Edustack project)
  supabase.anon     : Supabase anon key (writes to eduplugin_events)
  user_id           : per-install uuid for namespacing events
  chat_capture      : 'on' | 'off' — opt-in chat transcript shipping
  models.yaml       : per-stage model overrides

Backwards compatibility: vps.url / vps.token still read if present, but the
new sink ignores them in favour of supabase.url / supabase.anon.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import os
import uuid
import yaml


# Defaults baked in so /create-video-setup needs zero extra prompts when the
# user is fine with the Edustack-shared observability sink.
DEFAULT_SUPABASE_URL = "https://ulyzimrayfzhbltpxbaj.supabase.co"


@dataclass(frozen=True)
class Config:
    output_root: Path
    fal_key: str
    elevenlabs_key: str
    supabase_url: str
    supabase_anon: str | None
    user_id: str
    chat_capture: bool
    models: dict

    # Back-compat properties — old callers read .vps_url / .vps_token.
    @property
    def vps_url(self) -> str: return self.supabase_url
    @property
    def vps_token(self) -> str | None: return self.supabase_anon

    @property
    def config_dir(self) -> Path:
        return self.output_root / ".config"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip()


def _read_or_create_user_id(cfg_dir: Path) -> str:
    f = cfg_dir / "user_id"
    if f.is_file():
        return _read(f)
    uid = str(uuid.uuid4())
    cfg_dir.mkdir(parents=True, exist_ok=True)
    f.write_text(uid)
    try:
        f.chmod(0o600)
    except Exception:
        pass
    return uid


def load(output_root: str | os.PathLike | None = None) -> Config:
    root = Path(output_root or os.environ.get("EDUSTACK_VIDEO_OUTPUT") or os.getcwd()).resolve()
    cfg = root / ".config"
    if not cfg.is_dir():
        raise SystemExit(f"No .config/ at {cfg}. Run /create-video-setup first.")
    sup_url_p = cfg / "supabase.url"
    sup_anon_p = cfg / "supabase.anon"
    cap_p = cfg / "chat_capture"
    models_p = cfg / "models.yaml"

    # Migration helper: read deprecated vps.* if the new files are missing,
    # purely so older installs don't break — they just won't write to Supabase
    # until a re-setup that prompts for the anon key.
    legacy_url_p = cfg / "vps.url"
    sup_url = _read(sup_url_p) if sup_url_p.exists() else (
        _read(legacy_url_p) if legacy_url_p.exists() else DEFAULT_SUPABASE_URL)

    return Config(
        output_root=root,
        fal_key=_read(cfg / "fal.key"),
        elevenlabs_key=_read(cfg / "elevenlabs.key"),
        supabase_url=sup_url,
        supabase_anon=_read(sup_anon_p) if sup_anon_p.exists() else None,
        user_id=_read_or_create_user_id(cfg),
        chat_capture=(_read(cap_p) == "on") if cap_p.exists() else False,
        models=yaml.safe_load(models_p.read_text()) if models_p.exists() else {},
    )
