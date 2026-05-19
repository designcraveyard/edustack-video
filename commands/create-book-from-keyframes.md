---
description: Build a print-ready picture book from an existing video run's storyboard keyframes. Reuses keyframes verbatim — no fresh gpt-image-2 illustrations.
---

# /create-book-from-keyframes

Use this when a video run has completed and the user wants a picture book built from the same keyframes the video used — preserving visual continuity between the video and the printed book. Skips Phase B1 and B2 entirely; goes straight to birefnet (when requested) and A4P / A3L canvas composition at 300 DPI.

**Invoke the `book-from-keyframes` skill immediately.** It will:

1. Identify or ask for the source run directory (must have `storyboard/keyframes/beat_*.png`).
2. List available keyframes with beat labels and narration.
3. Walk the user through a chat-driven page assignment: which keyframe → which page → which template → what voice copy → remove background or not.
4. Compose and save `<run-dir>/book/from_keyframes.config.json` for review.
5. Run `scripts.phase_book_from_keyframes` to produce the RGBA pages and the final A4P / A3L canvases at 300 DPI.
6. Surface the outputs in chat with clickable paths.

If the user does not have a completed video run yet, suggest `/create-video` first — this command is for the post-video book path. If the user wants entirely fresh book illustrations (not based on the video keyframes), tell them to set `brief.book.page_count_target > 0` in their video brief and run `/create-video` with the book branch enabled — that's the default Phase B1–B3 path.

For per-page regeneration after an initial run of this command, the user can edit `<run-dir>/book/from_keyframes.config.json` directly and re-invoke this command — the script overwrites pages in place.
