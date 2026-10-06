"""Ranking of Morpheus's candidate analyses.

Morpheus returns every analysis its stems/endings permit, ordered alphabetically
by lemma (see `CompAnals` in the C source). That order is linguistically
meaningless: for ``θεοῦ`` the verb θεάομαι sorts before the noun θεός. This module
re-ranks candidates by (1) lemma frequency in a reference corpus and (2) a few
lightweight contextual cues.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, Iterable, Optional

from .analysis import Analysis
from .beta import normalize_lemma

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Slight preference for open-class words when frequencies tie.
POS_PRIOR = {
    "V": 0.00,
    "N": 0.20,
    "A": 0.10,
    "RA": 0.20,
    "RP": 0.10,
    "RD": 0.05,
    "RR": 0.05,
    "RI": 0.00,
    "D": 0.10,
    "P": 0.15,
    "C": 0.05,
    "X": 0.00,
    "I": 0.00,
}

NOMINAL = {"N", "A", "RA", "RP", "RD", "RR", "RI"}


def load_default_frequencies() -> Dict[str, int]:
    """Load the bundled Koine lemma-frequency table (empty when absent)."""
    path = os.path.join(_DATA_DIR, "lemma_frequencies.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("frequencies", data)


def context_bonus(analysis: Analysis, prev_pos: Optional[str], next_pos: Optional[str]) -> float:
    """Small contextual adjustment based on the neighbouring tokens' chosen POS."""
    bonus = 0.0
    finite_verb = analysis.pos == "V" and not analysis.is_participle
    if prev_pos == "RA":
        if analysis.pos in {"N", "A"}:
            bonus += 0.30
        elif finite_verb:
            bonus -= 0.30
    if prev_pos == "P":  # preposition governs a nominal
        if analysis.pos in {"N", "A"}:
            bonus += 0.20
        elif finite_verb:
            bonus -= 0.20
    if analysis.is_participle and prev_pos in {"RA", "N", "A"}:
        bonus += 0.10
    return bonus


class Ranker:
    def __init__(self, frequencies: Optional[Dict[str, int]] = None, use_context: bool = False):
        self.frequencies = {normalize_lemma(key): value for key, value in (frequencies or {}).items()}
        self.max_frequency = max(self.frequencies.values(), default=1)
        self.log_max = math.log1p(self.max_frequency)
        self.use_context = use_context

    def frequency_score(self, analysis: Analysis) -> float:
        frequency = max(
            (self.frequencies.get(normalize_lemma(variant), 0) for variant in analysis.variants()),
            default=0,
        )
        return math.log1p(frequency) / self.log_max if self.log_max else 0.0

    def score(self, analysis: Analysis) -> float:
        return self.frequency_score(analysis) + POS_PRIOR.get(analysis.pos, 0.0) * 0.5

    def rank(self, analyses: Iterable[Analysis]) -> list[Analysis]:
        ranked = list(analyses)
        for analysis in ranked:
            analysis.score = self.score(analysis)
        ranked.sort(key=lambda item: (-item.score, item.lemma))
        return ranked

    def rerank_with_context(self, token_analyses: list[list[Analysis]]) -> None:
        """Second pass: adjust each token's candidates using the neighbours' current top POS."""
        tops = [analyses[0].pos if analyses else None for analyses in token_analyses]
        for index, analyses in enumerate(token_analyses):
            prev_pos = tops[index - 1] if index > 0 else None
            next_pos = tops[index + 1] if index + 1 < len(tops) else None
            for analysis in analyses:
                analysis.score += context_bonus(analysis, prev_pos, next_pos)
            analyses.sort(key=lambda item: (-item.score, item.lemma))
