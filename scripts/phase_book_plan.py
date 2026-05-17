"""Phase B1 — book-plan.

Curates the book page list:
  - Reads brief.json, script.md (via script_io), characters/, storyboard/keyframes/.
  - Mixes reused video beats with book-only scenes; total = brief.book.page_count_target.
  - Assigns one template per page from the user's shortlist using a content-type heuristic.
  - Rewrites each beat's narration into book voice (storybook/factual/playful).
  - Writes book/plan.json. Caller surfaces Gate B1 to the user.

Deliberately mechanical: the orchestrating skill (skills/book-plan/SKILL.md) is
where Claude does any higher-order rewriting. This script provides the
deterministic floor so a `--run-dir` invocation always produces a valid plan,
which Claude can then refine via direct file edits at Gate B1.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

from scripts.lib.run_state import RunState
from scripts.lib.paths import RunPaths
from scripts.lib.book_canvas import canvas_for
from scripts.lib import script_io


CONTENT_TYPE_PREFS = {
    "narrative":       ["full-bleed-with-text-zone", "split-layout", "illustrated-border"],
    "educational":     ["scattered-spots", "connected-infographic", "split-layout"],
    "character_intro": ["vignette-on-page", "character-text-pocket", "split-layout"],
    "dramatic":        ["full-spread-no-text", "spread-scene-plus-spots", "full-bleed-with-text-zone"],
}


def classify_beat(beat) -> str:
    """Lightweight content classification from beat label + visual cue."""
    blob = f"{getattr(beat, 'label', '')} {getattr(beat, 'visual', '') or ''} {getattr(beat, 'narration', '')}".lower()
    if any(k in blob for k in ("intro", "introduce", "meet", "hello")):
        return "character_intro"
    if any(k in blob for k in ("climax", "reveal", "dramatic", "twist")):
        return "dramatic"
    if any(k in blob for k in ("explain", "concept", "how", "why", "step", "process", "definition")):
        return "educational"
    return "narrative"


def pick_template(content_type: str, allowed: list[str]) -> str:
    for t in CONTENT_TYPE_PREFS.get(content_type, []):
        if t in allowed:
            return t
    return allowed[0]


def _strip_html_comments(s: str) -> str:
    return re.sub(r"<!--.*?-->", "", s or "", flags=re.DOTALL).strip()


def book_voice_rewrite(line: str, voice: str) -> str:
    """Deterministic fallback rewrite. Claude's planning pass typically replaces this."""
    s = _strip_html_comments(line or "").strip()
    if not s:
        return ""
    # cap at ~4 lines / ~280 chars
    if len(s) > 280:
        s = s[:277] + "…"
    if voice == "factual_calm":
        return s.rstrip("!.")
    if voice == "playful_rhyming":
        return s.rstrip(".") + "."
    return s   # storybook_narrator: pass-through


def _default_text_zone(template: str) -> str:
    return {
        "full-bleed-with-text-zone":   "top-left third, 4 lines",
        "vignette-on-page":            "top 40% of canvas, centered, 4 lines",
        "split-layout":                "right half, top-aligned, 6 lines",
        "scattered-spots":             "center of page between spots, 5 lines",
        "full-spread-no-text":         "no text zone (illustration-only)",
        "illustrated-border":          "central rectangular text region, 8 lines",
        "character-text-pocket":       "bottom 35% pocket area, 5 lines",
        "connected-infographic":       "labels around each node, 1–2 lines each",
        "spread-scene-plus-spots":     "top 25% above the scene, 3 lines",
    }.get(template, "centered, 4 lines")


def _default_prompt_params(template: str) -> dict:
    return {
        "full-bleed-with-text-zone": {"text_zone_side": "RIGHT", "text_zone_percent": "35",
                                       "art_style_description": "soft, painterly children's-book illustration"},
        "vignette-on-page":          {"vignette_position": "BOTTOM-CENTER", "vignette_percent": "55",
                                       "text_area_position": "TOP", "decorative_elements": "leaves, small petals"},
        "split-layout":              {"split_side": "LEFT", "art_style_description": "painterly"},
        "scattered-spots":           {"spot_count": "5", "art_style_description": "flat-illustration"},
        "full-spread-no-text":       {"art_style_description": "cinematic painterly"},
        "illustrated-border":        {"border_motif": "leaves and vines", "art_style_description": "watercolour"},
        "character-text-pocket":     {"character_position": "TOP-CENTER", "art_style_description": "claymation-3d"},
        "connected-infographic":     {"node_count": "3", "art_style_description": "flat-illustration"},
        "spread-scene-plus-spots":   {"spot_count": "2", "art_style_description": "painterly"},
    }.get(template, {"art_style_description": "painterly children's-book illustration"})


