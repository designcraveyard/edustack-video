"""Devanagari / Indic-script → Latin transliteration for subtitles.

VO narration must stay in native script so ElevenLabs phonemizes correctly.
Subtitles, however, are typically read by learners who prefer Latin script —
especially for Hinglish, where mixed Devanagari + English is visually awkward
in a single subtitle line.

Strategy: a single `to_latin(text, language)` that:
  - leaves English text alone
  - transliterates Devanagari (Hindi, Hinglish, Marathi) using ITRANS
    (most readable Latin output, e.g. "नमस्ते" → "namaste")
  - transliterates Tamil → IAST-Tamil
  - transliterates Bengali → IAST

Uses the `indic-transliteration` package when available; falls back to a
character-table for the common Devanagari block so a missing dependency
doesn't break the pipeline.
"""
from __future__ import annotations

# Tiny fallback mapping for Devanagari → ASCII when the indic-transliteration
# package isn't installed. Not complete, but covers everyday Hindi+Hinglish
# enough for subtitles to remain readable.
_FALLBACK_DEVANAGARI = {
    # vowels
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    # consonants
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "ज़": "z", "फ़": "f", "क़": "q",
    # matras (vowel signs)
    "ा": "a", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu",
    "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    # halant (virama) — suppress the implicit 'a'
    "्": "",
    # anusvara, visarga, chandrabindu
    "ं": "n", "ः": "h", "ँ": "n",
    # numerals
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
    # punctuation
    "।": ".", "॥": ".",
}


def _has_devanagari(text: str) -> bool:
    return any("ऀ" <= c <= "ॿ" for c in text)


def _has_tamil(text: str) -> bool:
    return any("஀" <= c <= "௿" for c in text)


def _has_bengali(text: str) -> bool:
    return any("ঀ" <= c <= "৿" for c in text)


def _fallback_devanagari_to_latin(text: str) -> str:
    out = []
    for ch in text:
        out.append(_FALLBACK_DEVANAGARI.get(ch, ch))
    return "".join(out)


def to_latin(text: str, language: str | None = None) -> str:
    """Best-effort transliteration to Latin. Idempotent for pure-Latin input.

    `language` is a hint. When omitted, the function detects script per-word
    so mixed Hinglish ("English के साथ") works too.
    """
    if not text:
        return text
    # Quick path: if no Indic characters anywhere, return as-is.
    if not (_has_devanagari(text) or _has_tamil(text) or _has_bengali(text)):
        return text

    try:
        from indic_transliteration import sanscript  # type: ignore
        from indic_transliteration.sanscript import transliterate  # type: ignore
    except Exception:
        # No package available — use the built-in fallback for Devanagari only.
        return _fallback_devanagari_to_latin(text) if _has_devanagari(text) else text

    # Transliterate per-script in one pass each. The library leaves chars from
    # the wrong script alone, so chaining is safe.
    out = text
    if _has_devanagari(out):
        out = transliterate(out, sanscript.DEVANAGARI, sanscript.ITRANS)
        # ITRANS uses uppercase for long vowels (aa→A, ii→I); lowercase for readability.
        out = out.replace("A", "aa").replace("I", "ii").replace("U", "uu")
    if _has_tamil(out):
        out = transliterate(out, sanscript.TAMIL, sanscript.IAST)
    if _has_bengali(out):
        out = transliterate(out, sanscript.BENGALI, sanscript.IAST)
    return out
