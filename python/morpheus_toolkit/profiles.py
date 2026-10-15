"""Named output-convention profiles.

Corpus-specific conventions were previously only available inside the annotation
scripts (``build_morph_lxx.py`` / ``build_morph_af.py``). This module exposes
them as named, reusable transforms on a token's analyses, selected with
``Morpheus(profile="morphgnt")``.

Profiles only rewrite *presentation* (lemma/POS conventions); they never add or
drop candidate analyses.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from .analysis import Analysis
from .beta import to_beta

_ARTICLE_LEMMA = "ὁ"
_ARTICLE_BETA = to_beta(_ARTICLE_LEMMA)


def dictionary_forms(analyses: List[Analysis]) -> List[Analysis]:
    """MorphGNT/LXX dictionary-form convention for the definite article.

    Morpheus lemmatizes article forms under the bare stem (``ο(`` etc.); the
    MorphGNT-style convention groups them all under the nominative ``ὁ`` with
    POS ``RA``. Applied per candidate, so an ambiguous form that also has a
    relative-pronoun (RR) reading keeps both — only the RA candidate is renamed.
    """
    for analysis in analyses:
        if analysis.pos == "RA" and analysis.lemma != _ARTICLE_LEMMA:
            analysis.lemma = _ARTICLE_LEMMA
            analysis.lemma_beta = _ARTICLE_BETA
            analysis.lemma_variants = (_ARTICLE_LEMMA,)
    return analyses


PROFILES: Dict[str, Callable[[List[Analysis]], List[Analysis]]] = {
    "morphgnt": dictionary_forms,
    "lxx": dictionary_forms,
}


def apply_profile(name: str, analyses: List[Analysis]) -> List[Analysis]:
    transform = PROFILES.get((name or "").lower())
    return transform(analyses) if transform and analyses else analyses
