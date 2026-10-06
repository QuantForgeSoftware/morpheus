"""
Map a Morpheus analysis to MorphGNT/CCAT POS and parsing codes, so results can be
compared with (or merged into) MorphGNT-style corpora.

Parsing code layout (8 chars): person, tense, voice, mood, case, number, gender,
degree; `-` marks an inapplicable category. E.g. ``3AAI-S--`` (aorist indicative
3rd singular) or ``-PAPNSF-`` (present active participle, nom. sg. fem.).
"""
from __future__ import annotations

from .analysis import Analysis

POS_CODE = {
    "N": "N-",
    "A": "A-",
    "V": "V-",
    "P": "P-",
    "D": "D-",
    "C": "C-",
    "X": "X-",
    "I": "I-",
    "RA": "RA",
    "RP": "RP",
    "RD": "RD",
    "RR": "RR",
    "RI": "RI",
}

PERSON = {"1st": "1", "2nd": "2", "3rd": "3"}
TENSE = {"pres": "P", "imperf": "I", "fut": "F", "aor": "A", "perf": "X", "plup": "Y"}
VOICE = {"act": "A", "mid": "M", "pass": "P", "mp": "M"}
MOOD = {"ind": "I", "imper": "D", "subj": "S", "opt": "O", "inf": "N", "part": "P"}
CASE = {"nom": "N", "gen": "G", "dat": "D", "acc": "A", "voc": "V"}
NUMBER = {"sg": "S", "pl": "P", "dual": "D"}
GENDER = {"masc": "M", "fem": "F", "neut": "N"}
DEGREE = {"comp": "C", "superl": "S"}


def _first(values, table) -> str:
    for value in values or ():
        if value in table:
            return table[value]
    return "-"


def pos_code(analysis: Analysis) -> str:
    """MorphGNT POS code; synthetic proper names are `NP`."""
    if analysis.proposed:
        return "NP"
    return POS_CODE.get(analysis.pos, "N-")


def parsing_code(analysis: Analysis) -> str:
    """The 8-character MorphGNT parsing code."""
    features = analysis.features
    return "".join(
        [
            _first(features.get("person"), PERSON),
            _first(features.get("tense"), TENSE),
            _first(features.get("voice"), VOICE),
            _first(features.get("mood"), MOOD),
            _first(features.get("case"), CASE),
            _first(features.get("number"), NUMBER),
            _first(features.get("gender"), GENDER),
            _first(features.get("degree"), DEGREE),
        ]
    )
