# Book branch routing

When `brief.book.page_count_target > 0`, the orchestrator runs three additional
phases serially **after** the video branch completes:

```
After Phase 6 (stitch) completes:
  if brief.book.page_count_target > 0:
    Phase B1 — python3 -m scripts.phase_book_plan --run-dir <run-dir>
               (writes <run-dir>/book/plan.json)
    Gate B1 — chat: render plan.json + reply 'approve' | 'regen page N: <comment>' | 'regen all'
    Phase B2 — python3 -m scripts.phase_book_render --run-dir <run-dir>
               (writes <run-dir>/book/pages/page-NN.png + .qa.json)
    Phase B3 — python3 -m scripts.phase_book_print_prep --run-dir <run-dir>
               (writes <run-dir>/book/print/page-NN.png + .txt)
  else:
    skip book phases.
```

## Gate B1

Render `book/plan.json` as a Markdown table in chat:

| # | Source | Template | Canvas | Scene (≤80c) | Voice copy |
|---|---|---|---|---|---|
| 1 | beat_3 | split-layout | A3L | Mowgli sleeping… | "When the moon dipped…" |
| 2 | book_only | scattered-spots | A4P | Inside, green helpers… | "Tiny green helpers…" |

Followed by clickable `file://` links to:
- the keyframe ref (if present)
- the character refs
- `book/plan.json` itself

User replies parsed as:
- `approve` → proceed to Phase B2.
- `regen page N: <comment>` → edit `plan.json` entry N (template/scene_prompt/book_voice_copy/prompt_params) per the comment, re-emit the summary, wait again.
- `regen all` → re-run Phase B1 with the user's comment threaded into the planner LLM as additional guidance.

For book-only pages with empty `book_voice_copy`, the orchestrator should
generate copy from the `scene_prompt` and `brief.book.voice` style before
posting the Gate B1 summary, so the user has copy to review.

## Per-page regen after rendering

If a user wants to regenerate one image after Phase B3 (e.g. drift on page 4), they run:

```
/create-book-regen page-04
```

That command invokes `scripts/phase_book_render.py --run-dir <run-dir> --only-page 4`
followed by `scripts/phase_book_print_prep.py --run-dir <run-dir> --only-page 4`.

## Failure handling

- Phase B2 is bounded: failed pages don't block the rest of the book. They
  surface in chat with their `qa.json` payload and a hint to run
  `/create-book-regen page-NN`.
- Phase B3 has no LLM calls; the only failure mode is a missing or corrupt
  source PNG, which will print a per-page error and skip that page.
- Both Phase B2 and B3 mark `run.json.phases.book_*.status` as
  `complete | partial` so the orchestrator can report partial books cleanly.
