# System requirements

| Tool | Min version | macOS | Linux (Debian/Ubuntu) |
|---|---|---|---|
| node | 20.x | `brew install node@20` | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt install -y nodejs` |
| python | 3.10 | `brew install python@3.12` | `sudo apt install python3 python3-venv` |
| ffmpeg | 6.x | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| imagemagick | 7.x | `brew install imagemagick` | `sudo apt install imagemagick` |
| git | 2.30 | `brew install git` | `sudo apt install git` |
| uv | 0.4 | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

## Disk space
Allow ~3 GB for a typical 60-second run (clips, intermediate frames, audio, final.mp4). The `.venv/` is ~400 MB.

## Network
Outbound HTTPS only — fal.ai, ElevenLabs, and the user's VPS. No inbound ports required (brief UI binds `127.0.0.1` only).

## macOS notes
- imagemagick `convert` may collide with `/usr/bin/convert` from XQuartz. `brew link --overwrite imagemagick` if needed.
- On Apple Silicon, MoviePy + ffmpeg work natively (no Rosetta).
