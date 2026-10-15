"""Automatic selection (or blending) of the bundled domain frequency tables.

The toolkit ships several lemma-frequency tables built from different registers
(Koine NT, Apostolic Fathers, papyri, LXX, classical). Ranking quality depends on
which one the caller passes — on PROIEL Herodotus the classical table beats the
Koine one by ~4 points — so forcing the user to choose is a footgun.

This module scores every bundled table against the token candidates of the text
being analyzed and either picks the best-fitting single table or blends them. The
fit uses the candidate lemmas' *rank* inside each table (normalized by table size),
which is robust to the very different corpus sizes behind the tables. Selection is
on by default for Greek (`Morpheus(adaptive_tables=False)` opts out).
"""
from __future__ import annotations

import json
import os
from typing import Dict, Iterable, Optional, Sequence

from .analysis import Analysis
from .beta import normalize_lemma

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# name -> bundled file. "koine" is the default table the API already loads.
TABLE_FILES = {
    "koine": "lemma_frequencies.json",
    "apostolic": "lemma_frequencies_af.json",
    "papyri": "lemma_frequencies_pg.json",
    "lxx": "lemma_frequencies_lxx.json",
    "classical": "lemma_frequencies_grc.json",
}


def _load_file(name: str) -> Dict[str, int]:
    path = os.path.join(_DATA_DIR, TABLE_FILES[name])
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return {
        normalize_lemma(key): value
        for key, value in data.get("frequencies", data).items()
    }


class TableSet:
    """Ensemble of bundled frequency tables with per-text fit selection."""

    def __init__(self, names: Optional[Iterable[str]] = None, min_tokens: int = 40,
                 tables: Optional[Dict[str, Dict[str, int]]] = None):
        if tables is not None:
            self.tables = {
                name: {normalize_lemma(k): v for k, v in table.items()}
                for name, table in tables.items()
            }
        else:
            names = list(names) if names else list(TABLE_FILES)
            self.tables = {
                name: _load_file(name) for name in names if os.path.exists(
                    os.path.join(_DATA_DIR, TABLE_FILES[name])
                )
            }
        self.min_tokens = min_tokens  # below this, keep the default table
        # Rank map per table: lemma -> rank (0 = most frequent), plus size.
        self._ranks: Dict[str, Dict[str, int]] = {}
        for name, table in self.tables.items():
            ordered = sorted(table, key=lambda lem: (-table[lem], lem))
            self._ranks[name] = {lemma: index for index, lemma in enumerate(ordered)}

    def fit_scores(self, candidate_lists: Sequence[Sequence[Analysis]]) -> Dict[str, float]:
        """Mean normalized-rank fit of each table against a text's candidates.

        For each token we take the candidate lemma that ranks highest in the table
        (lowest normalized rank) and average ``1 - normalized_rank`` over tokens
        (0 for misses). The table that best explains the text's vocabulary wins.
        """
        counts = {name: 0.0 for name in self.tables}
        total = 0
        for analyses in candidate_lists:
            total += 1
            for name, ranks in self._ranks.items():
                size = len(ranks) or 1
                best = 1.0
                for analysis in analyses:
                    for variant in analysis.variants():
                        rank = ranks.get(normalize_lemma(variant))
                        if rank is not None:
                            best = min(best, rank / size)
                counts[name] += 1.0 - best
        if total:
            for name in counts:
                counts[name] /= total
        return counts

    def select(self, candidate_lists: Sequence[Sequence[Analysis]]) -> str:
        """Return the best-fitting table name (or the default for short inputs)."""
        if len(candidate_lists) < self.min_tokens or not self.tables:
            return "koine" if "koine" in self.tables else next(iter(self.tables), "koine")
        scores = self.fit_scores(candidate_lists)
        return max(scores, key=scores.get)

    def frequencies(self, name: str) -> Dict[str, int]:
        return self.tables.get(name, {})

    def blend(self, weights: Optional[Dict[str, float]] = None,
              scale: int = 1_000_000) -> Dict[str, int]:
        """Weighted blend of all tables into one frequency dict.

        Each table is normalised to a common mass before weighting, so a small
        corpus (AF) does not dominate a large one (LXX).
        """
        weights = weights or {name: 1.0 for name in self.tables}
        combined: Dict[str, float] = {}
        for name, table in self.tables.items():
            weight = weights.get(name, 0.0)
            if not weight:
                continue
            total = sum(table.values()) or 1
            for lemma, count in table.items():
                combined[lemma] = combined.get(lemma, 0.0) + weight * count / total
        return {lemma: int(round(value * scale)) for lemma, value in combined.items()}


def load_table_set(names: Optional[Iterable[str]] = None) -> TableSet:
    return TableSet(names=names)
