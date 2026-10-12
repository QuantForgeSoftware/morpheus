"""Unicode <-> beta-code conversion and lemma normalization."""
from __future__ import annotations

import re
import unicodedata

from beta_code import beta_code_to_greek, greek_to_beta_code

# Morpheus disambiguates homonymous lemmas with trailing markers: digits in the
# Greek stemlib (``le/gw1``) and ``#N`` in the Latin one (``sum#1``).
_TRAILING_HOMONYM = re.compile(r"[\d#]*$")

# Morpheus recognizes elision only with an ASCII apostrophe (a)ll' -> a)lla/);
# editors use the curly variants.
_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'", "\u00b4": "'"})

# Classical editions (e.g. AGLDT) mark elision with a word-final combining comma
# above (U+0313, the ypogegrammeni): δ̓ = δέ before a vowel. Only at end of word —
# mid-word combining marks are letter parts and must be left alone.
_ELISION_COMMA = "\u0313"


def to_beta(text: str) -> str:
    """Convert Unicode Greek to beta code (returns '' on failure)."""
    if not text:
        return ""
    try:
        t = text.translate(_APOSTROPHES)
        if len(t) > 1 and t[-1] == _ELISION_COMMA:
            t = t[:-1] + "'"
        return greek_to_beta_code(t)
    except Exception:
        return ""


def from_beta(text: str) -> str:
    """Convert beta code to Unicode Greek (returns the input on failure)."""
    if not text:
        return ""
    try:
        return beta_code_to_greek(text)
    except Exception:
        return text


def strip_homonym(lemma: str) -> str:
    """Drop Morpheus's homonym disambiguators (``le/gw1`` -> ``le/gw``, ``sum#1`` -> ``sum``)."""
    return _TRAILING_HOMONYM.sub("", lemma or "")


def normalize_lemma(lemma: str) -> str:
    """Canonical key for lemma comparison: NFC, lower-case, artifacts stripped."""
    if not lemma:
        return ""
    return unicodedata.normalize("NFC", strip_homonym(lemma.replace("^", "").replace("_", ""))).lower()
