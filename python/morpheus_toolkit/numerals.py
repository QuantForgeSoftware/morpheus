"""Opt-in synthetic analyses for Greek letter-numeral tokens (Round 9 item 3).

Papyri write numbers as bare Greek letters (β = 2, κθ = 90, λϛ = 36 …); the
stemlib has no entries for them, so they are misses. The bundled table
(``data/papyrus_numerals.json``, built from the PapyGreek treebank's numeral
gold) maps each attested letter-numeral form to its gold lemma; behind the
opt-in flag (``Morpheus(numerals=True)`` / CLI ``--numerals``), tokens Morpheus
cannot analyze get a synthetic analysis (POS N, flagged ``proposed=True``).

Round 17 item 2 adds a compositional rule beside the table: a run of numeral
letters with **no vowel** is a number (χμγ = 643, ψπ = 780, ρξβ = 162) — real
Greek words always contain a vowel, so vowel-less runs are numerals,
abbreviations, or truncations, all of which get the table's surface-lemma
convention. The numeric value is carried in the ``value`` feature. The table
stays the exception list (case fallback, decimal-annotated lemmas like 1300).

Only UNANALYZED tokens are touched — analyzed forms are never overridden, so
real one- or two-letter words and particles in other corpora stay safe. Greek
only; with the flag off no table is loaded and behavior is byte-identical to
before.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from .analysis import Analysis
from .beta import from_beta

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_TABLE_PATH = os.path.join(_DATA_DIR, "papyrus_numerals.json")

# The 27 letter-numerals (α = 1 … ϡ = 900) in beta code. Stigma, koppa and
# sampi pass through ``to_beta`` unchanged, so they appear as themselves.
_NUMERAL_LETTERS = frozenset("abgdezhqiklmncoprstufxywϛϟϙϡ")
_VOWELS = frozenset("aehiouw")
_LETTER_VALUES = {
    "a": 1, "b": 2, "g": 3, "d": 4, "e": 5, "ϛ": 6, "z": 7, "h": 8, "q": 9,
    "i": 10, "k": 20, "l": 30, "m": 40, "n": 50, "c": 60, "o": 70, "p": 80,
    "ϟ": 90, "ϙ": 90,
    "r": 100, "s": 200, "t": 300, "u": 400, "f": 500, "x": 600, "y": 700,
    "w": 800, "ϡ": 900,
}

_table: Optional[dict] = None


def load_numeral_table() -> dict:
    """Load (and cache) the bundled table; empty when absent."""
    global _table
    if _table is None:
        loaded: dict[str, str] = {}
        if os.path.exists(_TABLE_PATH):
            with open(_TABLE_PATH, encoding="utf-8") as handle:
                data = json.load(handle)
            for beta, entry in data.get("forms", {}).items():
                loaded[beta] = entry["lemma"]
        _table = loaded
    return _table


def propose(beta: str, surface: Optional[str] = None) -> Optional[Analysis]:
    """Synthetic numeral analysis for a form, else None.

    Numeral case is meaningless (α = Α = 1), so single letters fall back across
    case in both directions: a lowercase letter missing from the table resolves
    via its capital entry (beta ``*`` prefix; recovers α and ε, whose capital
    forms are attested), and a capital single letter the table lacks resolves
    via its lowercase entry, re-capitalized (Β → β → Β). Forms
    outside the table are checked against the compositional rule: a vowel-less
    run of at least two numeral letters is a number, proposed with the surface
    as its lemma (the table's convention) and the letter sum as its value.
    ``surface`` is the original Unicode spelling; when it is absent — or the
    same as the beta key, as in ``analyze_beta`` calls — the lemma is
    reconstructed from the beta code.
    """
    table = load_numeral_table()
    key = beta or ""
    lemma = table.get(key)
    if lemma is None and len(key) == 1 and key.isalpha():
        lemma = table.get("*" + key.lower())
    if lemma is None and len(key) == 2 and key.startswith("*"):
        # Case is meaningless in both directions: a capital single letter the
        # table lacks falls back to its lowercase entry (Β → β), capitalized
        # back to match the surface's case.
        lowered = table.get(key[1:].lower())
        if lowered:
            lemma = lowered[:1].upper() + lowered[1:]
    if not lemma:
        letters = key[1:] if key.startswith("*") else key
        if (len(letters) >= 2
                and all(letter in _NUMERAL_LETTERS for letter in letters)
                and not any(letter in _VOWELS for letter in letters)):
            value = sum(_LETTER_VALUES.get(letter, 0) for letter in letters)
            # Beta-input callers (``analyze_beta``) have no Unicode surface:
            # reconstruct it, turning the word-final ς of from_beta back to σ.
            display = surface if surface and surface != beta else from_beta(key).replace("ς", "σ")
            return Analysis(
                lemma=display,
                lemma_beta=beta,
                pos="N",
                raw_pos="N",
                stemtype="numeral",
                features={"value": (str(value),)},
                proposed=True,
            )
        return None
    return Analysis(
        lemma=lemma,
        lemma_beta=beta,
        pos="N",
        raw_pos="N",
        stemtype="numeral",
        proposed=True,
    )
