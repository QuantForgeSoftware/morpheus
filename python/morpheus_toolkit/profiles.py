"""Named output-convention profiles.

Corpus-specific conventions were previously only available inside the annotation
scripts (``build_morph_lxx.py`` / ``build_morph_af.py``). This module exposes
them as named, reusable transforms on a token's analyses, selected with
``Morpheus(profile="morphgnt")`` — several can be combined with a comma
(``"morphgnt,base-lemmas"``), applied left to right.

Profiles only rewrite *presentation* (lemma/POS conventions); they never add or
drop candidate analyses.

Two kinds exist:

- *static* profiles (``morphgnt``, ``lxx`` = dictionary forms) rewrite a fixed
  convention;
- *analyzer-guarded* profiles (``base-lemmas``) consult the analyzer's own
  reference vocabulary, so the rewrite only fires when the result is an attested
  word (a preverb is stripped from a compound verb only when the remainder is a
  verb the analyzer knows).
"""
from __future__ import annotations

import unicodedata
from typing import Callable, Dict, List, Optional, Set

from .analysis import Analysis
from .beta import normalize_lemma, to_beta

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


# --- base-lemmas (analyzer-guarded) ------------------------------------------
#
# Reference corpora lemmatize compound verbs to the base verb (the preverb goes
# to a separate prefix column). With this profile we do the same: strip a
# leading preverb from a verb lemma when the remainder is itself an attested
# verb — the guard that prevents stripping preverb-like strings off words that
# are not compounds.
PREVERBS = ["ανα", "αντι", "απο", "αφ", "δια", "εκ", "εξ", "εν", "υπερ",
            "κατα", "παρα", "περι", "προσ", "συν", "υπο"]  # accents stripped

# Contracted/assimilated compounds lose the preverb's final vowel (δια+ἔρχομαι →
# διέρχομαι), so head-stripping misses them. Tail-matching recovers them, but a
# simplex can end in another verb's string (χωρίζω ~ ρίζω) — so a tail is
# accepted only when what precedes it is an attested preverb remnant. The set
# below is the remnants observed in the LXX (tmp/lxx/count_compounds.py) plus
# the full preverbs; hyphenated entries are Morpheus's explicit compound notation.
PREVERB_REMNANTS: Set[str] = {
    "επι", "κατ", "εισ", "αν", "απ", "παρ", "επ", "καθ", "δι", "εμ", "προ",
    "εξαπο", "υπ", "συμ", "παρεμ", "εγκατα", "συγ", "μετα", "συλ", "εκ-",
    "εν-", "ανταπο", "εφ", "κατα-", "διαρ", "ανθ", "εγ", "απορ", "συ",
    "προκατα", "συν-", "αποκαθ", "μεθ", "διαν", "υφ", "μετ", "απο-",
    "ανα-", "εξαν", "επι-",
} | set(PREVERBS)


def _deacc(s: str) -> str:
    """Lowercase and strip all diacritics (incl. breathings)."""
    return "".join(ch for ch in unicodedata.normalize("NFD", s.lower())
                   if not unicodedata.combining(ch))


class BaseLemmas:
    """Compound verbs lemmatize to the base verb, guarded by known verbs.

    The vocabulary is the analyzer's joint (lemma, POS) table when it has one
    (e.g. the LXX annotation driver's table), else the bundled Koine joint
    table: a lemma counts as a known verb when any of its joint POS values
    starts with ``V``. The base lemma is taken in the table's canonical
    accentuation.
    """

    def __init__(self, analyzer=None):
        self._analyzer = analyzer
        self._known: Optional[Dict[str, str]] = None
        self._by_len: List[str] = []
        self._memo: Dict[str, Optional[str]] = {}

    def _vocabulary(self) -> Dict[str, str]:
        if self._known is not None:
            return self._known
        joint = {}
        ranker = getattr(self._analyzer, "ranker", None)
        if ranker is not None and getattr(ranker, "joint", None):
            joint = ranker.joint
        if not joint:
            from .ranking import load_default_joint_frequencies

            joint = load_default_joint_frequencies()
        known: Dict[str, str] = {}
        for lemma, row in joint.items():
            if any(str(pos).startswith("V") for pos in row):
                known[_deacc(lemma)] = normalize_lemma(lemma)
        self._known = known
        self._by_len = sorted(known, key=len, reverse=True)
        return known

    def base_of(self, lemma: str) -> Optional[str]:
        """Base verb for a compound-verb lemma (memoized), or None."""
        d = _deacc(lemma)
        if d in self._memo:
            return self._memo[d]
        known = self._vocabulary()
        base: Optional[str] = None
        # 1) intact preverb at the head
        for pv in PREVERBS:
            if d.startswith(pv) and len(d) > len(pv):
                rest = d[len(pv):]
                for cand in (rest, rest.replace("ει", "ε"), rest.replace("ου", "ο")):
                    base = known.get(cand)
                    if base is not None:
                        break
                if base is not None:
                    break
        # 2) contracted/assimilated: longest tail that is an attested verb AND is
        #    preceded by a preverb remnant (guards against simplexes like χωρίζω)
        if base is None and len(d) >= 6:
            for v in self._by_len:
                if len(v) < 4 or len(d) <= len(v) + 1:
                    continue
                if d.endswith(v) and d[:-len(v)] in PREVERB_REMNANTS:
                    base = known[v]
                    break
        self._memo[d] = base
        return base

    def __call__(self, analyses: List[Analysis]) -> List[Analysis]:
        for analysis in analyses:
            if not (analysis.pos or "").startswith("V"):
                continue
            base = self.base_of(analysis.lemma)
            if base is None or normalize_lemma(base) == normalize_lemma(analysis.lemma):
                continue
            analysis.lemma = base
            analysis.lemma_beta = to_beta(base)
            analysis.lemma_variants = (base,)
        return analyses


_STATIC_PROFILES: Dict[str, Callable[[List[Analysis]], List[Analysis]]] = {
    "morphgnt": dictionary_forms,
    "lxx": dictionary_forms,
}

# Selectable names (static + guarded); used by the CLI for validation.
PROFILE_NAMES = sorted(_STATIC_PROFILES) + ["base-lemmas"]

_STANDALONE_BASE_LEMMAS: Optional[BaseLemmas] = None


def apply_profile(name: str, analyses: List[Analysis],
                  analyzer=None) -> List[Analysis]:
    """Apply one profile (or a comma-separated combination, left to right).

    Unknown names are a no-op (existing behavior); ``analyzer`` supplies the
    vocabulary for guarded profiles and caches their state per instance.
    """
    if not analyses:
        return analyses
    for part in (name or "").lower().split(","):
        part = part.strip()
        if not part:
            continue
        if part in _STATIC_PROFILES:
            _STATIC_PROFILES[part](analyses)
            continue
        if part == "base-lemmas":
            transform = None
            if analyzer is not None:
                cache = analyzer.__dict__.setdefault("_profile_transforms", {})
                transform = cache.get(part)
                if transform is None:
                    transform = cache[part] = BaseLemmas(analyzer)
            else:
                global _STANDALONE_BASE_LEMMAS
                if _STANDALONE_BASE_LEMMAS is None:
                    _STANDALONE_BASE_LEMMAS = BaseLemmas()
                transform = _STANDALONE_BASE_LEMMAS
            transform(analyses)
    return analyses