def build_plan(brief: dict, beats: list, keyframes_dir: Path,
               characters_dir: Path) -> dict:
    book = brief.get("book") or {}
    n = int(book.get("page_count_target") or 0)
    if n <= 0:
        return {"pages": []}
    allowed = list(book.get("templates") or [])
    if len(allowed) < 2:
        raise ValueError("brief.book.templates requires 2–4 entries")
    voice = book.get("voice") or "storybook_narrator"

    reused_n = min(len(beats), max(1, int(round(n * 0.6))))
    bookonly_n = n - reused_n

    # Character refs: prefer sheet.png; otherwise grab up to 3 PNGs from characters/
    char_refs: list[str] = []
    sheet = characters_dir / "sheet.png"
    if sheet.exists():
        char_refs.append("characters/sheet.png")
    for p in sorted(characters_dir.glob("*.png")):
        rel = f"characters/{p.name}"
        if rel not in char_refs:
            char_refs.append(rel)
        if len(char_refs) >= 3:
            break

    pages: list[dict] = []

    # 1) reused video beats
    for i in range(reused_n):
        beat = beats[i]
        ctype = classify_beat(beat)
        tmpl = pick_template(ctype, allowed)
        kf_name = f"beat_{beat.id:02d}.png"
        kf_rel = f"storyboard/keyframes/{kf_name}"
        kf_path = keyframes_dir / kf_name
        if not kf_path.exists():
            kf_rel = None
        pages.append({
            "page_no": len(pages) + 1,
            "scene_source": f"beat_{beat.id}",
            "keyframe_ref": kf_rel,
            "character_refs": char_refs[:3],
            "template": tmpl,
            "canvas": canvas_for(tmpl),
            "scene_prompt": (_strip_html_comments(getattr(beat, "visual", "") or beat.narration))[:300].strip(),
            "book_voice_copy": book_voice_rewrite(beat.narration, voice),
            "text_zone_hint": _default_text_zone(tmpl),
            "prompt_params": _default_prompt_params(tmpl),
        })

    # 2) book-only scenes — derive light extensions from script summary/title
    summary = ""
    if beats:
        summary = beats[0].narration[:200]
    for j in range(bookonly_n):
        ctype = "narrative" if j % 2 == 0 else "educational"
        tmpl = pick_template(ctype, allowed)
        pages.append({
            "page_no": len(pages) + 1,
            "scene_source": "book_only",
            "keyframe_ref": None,
            "character_refs": char_refs[:3],
            "template": tmpl,
            "canvas": canvas_for(tmpl),
            "scene_prompt": (
                f"Additional book scene #{j+1}: a moment that elaborates on "
                f"\"{summary[:120]}\". The characters appear in the same style as the sheets."
            ),
            "book_voice_copy": "",   # to be filled by the planner LLM or user at Gate B1
            "text_zone_hint": _default_text_zone(tmpl),
            "prompt_params": _default_prompt_params(tmpl),
        })

    return {"pages": pages}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()

    rp = RunPaths(run_dir)
    rs = RunState.load_or_init(run_dir)

    brief_path = rp.brief
    if not brief_path.exists():
        print("[book-plan] brief.json missing.", file=sys.stderr)
        return 2
    brief = json.loads(brief_path.read_text(encoding="utf-8"))

    if not (brief.get("book") or {}).get("page_count_target"):
        print("[book-plan] brief.book.page_count_target = 0 or absent; skipping.")
        return 0

    script_path = rp.script
    if not script_path.exists():
        print(f"[book-plan] {script_path.name} missing — run Phase 1 first.", file=sys.stderr)
        return 2
    script = script_io.load(script_path)
    beats = list(script.beats)

    keyframes_dir = rp.keyframes_dir
    characters_dir = rp.characters_dir
    if not characters_dir.exists():
        characters_dir.mkdir(parents=True, exist_ok=True)

    plan = build_plan(brief, beats, keyframes_dir, characters_dir)

    book_dir = run_dir / "book"
    book_dir.mkdir(parents=True, exist_ok=True)
    out = book_dir / "plan.json"
    out.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    n_pages = len(plan["pages"])
    print(f"[book-plan] wrote {out} with {n_pages} pages.")

    # mark state
    rs.phases.setdefault("book_plan", {})["status"] = "complete"
    rs.next_phase = "book_render"
    rs.save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
