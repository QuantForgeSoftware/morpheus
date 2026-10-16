"""Temperature scaling for the reported analysis confidence.

Morpheus candidates are scored by the ranker and the scores are turned into a
softmax ``confidence``. Those scores are *ordering* scores, not probabilities:
before calibration the top confidence is systematically mis-scaled. This module
loads the fitted temperature for the score path in use (frequency vs learned;
``scripts/calibrate.py``) and applies it. With no calibration file the
temperature is 1.0 (unchanged behavior).
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Sequence

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_calibration() -> Dict[str, float]:
    path = os.path.join(_DATA_DIR, "calibration.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_temperature(learned: bool = False, joint: bool = False) -> float:
    """Return the fitted temperature for the score path in use.

    Three fitted scales exist: the plain frequency path (``temperature``), the
    joint (lemma, POS) path (``temperature_joint``), and the learned path
    (``temperature_learned``). Falls back to the frequency temperature (then to
    1.0) when the requested one has not been fitted.
    """
    data = load_calibration()
    if learned:
        key = "temperature_learned"
    elif joint:
        key = "temperature_joint"
    else:
        key = "temperature"
    value = data.get(key)
    if value is None:
        value = data.get("temperature", 1.0)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 1.0
    return value if value > 0 else 1.0


def load_proposal_priors() -> Dict[str, float]:
    """Per-strategy accuracies for all-proposed tokens (see ``calibrate.py``).

    A token whose candidates are all proposals has a softmax confidence
    *conditional on the generated candidate set*, not P(proposal correct) — and
    a lone proposal always reports 1.0. The fitted priors scale that softmax by
    the measured accuracy of the strategy that produced each candidate.
    """
    data = load_calibration()
    priors = data.get("proposal_priors", {})
    if not isinstance(priors, dict):
        return {}
    out: Dict[str, float] = {}
    for key, value in priors.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def load_pos_reliability(learned: bool = False, joint: bool = False) -> Dict[str, float]:
    """Per-class P(top-1 class correct), fitted by ``scripts/calibrate.py``.

    The class mass alone is peaked for the lemma, not for the class (SBLGNT:
    mean mass ~1.0 while coarse POS accuracy is ~0.79), so the reported POS
    confidence multiplies it by this fitted per-class rate. One table is fitted
    per score path (plain / joint / learned); ``"other"`` is the overall
    accuracy, used for classes without a fitted row.
    """
    data = load_calibration()
    if learned:
        key = "pos_reliability_learned"
    elif joint:
        key = "pos_reliability_joint"
    else:
        key = "pos_reliability"
    table = data.get(key)
    if not isinstance(table, dict):
        table = data.get("pos_reliability", {})
    if not isinstance(table, dict):
        return {}
    out: Dict[str, float] = {}
    for key_name, value in table.items():
        try:
            out[str(key_name)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


# Coarse POS classes for the reported POS confidence: the distinctions the
# evaluators score (the fine RA/RP/RD/RR/RI article-pronoun split is not
# reliably decidable from form; I folds into X, matching the gate's class
# equivalences).
COARSE_POS = {
    "N": "N", "A": "A", "V": "V",
    "RA": "R", "RP": "R", "RD": "R", "RR": "R", "RI": "R",
    "P": "P", "C": "C", "D": "D", "X": "X", "I": "X",
}


def coarse_pos(pos: str) -> str:
    return COARSE_POS.get(pos or "", "?")


def class_masses(classes: Sequence[str], confidences: Sequence[float]) -> List[float]:
    """Confidence mass of each element's class (the POS-confidence estimate).

    ``class_masses[i]`` sums the confidences of the elements sharing element
    ``i``'s class: the estimated probability that the element's class is the
    right class, under the calibrated candidate distribution.
    """
    totals: Dict[str, float] = {}
    for name, confidence in zip(classes, confidences):
        totals[name] = totals.get(name, 0.0) + confidence
    return [totals[name] for name in classes]


def softmax_confidences(scores: Sequence[float], temperature: float = 1.0) -> List[float]:
    """Softmax over scores with a temperature (>1 flattens, <1 sharpens)."""
    if not scores:
        return []
    temp = temperature if temperature and temperature > 0 else 1.0
    top = max(scores)
    weights = [math.exp((score - top) / temp) for score in scores]
    total = sum(weights) or 1.0
    return [weight / total for weight in weights]


def expected_calibration_error(confidences: Sequence[float], correct: Sequence[int],
                               bins: int = 10) -> float:
    """Top-1 expected calibration error: |mean confidence - accuracy| per bin."""
    if not confidences:
        return 0.0
    buckets = [[] for _ in range(bins)]
    for confidence, hit in zip(confidences, correct):
        index = min(int(confidence * bins), bins - 1)
        buckets[index].append((confidence, hit))
    total = len(confidences)
    ece = 0.0
    for bucket in buckets:
        if not bucket:
            continue
        mean_conf = sum(c for c, _ in bucket) / len(bucket)
        accuracy = sum(h for _, h in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(mean_conf - accuracy)
    return ece
