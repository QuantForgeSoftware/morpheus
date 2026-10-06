"""Structured analysis records and the Morpheus -> fine-grained POS mapping."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Tuple

from .beta import from_beta, strip_homonym

ANAL_RE = re.compile(r"<NL>(.*?)</NL>")

# Morphological feature vocabularies (Morpheus emits space-separated tokens;
# combined values are slash-joined, e.g. ``nom/voc/acc`` or ``masc/neut``).
GENDERS = {"masc", "fem", "neut"}
CASES = {"nom", "gen", "dat", "acc", "voc"}
NUMBERS = {"sg", "pl", "dual"}
TENSES = {"pres", "imperf", "fut", "aor", "perf", "plup"}
VOICES = {"act", "mid", "pass", "mp"}
MOODS = {"ind", "subj", "opt", "imper", "inf", "part"}
PERSONS = {"1st", "2nd", "3rd"}
DEGREES = {"comp", "superl"}

CATEGORIES = (
    ("gender", GENDERS),
    ("case", CASES),
    ("number", NUMBERS),
    ("tense", TENSES),
    ("voice", VOICES),
    ("mood", MOODS),
    ("person", PERSONS),
    ("degree", DEGREES),
)


@dataclass
class Analysis:
    """One morphological analysis of a token."""

    lemma: str  # Unicode (homonym digits stripped)
    lemma_beta: str
    pos: str  # fine-grained (V, N, A, P, RA, RP, RD, RR, RI, D, C, X, I)
    raw_pos: str  # Morpheus's coarse POS (N/V/P/...)
    stemtype: str
    features: Dict[str, Tuple[str, ...]] = field(default_factory=dict)
    # Morpheus joins lemma variants with commas (e.g. ``γενέσεω^ς,γένεσις``); keep
    # them all so matching/ranking can use whichever the gold corpus uses.
    lemma_variants: Tuple[str, ...] = ()
    score: float = 0.0

    @property
    def mood(self):
        return self.features.get("mood")

    @property
    def is_participle(self) -> bool:
        return "part" in self.features.get("mood", ())

    def variants(self) -> Tuple[str, ...]:
        return self.lemma_variants or (self.lemma,)

    def matches_lemma(self, gold: str) -> bool:
        from .beta import normalize_lemma

        return any(normalize_lemma(variant) == gold for variant in self.variants())

    def feature_string(self) -> str:
        return " ".join(f"{key}={','.join(values)}" for key, values in self.features.items())

    def to_dict(self) -> dict:
        return {
            "lemma": self.lemma,
            "lemma_variants": list(self.variants()),
            "pos": self.pos,
            "features": {key: list(values) for key, values in self.features.items()},
            "stemtype": self.stemtype,
            "score": round(self.score, 4),
        }


def _features(tokens) -> Dict[str, Tuple[str, ...]]:
    features: Dict[str, Tuple[str, ...]] = {}
    for token in tokens:
        parts = tuple(token.split("/"))
        for name, vocab in CATEGORIES:
            if all(part in vocab for part in parts):
                merged = tuple(dict.fromkeys(features.get(name, ()) + parts))
                features[name] = merged
                break
    return features


def fine_pos(raw_pos: str, stemtype: str) -> str:
    """
    Recover a finer POS from Morpheus's coarse tag plus the stem type.

    Morpheus labels nouns, adjectives, pronouns, articles and prepositions all as
    ``N``; the stem type disambiguates most of them. Adjectives vs nouns remain a
    known ambiguity (both use nominal stems).
    """
    if raw_pos == "V":
        return "V"
    if raw_pos == "P":  # Morpheus tags participles as P
        return "V"
    if raw_pos != "N":
        return raw_pos
    stem = stemtype or ""
    # Exact matches: Morpheus uses these single-word stem types. Substring checks
    # would misfire (`particle` contains `article`, `reg_conj` contains `conj`).
    if stem == "article":
        return "RA"
    if stem == "prep":
        return "P"
    if stem == "adverb":
        return "D"
    if stem == "conj":
        return "C"
    if stem == "particle":
        return "X"
    if stem == "interj":
        return "I"
    if stem == "relative":
        return "RR"
    if stem == "art_adj":
        return "A"
    if "pron" in stem:
        return "RP"
    if stem in {"indecl", "indef"}:
        return "RI"
    return "N"


def parse_perseus_analyses(line: str) -> list[Analysis]:
    """Parse a line of Perseus-format output (possibly several ``<NL>`` records)."""
    analyses: list[Analysis] = []
    for match in ANAL_RE.finditer(line):
        tokens = match.group(1).split()
        if len(tokens) < 2:
            continue
        raw_pos, form = tokens[0], tokens[1]
        rest = tokens[2:]
        stemtype = rest[-1] if rest else ""
        features = _features(rest[:-1] if rest else [])
        # Morpheus emits comma-joined lemma variants and internal beta markers
        # (`^`, `_`) that are not part of the word.
        cleaned = form.replace("^", "").replace("_", "")
        variants_beta = tuple(strip_homonym(part) for part in cleaned.split(",") if part) or (
            strip_homonym(cleaned),
        )
        variants = tuple(from_beta(part) for part in variants_beta)
        # Morpheus prints lemma variants as `form,lemma` (e.g. `ku_ri/ou,ku/rios`);
        # the canonical lemma is the last one.
        analyses.append(
            Analysis(
                lemma=variants[-1],
                lemma_beta=variants_beta[-1],
                pos=fine_pos(raw_pos, stemtype),
                raw_pos=raw_pos,
                stemtype=stemtype,
                features=features,
                lemma_variants=variants,
            )
        )
    return analyses
