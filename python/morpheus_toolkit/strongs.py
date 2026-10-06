"""Map Morpheus lemmas to Strong's numbers (Greek)."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, Optional

from .beta import normalize_lemma

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


@lru_cache(maxsize=1)
def load_default_strongs() -> Dict[str, int]:
    path = os.path.join(_DATA_DIR, "lemma_strongs.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("strongs", data)


@lru_cache(maxsize=1)
def _normalized() -> Dict[str, int]:
    return {normalize_lemma(lemma): number for lemma, number in load_default_strongs().items()}


def strongs_for(lemma: str) -> Optional[int]:
    """The Strong's number for a Greek lemma, or None when unknown."""
    if not lemma:
        return None
    return _normalized().get(normalize_lemma(lemma))
