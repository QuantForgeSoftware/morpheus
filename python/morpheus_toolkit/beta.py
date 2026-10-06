"""Unicode <-> beta-code conversion and lemma normalization."""
from __future__ import annotations

import re
import unicodedata

from beta_code import beta_code_to_greek, greek_to_beta_code

_TRAILING_HOMONYM = re.compile(r"\d+$")


def to_beta(text: str) -> str:
    """Convert Unicode Greek to beta code (returns '' on failure)."""
    if not text:
        return ""
    try:
        return greek_to_beta_code(text)
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
    """Drop Morpheus's homonym disambiguator digits (``le/gw1`` -> ``le/gw``)."""
    return _TRAILING_HOMONYM.sub("", lemma or "")


def normalize_lemma(lemma: str) -> str:
    """Canonical key for lemma comparison: NFC, lower-case, artifacts stripped."""
    if not lemma:
        return ""
    return unicodedata.normalize("NFC", strip_homonym(lemma.replace("^", "").replace("_", ""))).lower()
