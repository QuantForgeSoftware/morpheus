"""
A POS-bigram Viterbi tagger over Morpheus's candidate analyses.

Morpheus gives no way to choose among its candidates. Frequency ranking chooses
well in isolation; this adds context: it finds the most likely POS sequence with
a bigram model trained on a gold corpus, then promotes each token's best analysis
for the chosen POS.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Optional, Sequence

from .analysis import Analysis

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MISS_TAG = "?"
MISS_EMISSION = -1.0


def load_default_pos_model() -> dict:
    path = os.path.join(_DATA_DIR, "pos_bigram.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class PosTagger:
    def __init__(self, model: dict, emission_weight: float = 3.0, smoothing: float = 0.1):
        self.unigrams: Dict[str, int] = model.get("unigrams", {})
        self.bigrams: Dict[str, Dict[str, int]] = model.get("bigrams", {})
        self.starts: Dict[str, int] = model.get("starts", {})
        self.emission_weight = emission_weight
        self.k = smoothing
        self.vocab = set(self.unigrams) | {MISS_TAG}
        self.v = max(len(self.vocab), 1)
        self.start_total = sum(self.starts.values()) or 1
        self.row_totals = {key: sum(row.values()) for key, row in self.bigrams.items()}

    def _log_start(self, pos: str) -> float:
        return math.log((self.starts.get(pos, 0) + self.k) / (self.start_total + self.k * self.v))

    def _log_transition(self, prev: str, pos: str) -> float:
        row = self.bigrams.get(prev, {})
        total = self.row_totals.get(prev, 0)
        return math.log((row.get(pos, 0) + self.k) / (total + self.k * self.v))

    def tag(self, token_analyses: Sequence[Sequence[Analysis]]) -> List[Optional[Analysis]]:
        """Return the chosen analysis for each token (None for misses)."""
        # Per token, keep the best-scoring candidate for each POS.
        states: List[Dict[str, Optional[Analysis]]] = []
        for analyses in token_analyses:
            by_pos: Dict[str, Optional[Analysis]] = {}
            for analysis in analyses:
                current = by_pos.get(analysis.pos)
                if current is None or analysis.score > current.score:
                    by_pos[analysis.pos] = analysis
            states.append(by_pos or {MISS_TAG: None})

        back: List[Dict[str, str]] = []
        prev_scores: Dict[str, float] = {}
        for index, by_pos in enumerate(states):
            current: Dict[str, float] = {}
            pointer: Dict[str, str] = {}
            for pos, analysis in by_pos.items():
                emission = (analysis.score * self.emission_weight) if analysis is not None else MISS_EMISSION
                if index == 0:
                    current[pos] = self._log_start(pos) + emission
                else:
                    best_value = None
                    best_prev = pos
                    for prev_pos, prev_score in prev_scores.items():
                        value = prev_score + self._log_transition(prev_pos, pos)
                        if best_value is None or value > best_value:
                            best_value, best_prev = value, prev_pos
                    current[pos] = best_value + emission
                    pointer[pos] = best_prev
            back.append(pointer)
            prev_scores = current

        last = max(prev_scores, key=prev_scores.get)
        path = [last]
        for index in range(len(states) - 1, 0, -1):
            last = back[index][last]
            path.append(last)
        path.reverse()

        return [by_pos.get(pos) for by_pos, pos in zip(states, path)]

    def rerank(self, token_analyses: List[List[Analysis]]) -> None:
        chosen = self.tag(token_analyses)
        for analyses, best in zip(token_analyses, chosen):
            if best is None:
                continue
            analyses.sort(key=lambda analysis: (analysis is not best, -analysis.score))
