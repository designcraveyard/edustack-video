"""Phase 3a — Characters.

Three branches driven by brief.character_mode:
  - human    : gpt-image-2 rich-template sheet (title + hero pose + expressions
               row + turnaround + palette + details) + Gemini audit + descriptions.json.
  - abstract : gpt-image-2 rich-template sheet for stylized/non-human mascots
               + Gemini audit + descriptions.json.
  - none     : write characters/description_block.md only; no sheet PNG; no
               descriptions.json (Phase 3a is otherwise skipped).

Output contract (human / abstract):
    characters/sheet.png            ← the generated sheet (gpt-image-2, 16:9)
    characters/sheet_prompt.md      ← the verbatim prompt sent (style descriptor
                                       + per-character verbatim descriptions +
                                       layout instructions)
    characters/analysis.json        ← Gemini 2.5 Pro QA report + _qa_history
    characters/descriptions.json    ← per-character verbatim descriptions.
                                       Downstream phases (storyboard, clips)
                                       paste these IDENTICALLY into every prompt
                                       so the model sees the same character
                                       paragraph every time. This is THE
                                       consistency mechanism.

The verbatim description block is what eliminates drift across the whole
pipeline. The sheet PNG is an additional grounding signal for image-conditioned
generations; the text descriptions are non-negotiable.

References (mirror these in prompt copy):
  - skills/character-sheet-generator/references/prompt-template.md
    (canonical Jay/Scooterist + Leafy Grazer/Claw Hunter layouts)
  - skills/character-sheet-generator/references/character-sheet-design.md
  - skills/character-sheet-generator/references/model-selection.md
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import textwrap
from pathlib import Path

from scripts.lib.config import load as load_config
from scripts.lib.run_state import RunState
from scripts.lib.vps_logger import VPSLogger
from scripts.lib.paths import RunPaths
from scripts.lib.fal_client import FalClient
from scripts.lib.visual_analyzer import VisualAnalyzer
from scripts.lib import script_io


# ── Style descriptors ──────────────────────────────────────────────────────
# Mapping from brief.style → one-paragraph aesthetic descriptor that gets
# prepended to the gpt-image-2 prompt. Falls back to a generic descriptor that
# names the style verbatim. Add more as brief styles are introduced.
STYLE_DESCRIPTORS: dict[str, str] = {
    "pixar": (
        "Pixar 3D animated film aesthetic, soft directional lighting, smooth "
        "subsurface materials, expressive characters, shallow depth of field."
    ),
    "watercolour": (
        "Watercolour illustration aesthetic, paper texture, soft pigment bleeds, "
        "layered washes, hand-mixed earthy palette."
    ),
    "watercolor": (
        "Watercolour illustration aesthetic, paper texture, soft pigment bleeds, "
        "layered washes, hand-mixed earthy palette."
    ),
    "2d flat": (
        "2D flat illustration aesthetic, clean vector shapes, limited shading, "
        "bold readable silhouettes, harmonised palette, no gradients."
    ),
    "2d animated": (
        "2D animated film aesthetic, hand-painted backgrounds, expressive line "
        "work, layered cel shading, vibrant story-driven palette."
    ),
    "cinematic": (
        "Cinematic live-action aesthetic, naturalistic lighting, photoreal "
        "materials, shallow depth of field, filmic colour grading."
    ),
    "whiteboard": (
        "Whiteboard explainer aesthetic, ink line work on warm off-white, "
        "spot colour for emphasis, simple flat shading, clear silhouettes."
    ),
    "doodle": (
        "Doodle sketchbook aesthetic, slightly imperfect ink lines, hand-noted "
        "labels, paper grain, restrained spot colour."
    ),
    "clay": (
        "Stop-motion clay animation aesthetic, plasticine sheen, visible "
        "thumbprints, soft directional studio lighting, slightly chunky proportions."
    ),
}


def style_descriptor_for(style: str) -> str:
    key = (style or "").strip().lower()
    if key in STYLE_DESCRIPTORS:
        return STYLE_DESCRIPTORS[key]
    # Fall back: name the style verbatim so the model has SOMETHING to anchor on.
    return (
        f"{style.strip()} illustration aesthetic. Cohesive visual language, "
        "polished concept-art finish, classroom-friendly readability."
    )


# ── Style-specific "Style requirements" finish bullets ─────────────────────
STYLE_FINISH_BULLETS: dict[str, list[str]] = {
    "pixar": [
        "Pixar 3D finish with soft global illumination, subtle subsurface scattering, "
        "gentle ambient occlusion, and polished family-film rendering",
    ],
    "watercolour": [
        "Watercolour finish with soft pigment blooms, translucent washes, and hand-painted edges",
    ],
    "watercolor": [
        "Watercolour finish with soft pigment blooms, translucent washes, and hand-painted edges",
    ],
    "2d flat": [
        "Flat vector finish: crisp edges, no gradients on character forms, "
        "limited cel shading for depth",
    ],
    "2d animated": [
        "Hand-painted 2D animation finish: layered cel shading, painterly backgrounds, "
        "expressive line weight",
    ],
    "cinematic": [
        "Photoreal cinematic finish: naturalistic skin and fabric, soft cinematic key + fill, "
        "filmic colour grade",
    ],
    "whiteboard": [
        "Whiteboard ink-on-paper finish: clean line work, restrained spot colour, "
        "soft warm paper tone",
    ],
    "doodle": [
        "Sketchbook doodle finish: slightly wobbly lines, hand-noted captions, paper grain",
    ],
    "clay": [
        "Stop-motion clay finish: visible plasticine texture, soft studio lighting, "
        "subtle thumbprints retained",
    ],
}


def style_finish_bullets(style: str) -> list[str]:
    key = (style or "").strip().lower()
    return STYLE_FINISH_BULLETS.get(key) or [
        f"Cohesive {style} finish; polished concept-art presentation"
    ]


# ── Expression + detail callout heuristics ─────────────────────────────────
DEFAULT_CLOSEUP_EXPRESSIONS = ["focus", "curiosity", "surprise", "friendly smile"]
DEFAULT_EXPRESSION_GRID = ["curiosity", "calm", "surprise", "focus", "reassurance", "confidence"]


def closeup_expressions_for(cast: script_io.CastMember, fallback: list[str]) -> list[str]:
    """Pick 4 expressions for the close-up row from the character's personality
    text. Falls back to a sensible default set.

    We look for emotion words in the personality / voice_tone text and prefer
    those when present. This makes Jay's row read "focus / determination /
    surprise / delighted laughter" instead of a generic set when the script
    has already characterised him.
    """
    blob = " ".join([cast.personality, cast.voice_tone]).lower()
    candidates = [
        "focus", "determination", "surprise", "delighted laughter",
        "calm", "curiosity", "alert focus", "confident calm",
        "concern", "joy", "concentration", "thoughtful", "hopeful",
        "mild confusion", "casual riding", "unaware focus",
        "gentle surprise", "relaxed chewing", "friendly smile",
        "quick head turn", "classroom-friendly determination",
    ]
    picked: list[str] = []
    for c in candidates:
        if c in blob and c not in picked:
            picked.append(c)
        if len(picked) >= 4:
            break
    while len(picked) < 4:
        for c in fallback:
            if c not in picked:
                picked.append(c)
            if len(picked) >= 4:
                break
    return picked[:4]


def expression_grid_for_cast(cast: list[script_io.CastMember]) -> list[str]:
    """Pick 4–6 expressions for the bottom EXPRESSIONS grid that span the cast.

    Union the per-character close-up sets, dedupe, cap at 6.
    """
    out: list[str] = []
    for m in cast:
        for e in closeup_expressions_for(m, DEFAULT_CLOSEUP_EXPRESSIONS):
            if e not in out:
                out.append(e)
        if len(out) >= 6:
            break
    while len(out) < 4:
        for e in DEFAULT_EXPRESSION_GRID:
            if e not in out:
                out.append(e)
            if len(out) >= 4:
                break
    return out[:6]


def palette_swatches_from_looks(cast: list[script_io.CastMember]) -> list[str]:
    """Pull simple "<colour> <thing>" swatch labels from the cast's looks text.

    We match common <adjective>+<noun> colour patterns ("dark hair", "warm
    brown skin", "blue jersey"). When the looks text is sparse, fall back to
    a small generic palette so the BOTTOM CENTER cell isn't empty.
    """
    swatches: list[str] = []
    palette_pattern = re.compile(
        r"\b("
        r"warm brown|dark brown|light brown|deep brown|"
        r"warm orange|burnt orange|warm orange-brown|"
        r"leaf green|sage green|olive green|forest green|"
        r"cream|beige|tan|"
        r"navy blue|royal blue|sky blue|"
        r"charcoal|graphite|slate|"
        r"helmet grey|warm grey|"
        r"paper white|off white"
        r")\b"
        r"(?:\s+(skin|hair|eyes|mane|coat|jersey|shirt|top|shorts|trousers|"
        r"jacket|sweater|helmet|scooter|stripe|paw|highlight|umber|accent|stick))?",
        flags=re.IGNORECASE,
    )
    for m in cast:
        for hit in palette_pattern.finditer(m.looks):
            label = " ".join(filter(None, [hit.group(1), hit.group(2)])).strip().lower()
            if label and label not in swatches:
                swatches.append(label)
            if len(swatches) >= 7:
                break
    while len(swatches) < 5:
        for fallback in ("warm skin tone", "dark hair", "primary outfit colour",
                         "accent colour", "neutral background"):
            if fallback not in swatches:
                swatches.append(fallback)
            if len(swatches) >= 5:
                break
    return swatches[:7]


def detail_callouts_for_cast(cast: list[script_io.CastMember]) -> list[str]:
    """Pick 3–5 visually distinctive details to call out at BOTTOM RIGHT.

    Heuristic: look for nouns the looks text emphasises ("eyebrows", "mane",
    "helmet", "stick", "paw", "tail", "stripe"). Concrete + visual; never
    abstract concepts.
    """
    detail_keywords = [
        "eyebrows", "mane", "helmet", "hockey-stick", "stick",
        "paw", "tail", "stripe", "stripes", "spots", "ears",
        "muzzle", "horns", "basket", "leaf", "fang", "claws",
        "scooter body", "jersey number", "wristband", "boots",
    ]
    out: list[str] = []
    for m in cast:
        looks_l = m.looks.lower()
        for kw in detail_keywords:
            if kw in looks_l and kw not in out:
                # Personalise the callout: "{name}'s {kw}" reads better on a sheet.
                out.append(f"{m.name}'s {kw}")
            if len(out) >= 5:
                break
    return out[:5] if out else [
        f"{cast[0].name}'s silhouette",
        "primary outfit detail",
        "signature accessory",
        "expression motif",
    ][:5]


# ── Rich-template prompt for human / abstract sheets ───────────────────────
HUMAN_SHEET_PROMPT = textwrap.dedent("""\
    {style_descriptor}

    Create a highly detailed {style} character turnaround sheet on a clean white studio background. Layout should resemble a professional animation pre-production character design board, 16:9, with generous whitespace and handwritten sketchbook typography labels.

    Title at top-left:
    "{title}"
    Subtitle:
    "CHARACTER SHEET"

    Overall aesthetic:
    {aesthetic_bullets}

    LEFT SECTION:
    Show a full-body hero pose of {hero_pose_description}.

    {character_blocks}

    CENTER TOP:
    Label: "{char1_name_upper}"
    - 4 close-up facial expressions in a horizontal row: {char1_closeups}
    - Below: full-body turnaround views — front, 3/4, side, back
    {right_top_section}
    BOTTOM CENTER:
    Label: "COLOR PALETTE"
    Circular swatches for the distinctive colors in this sheet: {palette_swatches}

    BOTTOM MIDDLE:
    Label: "EXPRESSIONS"
    Show additional small emotional portraits for {expression_grid_subjects}: {expression_grid}

    BOTTOM RIGHT:
    Label: "DETAILS"
    Close-up detail callouts for the visually distinctive features: {detail_callouts}

    Style requirements:
    - Cohesive visual language
    - Character proportions matching the brief's style
    - {finish_bullets}
    - Clean presentation sheet, white margins, balanced grid layout
    - 16:9 horizontal aspect ratio
    - Concept-art quality
""")


ABSTRACT_AESTHETIC_BULLETS_DEFAULT = [
    "Cohesive stylised aesthetic with a clear non-human mascot silhouette",
    "Classroom-friendly storybook mood, never scary or aggressive",
    "Muted organic palette with one warm accent family per character",
    "Light sketch-line outlines, no heavy ink blacks",
    "Readable mascot shapes at thumbnail size",
]

HUMAN_AESTHETIC_BULLETS_DEFAULT = [
    "Soft cinematic lighting with clear action-movie readability for a child audience",
    "Strong silhouette contrast between primary and secondary characters",
    "Clean studio presentation with polished shading and easy silhouette recognition",
    "Bright family-friendly palette",
    "Gentle surface detail, smooth materials, and strong clarity for motion scenes",
]


def aesthetic_bullets_for(mode: str, style: str) -> list[str]:
    """Pick 4–5 bullets describing the overall sheet aesthetic.

    These appear under "Overall aesthetic:" and shape how gpt-image-2
    handles lighting, palette, and silhouette. We bias on `mode` first
    (abstract sheets get mascot-readability hints; human sheets get
    silhouette/lighting hints), then keep generic style-friendly bullets.
    """
    base = ABSTRACT_AESTHETIC_BULLETS_DEFAULT if mode == "abstract" else HUMAN_AESTHETIC_BULLETS_DEFAULT
    return list(base)


# ── Cast utilities ──────────────────────────────────────────────────────────
def pick_cast_for_sheet(cast: list[script_io.CastMember], max_chars: int = 2) -> list[script_io.CastMember]:
    """Choose up to 2 characters for the sheet.

    Strategy: keep the script's declared order. The script-writer puts the
    protagonist first; a single shared sheet for protagonist + closest
    foil is the most useful reference for downstream phases.

    If there are 3+ characters, we still only put 2 on the sheet — the
    user's design rule. Phase 3a writes a notice into descriptions.json
    so the storyboard phase knows there are off-sheet characters to embed
    via description-only paragraphs.
    """
    if not cast:
        return []
    return cast[:max_chars]


def fallback_cast_from_script(script: script_io.Script) -> list[script_io.CastMember]:
    """When the script has no Cast block (legacy scripts, abstract mode),
    synthesise one or two placeholder CastMembers from the script's title
    and first beat narration so we still have something to put on the sheet.
    """
    head = script.beats[0].narration_plain if script.beats else script.title
    looks = (head[:300] or script.title).strip()
    return [
        script_io.CastMember(
            name="Narrator-on-screen",
            role="On-camera explainer / mascot for the lesson",
            personality="Clear, curious, and kind. Pulls the learner into the topic.",
            voice_tone="Warm, mid-paced, supportive.",
            looks=looks,
        )
    ]


def hero_pose_description(cast: list[script_io.CastMember]) -> str:
    if len(cast) >= 2:
        return f"{cast[0].name} standing beside {cast[1].name}, interacting in-character and clearly distinct"
    if cast:
        return f"{cast[0].name}, in a confident yet relaxed stance facing camera-right"
    return "the lesson's main character in a confident, on-model hero pose"


def character_blocks_text(cast: list[script_io.CastMember]) -> str:
    """Render the LEFT SECTION's per-character verbatim description blocks.

    These are the descriptions the model reads for the hero pose AND that
    we re-paste IDENTICALLY into every downstream prompt for consistency.
    """
    parts: list[str] = []
    for m in cast:
        parts.append(f"{m.name}:\n{m.verbatim_description}")
    return "\n\n".join(parts)


def right_top_section_text(cast: list[script_io.CastMember]) -> str:
    """Optional RIGHT TOP block for the second character. Empty for a solo sheet."""
    if len(cast) < 2:
        return ""
    closeups = ", ".join(closeup_expressions_for(cast[1], DEFAULT_CLOSEUP_EXPRESSIONS))
    return textwrap.dedent(f"""
        RIGHT TOP:
        Label: "{cast[1].name.upper()}"
        - 4 close-up facial expressions in a horizontal row: {closeups}
        - Below: full-body turnaround views — front, 3/4, side, back
    """).rstrip() + "\n"


def basename_for(cast: list[script_io.CastMember]) -> str:
    """Filename basename for prompt + analysis siblings (sheet.png is fixed)."""
    if len(cast) >= 2:
        return f"{cast[0].slug}-and-{cast[1].slug}"
    if cast:
        return cast[0].slug
    return "sheet"


def sheet_title_for(cast: list[script_io.CastMember]) -> str:
    if len(cast) >= 2:
        return f"{cast[0].name} & {cast[1].name}"
    if cast:
        return cast[0].name
    return "Character Sheet"


# ── Description-block prompt (mode: none) ──────────────────────────────────
DESC_BLOCK_SYSTEM = textwrap.dedent("""\
    You are a continuity supervisor for an explainer video. Given the script's
    topic and any character notes, write a structured 'character description block'
    that will be prepended to every storyboard and clip prompt to keep characters
    consistent across the whole video.

    Return STRICT markdown matching:
      ## Characters
      - **<role>**: <species/age> · <build/height> · <hair> · <eyes> · <skin/coat> · <outfit> · <signature prop/expression>.
      - ...

      ## Crowd / extras
      - <collective character description, if relevant>

      ## Consistency notes
      - <2-3 bullet rules: relative heights, lighting, palette locks>

    Be concrete and visual. No adjectives that don't translate to motion.""")


AUTO_RETRY_BUDGET = 2


# ── Output writers ─────────────────────────────────────────────────────────
def write_descriptions_json(rp: RunPaths, cast: list[script_io.CastMember],
                            style: str, style_descriptor: str,
                            extras_count: int) -> None:
    """Canonical per-character verbatim descriptions for downstream phases.

    Storyboard and Clip prompts paste these IDENTICALLY into every CHARACTERS
    section. This is what locks identity across the pipeline.
    """
    payload = {
        "style": style,
        "style_descriptor": style_descriptor,
        "characters": [
            {
                "name": m.name,
                "slug": m.slug,
                "role": m.role,
                "personality": m.personality,
                "voice_tone": m.voice_tone,
                "looks": m.looks,
                "verbatim_description": m.verbatim_description,
            }
            for m in cast
        ],
        "off_sheet_extras_count": extras_count,
    }
    rp.character_descriptions.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def write_prompt_md(rp: RunPaths, prompt: str, cast: list[script_io.CastMember],
                    style: str, style_descriptor: str, model: str, attempts: int) -> None:
    """Save the full prompt the model received, plus the verbatim descriptors,
    next to the sheet. Mirrors the structured "Character Sheet Prompt" doc
    the user provided as a reference example so a human can quickly audit
    what was sent."""
    char_count = len(cast)
    lines = [
        f"# Character Sheet Prompt — {basename_for(cast)}",
        "",
        f"- **Style:** {style}",
        f"- **Generator:** fal.ai / {model} · quality=high · aspect=16:9",
        f"- **Characters in this sheet:** {char_count} of max 2",
        f"- **Generation attempts:** {attempts}",
        "",
        "## Style descriptor",
        "",
        style_descriptor,
        "",
        "## Character descriptions (verbatim — reuse identically downstream)",
        "",
    ]
    for i, m in enumerate(cast, 1):
        lines.append(f"### {i}. {m.name}")
        lines.append("")
        lines.append(m.verbatim_description)
        lines.append("")
    lines.append("## Full prompt sent to the image model")
    lines.append("")
    lines.append("```text")
    lines.append(prompt.rstrip())
    lines.append("```")
    rp.character_prompt.write_text("\n".join(lines))


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--auto-retries", type=int, default=AUTO_RETRY_BUDGET,
                    help="Max auto-corrective regens when QA verdict=NEEDS_REGEN.")
    args = ap.parse_args()
    rp = RunPaths(Path(args.run_dir))
    rp.ensure_dirs()
    cfg = load_config(rp.dir.parent.parent)
    state = RunState.load_or_init(rp.dir)
    log = VPSLogger(cfg.supabase_url, cfg.supabase_anon, cfg.user_id, rp.dir)
    log.heartbeat(state.run_id, "characters", "started")

    brief = json.loads(rp.brief.read_text())
    mode = brief.get("character_mode", "human")
    style = brief.get("style", "2D Flat")
    notes = brief.get("notes", "") or ""
    script = script_io.load(rp.script)

    fal = FalClient(cfg.fal_key, logger=log, run_id=state.run_id)

    # ── mode: none ────────────────────────────────────────────────────────
    if mode == "none":
        user = (
            f"TOPIC: {script.title}\n"
            f"STYLE: {style}\nLANGUAGE: {script.language}\n"
            f"NOTES: {notes or '(none)'}\n\n"
            f"FIRST BEAT (for context):\n{script.beats[0].narration_plain if script.beats else ''}"
        )
        out = fal.any_llm(
            "google/gemini-2.5-pro",
            prompt=user, system_prompt=DESC_BLOCK_SYSTEM, phase="characters",
        )
        text = (out or {}).get("output") or (out or {}).get("text") or ""
        if not text and isinstance(out, dict):
            ch = (out.get("choices") or [{}])[0]
            text = ((ch.get("message") or {}).get("content")) or ""
        text = text.strip() or "## Characters\n- (none defined; rely on per-beat hints)\n"
        rp.description_block.write_text(text)
        log.log(state.run_id, "characters", "info",
                f"mode=none wrote {rp.description_block} bytes={len(text)}")
        state.mark_phase("characters", "complete")
        log.heartbeat(state.run_id, "characters", "complete")
        print(f"[characters] mode=none → {rp.description_block}", file=sys.stderr)
        return 0

    # ── mode: human / abstract ────────────────────────────────────────────
    cast_all = script.cast or fallback_cast_from_script(script)
    cast_sheet = pick_cast_for_sheet(cast_all, max_chars=2)
    extras_count = max(0, len(cast_all) - len(cast_sheet))
    if not cast_sheet:
        # extremely defensive — should never happen given fallback above
        raise SystemExit("no characters available for sheet (empty script.cast and fallback failed)")

    style_descriptor = style_descriptor_for(style)
    finish_bullets = "\n    - ".join(style_finish_bullets(style))
    aesthetic_bullets = "\n    - ".join(["- " + b for b in aesthetic_bullets_for(mode, style)])
    # Drop the leading "- " from the join target — we add it back uniformly.
    aesthetic_bullets = "\n    " + "\n    ".join("- " + b for b in aesthetic_bullets_for(mode, style))

    char1 = cast_sheet[0]
    char1_closeups = ", ".join(closeup_expressions_for(char1, DEFAULT_CLOSEUP_EXPRESSIONS))
    expr_grid_subjects = " and ".join(m.name for m in cast_sheet)
    expression_grid = ", ".join(expression_grid_for_cast(cast_sheet))
    palette = ", ".join(palette_swatches_from_looks(cast_sheet))
    details = ", ".join(detail_callouts_for_cast(cast_sheet))

    base_prompt = HUMAN_SHEET_PROMPT.format(
        style_descriptor=style_descriptor,
        style=style,
        title=sheet_title_for(cast_sheet),
        aesthetic_bullets=aesthetic_bullets,
        hero_pose_description=hero_pose_description(cast_sheet),
        character_blocks=character_blocks_text(cast_sheet),
        char1_name_upper=char1.name.upper(),
        char1_closeups=char1_closeups,
        right_top_section=right_top_section_text(cast_sheet),
        palette_swatches=palette,
        expression_grid_subjects=expr_grid_subjects,
        expression_grid=expression_grid,
        detail_callouts=details,
        finish_bullets=finish_bullets,
    )

    # gpt-image-2 with the model picks from models.yaml (default landscape_16_9, quality=high).
    model = (cfg.models.get("character_sheet") or {}).get("model") or "fal-ai/gpt-image-2"
    from scripts.lib.aspect import fal_image_payload
    size_payload = fal_image_payload("16:9", model, cfg.models, "character_sheet")

    va = VisualAnalyzer(fal, logger=log, run_id=state.run_id)

    attempt = 0
    addendum = ""
    analysis: dict = {}
    history: list[dict] = []
    final_prompt = base_prompt
    while attempt <= args.auto_retries:
        final_prompt = base_prompt + (
            f"\n\nADDITIONAL GUIDANCE (regen attempt {attempt}):\n{addendum}"
            if addendum else ""
        )
        result = fal.run(model, {
            "prompt": final_prompt,
            **size_payload,
        }, phase="characters")
        img_url = ((result.get("images") or [{}])[0]).get("url") or result.get("image", {}).get("url")
        if not img_url:
            raise SystemExit(f"character sheet response missing image url: {list(result.keys())}")
        fal.download(img_url, str(rp.character_sheet))

        analysis = va.analyse_character_sheet(
            rp.character_sheet, prompt_used=final_prompt,
            character_brief=character_blocks_text(cast_sheet),
            style=style, phase="characters",
        )
        verdict = (analysis.get("verdict") or "").upper()
        history.append({
            "attempt": attempt,
            "verdict": verdict or "UNKNOWN",
            "regen_reason": analysis.get("regen_reason"),
            "addendum_used": addendum or None,
        })

        if verdict == "APPROVED" or analysis.get("_degraded"):
            break

        addendum = analysis.get("corrective_addendum") \
            or analysis.get("regen_reason") \
            or "Re-render the sheet with exactly the requested layout regions. Lock palette across all cells. No background clutter."
        log.log(state.run_id, "characters", "warn",
                f"QA regen attempt {attempt + 1}: {analysis.get('regen_reason') or '(no reason)'}")
        attempt += 1

    # Persist all four outputs.
    analysis_payload = dict(analysis)
    analysis_payload["_qa_history"] = history
    rp.character_analysis.write_text(json.dumps(analysis_payload, indent=2))
    write_prompt_md(rp, final_prompt, cast_sheet, style, style_descriptor, model, attempts=len(history))
    write_descriptions_json(rp, cast_sheet, style, style_descriptor, extras_count)

    final_verdict = (analysis.get("verdict") or "UNKNOWN").upper()
    needs_review_at_gate = final_verdict != "APPROVED"
    log.log(state.run_id, "characters", "info",
            f"mode={mode} style={style} cast={[m.name for m in cast_sheet]} "
            f"attempts={len(history)} verdict={final_verdict} "
            f"sheet={rp.character_sheet.name} analysis={rp.character_analysis.name} "
            f"prompt={rp.character_prompt.name} descriptions={rp.character_descriptions.name}")

    state.mark_phase("characters", "pending_review")
    log.heartbeat(state.run_id, "characters", "complete")
    print(f"[characters] mode={mode} style={style} verdict={final_verdict} "
          f"attempts={len(history)} → {rp.character_sheet}", file=sys.stderr)
    if extras_count > 0:
        print(f"[characters] note: {extras_count} additional character(s) beyond the sheet — "
              f"their descriptions are recorded in descriptions.json for downstream prompt embedding.",
              file=sys.stderr)
    if needs_review_at_gate:
        print(f"[characters] ⚠ verdict={final_verdict} after {len(history)} attempts — "
              f"see {rp.character_analysis} for QA report", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
