"""Learned re-ranking of Morpheus's candidate analyses (opt-in).

Morpheus returns every analysis a form permits, alphabetically by lemma. The
bundled :class:`~morpheus_toolkit.ranking.Ranker` re-orders them by lemma
frequency (plus a hand-built POS prior); this module adds a *learned* model on
top of the same candidates.

The model is a linear (averaged-perceptron) ranker over candidate features that
frequency ranking does not see — fine POS, stem type, the candidate's frequency
*rank*, and POS interactions with the neighbouring tokens. Lemma frequency is
itself a feature, so the learned model starts from the frequency signal and can
only add to it (subject to generalization).

Trained on commit-safe gold only; see ``scripts/build_learned_model.py``. On by
default for Greek; pass ``use_learned=False`` (CLI ``--no-learned``) and no model
is loaded.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Optional, Sequence, Tuple

from .analysis import Analysis
from .beta import from_beta, normalize_lemma

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MISS_TAG = "?"
# Closed-class POS: their neighbours' *lemma* is informative and bounded, so we
# add lemma-context features only for these (avoids an unbounded feature space).
CLOSED_POS = {"RA", "RP", "RR", "RD", "P", "C", "D", "X"}


def load_default_model() -> dict:
    path = os.path.join(_DATA_DIR, "learned_reranker.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _freq_bucket(log_freq: float) -> str:
    """Coarse bucket for a lemma's log frequency (0 = unseen)."""
    if log_freq <= 0:
        return "0"
    if log_freq < 1:
        return "1"
    if log_freq < 2:
        return "2"
    if log_freq < 3:
        return "3"
    if log_freq < 4:
        return "4"
    if log_freq < 5:
        return "5"
    if log_freq < 6:
        return "6"
    return "7+"


