# edustack-video

A Claude Code plugin for generating educational explainer videos.

**Stack:** fal.ai (image + video + Gemini 2.5 Pro vision) · ElevenLabs (VO + word timestamps) · MoviePy (stitching) · Supabase (observability).

---

## Before you install — trust posture

Claude Code plugins are **highly trusted components** that run code on your machine and can read/write files in your workspace. Anthropic does not sign, scan, or verify plugin contents — the trust model is **manual review of the source repo**. Read [their guidance here](https://docs.claude.com/en/docs/claude-code/plugins) before installing any plugin, this one included.

**Before installing this plugin:**

1. **Inspect the repo.** Browse [github.com/designcraveyard/edustack-video](https://github.com/designcraveyard/edustack-video). The pieces a defensive review should look at:
   - [`plugin.json`](plugin.json) — the manifest. Lists every command, skill, and hook this plugin registers.
   - [`hooks/ship-chat.sh`](hooks/ship-chat.sh) — the only hook. Ships Claude chat deltas to Supabase **only when** `<output>/.config/chat_capture` is set to `on` (default: off, opt-in at setup).
   - [`scripts/`](scripts/) — every Python phase script. All external API calls go through `scripts/lib/fal_client.py` and `scripts/lib/elevenlabs_client.py`. No direct HTTP elsewhere.
   - [`CLAUDE.md`](CLAUDE.md) — repo-level guardrails Claude reads on every session in this workspace.
2. **Key handling, explicit:** your `FAL_KEY` and `ELEVENLABS_API_KEY` are saved at `<output>/.config/fal.key` and `<output>/.config/elevenlabs.key` with mode `0600` on the user's machine. They are passed directly from local Python to the upstream APIs. They are **never** posted to Supabase, never logged to the observability pipeline, never sent to any third party.
3. **Observability scope:** the plugin writes event metadata (run id, phase, prompt sha256, response status, latency) to a Supabase table on the Edustack project. Generated artifacts (audio, images, video) stay on disk — only their paths and sha256 are reported. Chat-transcript shipping is opt-in.
4. **You can verify telemetry yourself after install** by running [`/test-logs`](commands/test-logs.md) — it emits one synthetic event per stream and proves they land.

If you maintain this plugin or vetted the repo with your team, you can skip the inspection step — but the install commands below are the same either way.

---

## Install

Plugin installation happens **inside Claude Code** via slash commands. The CLI subcommand `claude plugin add` does not exist (this is a common misconception).

```text
# 1. Inside a Claude Code session, register this repo as a plugin marketplace.
#    A single repo can be both the marketplace and the plugin — that's this one.
/plugin marketplace add designcraveyard/edustack-video

# 2. Install the plugin from the marketplace.
/plugin install edustack-video@edustack-video

# 3. Reload so commands + skills + hooks are picked up.
/reload-plugins
```

Local-path install (for plugin developers running off a working copy):

```text
/plugin marketplace add ~/Documents/GitHub/edustack-video
/plugin install edustack-video@edustack-video
/reload-plugins
```

If you prefer the non-interactive form for the marketplace step:

```bash
# Outside Claude Code; adds the marketplace only. The /plugin install step
# still needs to run inside a Claude Code session.
claude plugin marketplace add designcraveyard/edustack-video
```

---

## Quick start

```text
# First-time setup (in any project dir you want to use as output root)
/create-video-setup

# Verify Supabase observability is wired (recommended after every setup)
/test-logs

# Create a video
/create-video
```

You need **two API keys**:
- `FAL_KEY` — https://fal.ai/dashboard/keys
- `ELEVENLABS_API_KEY` — https://elevenlabs.io/app/settings/api-keys

**System requirements:** Node 20+, Python 3.10+, ffmpeg, imagemagick, git, `uv`. The setup wizard detects missing pieces and offers `brew install` / `apt install` one-liners.

---

## Commands

| Command | Purpose |
|---|---|
| `/create-video` | Start a new run. Opens a localhost brief form, then walks through 5 phases with 4 review gates. |
| `/create-video-setup` | First-time wizard: keys, output folder, deps, Supabase wiring. |
| `/create-video-resume` | Resume an interrupted run from the last completed gate. |
| `/create-video-regen <phase\|item>` | Targeted regeneration (e.g. `regen clip 3`). |
| `/create-video-support` | Bundle current run state + chat → print debug URL. |
| `/test-logs` | Self-test the Supabase observability pipeline. One synthetic event per stream + chat hook end-to-end, then verifies each row landed. |
| `/plugin-update` | Pull latest from `main`, sync Python + Node deps, show changelog. Does the same thing as `/plugin marketplace update edustack-video` and additionally syncs `requirements.txt` / `package.json` if they changed. |
| `/plugin-info` | Current SHA, commits behind, recent changelog. |
| `/plugin-rollback <sha>` | Check out an older commit (for "the latest version broke me" emergencies). |

---

## Pipeline

```
brief → script → vo+timeline → [character sheet] → storyboard/keyframes → clips → stitch
        Gate 1    Gate 2                            Gate 3                 Gate 4
```

Each gate emits artifact paths in chat. Reply `approve` to advance, or `regen clip 3: face too dark` to selectively regenerate.

Character sheets use `fal-ai/gpt-image-2` at 16:9 with a rich 8-region layout (title + LEFT hero pose + CENTER/RIGHT TOP per-character expression rows + turnaround + BOTTOM palette / expressions / details). Per-character verbatim descriptions written to `characters/descriptions.json` flow IDENTICALLY into every downstream prompt — that's how identity locks across all beats and clips.

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full system design.

---

## Update flow

End users update on their schedule. Two paths produce the same result; pick whichever feels native:

```text
# Native Claude Code command — the canonical update path.
/plugin marketplace update edustack-video
/reload-plugins

# OR this plugin's own command — does git pull + uv pip sync + npm ci + changelog summary.
/plugin-update
```

Both pull from `main` of this repo. The plugin tracks releases by main-branch commits (no semver-tag gating in v0.x).

---

## License

MIT
