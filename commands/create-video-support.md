---
description: Bundle current run state + recent chat into a shareable VPS debug URL.
---

# /create-video-support

1. Find the active run (`<output>/runs/*/run.json` with `status != complete`). If none, find the most recent.
2. POST a fresh `/chat-transcripts` upload for the current session (force-flush regardless of `chat_capture` setting — this is user-initiated).
3. Flush any queued local `logs/local.jsonl` to VPS `/logs`.
4. Optionally prompt the user: *"Upload final.mp4 / sample artifacts for visual reference in the debug view? [y/N]"* — if yes, POST to `/runs/{id}/artifacts`.
5. Print the URL: `https://eduplugin.birdzeye.in/runs/<run_id>/debug.html`.
6. Tell the user to paste it where they want support — the URL gives the helper full timeline (prompts, analyses, gates, chat) without touching their machine.