class LearnedRanker:
    """Linear ranker over candidate features; mirrors the training feature set."""

    def __init__(self, model: dict, frequencies: Optional[Dict[str, int]] = None,
                 joint: Optional[Dict[str, Dict[str, int]]] = None):
        self.weights: Dict[str, float] = model.get("weights", {})
        self.frequencies = {
            normalize_lemma(key): value for key, value in (frequencies or {}).items()
        }
        self.joint = {normalize_lemma(key): row for key, row in (joint or {}).items()}
        # Lemma-context features (neighbour's closed-class lemma). Off unless the
        # model was trained with them: measured to overfit / propagate context
        # noise, so the shipped model leaves them off (see todo.md Item 3).
        self.use_lemma_context = bool(model.get("lemma_context"))
        # Precomputed feature vocabulary (from training) is informational; unseen
        # features simply score 0.

    # -- feature extraction (shared with the trainer) -----------------------
    def _best_frequency(self, analysis: Analysis) -> float:
        """Frequency of the candidate's canonical lemma.

        Not the max over ``variants()``: the leading variants are the *forms*
        the entry matched (see ``Ranker.frequency_score``), so a form element
        would credit the candidate with another word's frequency.
        """
        return self.frequencies.get(normalize_lemma(analysis.lemma), 0)

    def _best_joint(self, analysis: Analysis) -> int:
        row = self.joint.get(normalize_lemma(analysis.lemma))
        return row.get(analysis.pos, 0) if row else 0

    def features(
        self,
        analysis: Analysis,
        surface_beta: str,
        prev: Optional[Tuple[str, str]],
        next_: Optional[Tuple[str, str]],
        rank: int,
    ) -> Dict[str, float]:
        pos = analysis.pos or "?"
        prev_pos, prev_lemma = prev if prev else ("<s>", None)
        next_pos, next_lemma = next_ if next_ else ("<e>", None)
        log_freq = math.log1p(self._best_frequency(analysis))
        feats = {
            "bias": 1.0,
            f"pos={pos}": 1.0,
            f"stem={analysis.stemtype or '?'}": 1.0,
            f"freq={_freq_bucket(log_freq)}": 1.0,
            f"rank={min(rank, 4)}": 1.0,
            f"prev={prev_pos}": 1.0,
            f"next={next_pos}": 1.0,
            f"prev*pos={prev_pos}|{pos}": 1.0,
            f"next*pos={next_pos}|{pos}": 1.0,
        }
        # Lemma context, but only from closed-class neighbours: e.g. ἐγώ/σύ before a
        # verb constrains person, an article constrains a nominal reading. Bounded
        # because closed-class lemmas are few.
        if self.use_lemma_context and prev_pos in CLOSED_POS and prev_lemma:
            feats[f"plem={prev_lemma}"] = 1.0
            feats[f"plem*pos={prev_lemma}|{pos}"] = 1.0
        if self.use_lemma_context and next_pos in CLOSED_POS and next_lemma:
            feats[f"nlem={next_lemma}"] = 1.0
            feats[f"nlem*pos={next_lemma}|{pos}"] = 1.0
        if self.joint:
            feats[f"joint={_freq_bucket(math.log1p(self._best_joint(analysis)))}"] = 1.0
        # Morphological features (person/number/tense/mood/voice/case/gender/degree).
        # Without these the model cannot separate same-POS, same-lemma readings
        # (e.g. εἰμί imperfect 3sg vs 1sg), which is the largest residual class.
        for name, values in analysis.features.items():
            for value in values:
                feats[f"f={name}={value}"] = 1.0
        # Does the candidate lemma equal the token surface? (nominal readings on an
        # undeclined surface are common; helps nominative vs oblique homographs.)
        try:
            surfaced = normalize_lemma(from_beta(surface_beta))
        except Exception:  # pragma: no cover - defensive
            surfaced = ""
        if surfaced and normalize_lemma(analysis.lemma) == surfaced:
            feats["lemma=surface"] = 1.0
        return feats

    def score(self, feats: Dict[str, float]) -> float:
        weights = self.weights
        return sum(value * weights.get(name, 0.0) for name, value in feats.items())

    def rank(self, analyses: Sequence[Analysis], surface_beta: str,
             prev: Optional[Tuple[str, str]] = None,
             next_: Optional[Tuple[str, str]] = None) -> List[Analysis]:
        """Rank one token's candidates by the learned score (frequency breaks ties)."""
        # Rank by bundled frequency first, so the `rank=` feature is meaningful.
        ordered = sorted(
            analyses,
            key=lambda a: (-self._best_frequency(a), a.lemma),
        )
        scored: List[Tuple[float, float, str, Analysis]] = []
        for index, analysis in enumerate(ordered):
            feats = self.features(analysis, surface_beta, prev, next_, index)
            analysis.score = self.score(feats)
            scored.append((analysis.score, self._best_frequency(analysis), analysis.lemma, analysis))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return [item[3] for item in scored]

    def rank_sequence(self, tokens: List[Tuple[str, List[Analysis]]]) -> List[List[Analysis]]:
        """Rank a whole sequence; context = neighbours' frequency-ranked top-1.

        Uses the model itself for the final ordering, but takes context (POS and,
        for closed-class words, lemma) from the frequency ranking so training and
        inference see the same distribution (no teacher forcing on gold tags).
        """
        tops: List[Optional[Tuple[str, str]]] = []
        for _, analyses in tokens:
            if analyses:
                best = max(analyses, key=lambda a: (self._best_frequency(a), a.lemma))
                tops.append((best.pos, normalize_lemma(best.lemma)))
            else:
                tops.append(None)
        ranked: List[List[Analysis]] = []
        for index, (beta, analyses) in enumerate(tokens):
            if not analyses:
                ranked.append([])
                continue
            prev = tops[index - 1] if index > 0 else None
            next_ = tops[index + 1] if index + 1 < len(tops) else None
            ranked.append(self.rank(analyses, beta, prev, next_))
        return ranked
