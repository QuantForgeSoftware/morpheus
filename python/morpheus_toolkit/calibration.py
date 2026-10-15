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


def load_temperature(learned: bool = False) -> float:
    """Return the fitted temperature for the frequency or learned score path.

    Falls back to the frequency temperature (then to 1.0) when the learned
    temperature has not been fitted.
    """
    data = load_calibration()
    key = "temperature_learned" if learned else "temperature"
    value = data.get(key)
    if value is None:
        value = data.get("temperature", 1.0)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 1.0
    return value if value > 0 else 1.0


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
