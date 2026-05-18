# edustack-video

A Claude Code plugin for generating educational explainer videos.

**Stack:** fal.ai (image + video + Gemini vision) · ElevenLabs (VO + word timestamps) · MoviePy (stitching) · FastAPI VPS (observability).

## Quick start

```bash
# Install
claude plugin add https://github.com/designcraveyard/edustack-video

# First-time setup (in any project dir you want to use as output root)
/create-video-setup

# Create a video
/create-video
```

You need **two API keys**:
- `FAL_KEY` — https://fal.ai/dashboard/keys
- `ELEVENLABS_API_KEY` — https://elevenlabs.io/app/settings/api-keys

System requirements: Node 20+, Python 3.10+, ffmpeg, imagemagick, git.

## Commands

| Command | Purpose |
|---|---|
| `/create-video` | Start a new run. Opens a localhost brief form, then walks through 5 phases with 4 review gates. |
| `/create-video-setup` | First-time wizard: keys, output folder, deps. |
| `/create-video-resume` | Resume an interrupted run from the last completed gate. |
| `/create-video-regen <phase\|item>` | Targeted regeneration (e.g. `regen clip 3`). |
| `/create-video-support` | Bundle current run state + chat → print debug URL. |
| `/test-logs` | Self-test the Supabase observability pipeline. Emits one synthetic event per stream + exercises the chat hook, then verifies each row landed. Run after setup. |
| `/plugin-update` | Pull latest from `main`, sync deps, show changelog. |
| `/plugin-info` | Current SHA, commits behind, recent changelog. |
| `/plugin-rollback <sha>` | Check out an older commit. |

## Pipeline

```
brief → script → vo+timeline → [character sheet] → storyboard/keyframes → clips → stitch
        Gate 1    Gate 2                            Gate 3                 Gate 4
```

Each gate emits artifact paths in chat. Reply `approve` to advance, or `regen clip 3: face too dark` to selectively regenerate.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full system design (forthcoming).

## License

MIT
