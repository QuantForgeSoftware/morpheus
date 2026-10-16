"""Opt-in context-conditional re-ranking for homograph forms (Round 9 item 2).

Morpheus's candidate sets for a few function-word forms carry several lemmas
(ὃ → ὁ/ὅς, τε → σύ/τε, ἢ → εἰμί/ἠμί/ἤ/ἦ, ...). Global lemma frequency resolves
most of them, but where the gold corpora show a context-dependent split, the
bundled table (``data/homograph_contexts.json``, trained on SBLGNT + AF +
PapyGreek) re-ranks those candidates by P(gold lemma | form, prev POS, next
POS), falling back to the form's marginal gold distribution when the exact
context was not seen in training.

This is strictly opt-in (``Morpheus(use_homograph_context=True)`` / CLI
``--homographs``); with the flag off, no table is loaded and behavior is
byte-identical to before. Greek only.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Optional

from .analysis import Analysis
from .beta import normalize_lemma

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_TABLE_PATH = os.path.join(_DATA_DIR, "homograph_contexts.json")

_table: Optional[dict] = None


def load_homograph_table() -> dict:
    """Load (and cache) the bundled table; empty when absent."""
    global _table
    if _table is None:
        loaded: Dict[str, dict] = {}
        if os.path.exists(_TABLE_PATH):
            with open(_TABLE_PATH, encoding="utf-8") as handle:
                data = json.load(handle)
            for beta, entry in data.get("forms", {}).items():
                loaded[beta] = {
                    "marginal": {normalize_lemma(k): v for k, v in entry["marginal"].items()},
                    "contexts": {
                        ctx: {normalize_lemma(k): v for k, v in counts.items()}
                        for ctx, counts in entry["contexts"].items()
                    },
                }
        _table = loaded
    return _table


def rerank(analyses: List[Analysis], form_beta: str,
           prev_pos: Optional[str], next_pos: Optional[str]) -> List[Analysis]:
    """Re-rank one token's candidates using the context table (no-op when absent)."""
    entry = load_homograph_table().get(form_beta)
    if not entry or len(analyses) < 2:
        return analyses
    ctx_key = f"{prev_pos} {next_pos}" if prev_pos and next_pos else None
    dist = (entry["contexts"].get(ctx_key) if ctx_key else None) or entry["marginal"]
    for analysis in analyses:
        # Canonical lemma only: the variant list also carries the *form* element
        # Morpheus matched, which is not this candidate's lemma.
        analysis.score = math.log1p(dist.get(normalize_lemma(analysis.lemma), 0))
    analyses.sort(key=lambda item: (-item.score, item.lemma))
    return analyses
