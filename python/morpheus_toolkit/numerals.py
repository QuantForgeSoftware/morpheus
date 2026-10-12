"""Opt-in synthetic analyses for Greek letter-numeral tokens (Round 9 item 3).

Papyri write numbers as bare Greek letters (β = 2, κθ = 90, λϛ = 36 …); the
stemlib has no entries for them, so they are misses. The bundled table
(``data/papyrus_numerals.json``, built from the PapyGreek treebank's numeral
gold) maps each attested letter-numeral form to its gold lemma; behind the
opt-in flag (``Morpheus(numerals=True)`` / CLI ``--numerals``), tokens Morpheus
cannot analyze get a synthetic analysis (POS N, flagged ``proposed=True``).

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

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_TABLE_PATH = os.path.join(_DATA_DIR, "papyrus_numerals.json")

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


def propose(beta: str) -> Optional[Analysis]:
    """Synthetic numeral analysis for a form in the table, else None."""
    lemma = load_numeral_table().get(beta or "")
    if not lemma:
        return None
    return Analysis(
        lemma=lemma,
        lemma_beta=beta,
        pos="N",
        raw_pos="N",
        stemtype="numeral",
        proposed=True,
    )
