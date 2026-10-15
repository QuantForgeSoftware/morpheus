"""Recovery proposals for tokens Morpheus cannot analyze (Round 16).

Documentary and verse texts spell words in ways the stemlib does not contain:
itacism (ἥμυσυ for ἥμισυ), consonant alternation (βοιηθὸν for βοηθόν),
gemination, a dropped final -ν, or names in an oblique case the stemlib cannot
reach (Δωρίωνος for Δωρίων). Morpheus returns nothing for such tokens; this
module generates bounded, *generic* normalization candidates for them — no
corpus data involved — which the API re-analyzes against the stemlib:

- :func:`spelling_variants` — orthographic normalization candidates from the
  standard Greek alternations: vowel classes ι/ει/η/υ/οι/υι/ου, ε/αι, ο/ω;
  consonant classes τ/δ/θ, κ/γ/χ, π/β/φ; geminate simplification/doubling;
  documentary ο/οι, ει/ε, ζ/σ and μψ/ψ; the final -ν/-ς toggle including
  sandhi spellings (μὲγ → μέν, ἐὰμ → ἐάν); and dropped iota subscripts restored
  on single η positions (:func:`subscript_variants`). Closest-first (single
  substitutions before pairwise), deterministic, capped.
- :func:`name_candidates` — case-ending → nominative candidates for name-like
  surfaces (Δωρίωνος → Δωρίων, Ἀχιλλᾶτος → Ἀχιλλᾶς, Σωτέλῃ → Σωτέλης,
  Χοινώθμεως → Χοινωθμις).

Both fire only on tokens with NO analyses (like ``numerals``); analyzed tokens
are never touched, so the passes cannot change existing output. Proposals are
flagged ``proposed=True`` and record the normalization candidate in
``recovered_from``.
"""
from __future__ import annotations

import unicodedata
from dataclasses import replace
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

from .analysis import Analysis
from .beta import normalize_lemma, to_beta

# i-sound interchange first (longest digraphs before single letters), then the
# e- and o-classes. Documentary ο/οι is handled as a global rule below because
# οι is already claimed by the i-class.
VOWEL_CLASSES: Tuple[Tuple[str, ...], ...] = (
    ("υι", "οι", "ει", "η", "υ", "ι", "ου"),
    ("αι", "ε"),
    ("ω", "ο"),
)
CONSONANT_CLASSES: Tuple[Tuple[str, ...], ...] = (
    ("τ", "δ", "θ"),
    ("κ", "γ", "χ"),
    ("π", "β", "φ"),
)
GEMINATES = ("ρρ", "σσ", "ττ", "λλ", "μμ", "νν", "ππ", "κκ")
DOUBLED = ("ρ", "σ", "τ")
# Whole-word substitutions that are not per-position classes: documentary ο/οι
# and ει/ε interchanges, ζ/σ (ζμῆνος for σμῆνος), and μψ/ψ cluster
# simplification (ἀντιλήμψεως for ἀντιλήψεως).
GLOBAL_RULES = (("οι", "ο"), ("ει", "ε"), ("ζ", "σ"), ("μψ", "ψ"))

# Case-ending -> nominative replacements (longest suffixes first), applied to
# the unaccented surface (which uses σ, not final ς, after normalize()).
# Replacement endings use ς so candidates match the lemma conventions of
# normalize_lemma and the frequency tables. Evidence: PapyGreek miss profile
# (Round 16) plus standard declension — -ωνος/-ωνι for third-declension -ων
# names, -ατος/-ατι for -ᾶς names, -ιδος/-ιδει/-ιδι/-ιδου for -ίδης names, the
# common oblique endings of o- and a-stems, and the -ιον diminutive accusative.
NAME_RULES: Tuple[Tuple[str, str], ...] = (
    ("ιδοσ", "ιδης"),
    ("ιδει", "ιδης"),
    ("ιδι", "ιδης"),
    ("ιδου", "ιδης"),
    ("εωσ", "ις"),
    ("ατοσ", "ας"),
    ("ατι", "ας"),
    ("ωνοσ", "ων"),
    ("ωνι", "ων"),
    ("ωνα", "ων"),
    ("ιοσ", "ις"),
    ("ιου", "ις"),
    ("ιω", "ις"),
    ("ιν", "ιον"),
    ("ουσ", "ος"),
    ("ου", "ος"),
    ("ον", "ος"),
    ("ω", "ος"),
    ("η", "ης"),
    ("ει", "ης"),
    ("ει", "ις"),
    ("αν", "ας"),
    ("ην", "ης"),
    ("ι", "ις"),
    ("ι", "ης"),
)

SPELLING_CAP = 48
NAME_CAP = 16


def strip_accents(text: str) -> str:
    """Remove combining diacritics (accents, breathings, iota subscript)."""
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(c for c in decomposed if not 0x0300 <= ord(c) <= 0x036F)
    )


def normalize(form: str) -> str:
    """Unaccented, lower-case, letters-only surface used for candidate search."""
    letters = strip_accents(form).lower().replace("ς", "σ")
    return "".join(
        c for c in letters
        if c.isalpha() and unicodedata.category(c) != "Lm"  # drop ʼ (modifier letter)
    )


def _slots(form: str) -> List[Tuple[int, int, Tuple[str, ...]]]:
    """Interchangeable positions: (start, end, alternative spellings)."""
    slots: List[Tuple[int, int, Tuple[str, ...]]] = []
    index = 0
    while index < len(form):
        match = None
        for cls in VOWEL_CLASSES + CONSONANT_CLASSES:
            for member in cls:
                if form.startswith(member, index):
                    match = (
                        index,
                        index + len(member),
                        tuple(other for other in cls if other != member),
                    )
                    break
            if match:
                break
        if match:
            slots.append(match)
            index = match[1]
        else:
            index += 1
    return slots


def _substitute(form: str, substitutions: List[Tuple[int, int, str]]) -> str:
    for start, end, replacement in sorted(substitutions, reverse=True):
        form = form[:start] + replacement + form[end:]
    return form


def _display(form: str) -> str:
    """Word-final σ back to ς (cosmetic; β-code treats them alike)."""
    return form[:-1] + "ς" if form.endswith("σ") else form


def spelling_variants(form: str, cap: int = SPELLING_CAP) -> List[str]:
    """Bounded orthographic normalization candidates, closest-first.

    Tier 1: one substitution, geminate simplification/doubling, the global
    ο/οι rule, and the final -ν/-ς toggle. Tier 2: two substitutions. Empty
    for forms shorter than two letters (single letters belong to ``numerals``).
    """
    base = normalize(form)
    if len(base) < 2:
        return []
    slots = _slots(base)
    candidates: List[str] = []
    seen = set()

    def add(candidate: str) -> None:
        candidate = _display(candidate)
        if candidate and candidate != _display(base) and candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)

    for start, end, alternatives in slots:
        for alternative in alternatives:
            add(_substitute(base, [(start, end, alternative)]))
    for geminate in GEMINATES:
        if geminate in base:
            add(base.replace(geminate, geminate[0]))
    for letter in DOUBLED:
        if letter in base:
            add(base.replace(letter, letter * 2))
    for source, target in GLOBAL_RULES:
        if source in base:
            add(base.replace(source, target))
    if base.endswith("ν"):
        add(base[:-1])
    elif base.endswith("σ"):
        add(base[:-1] + "ν")
    elif base.endswith("γ") or base.endswith("μ"):
        add(base[:-1] + "ν")  # sandhi spelling: μὲγ/ἐὰμ for μέν/ἐάν
    else:
        add(base + "ν")

    for (start1, end1, alts1), (start2, end2, alts2) in combinations(slots, 2):
        for alt1 in alts1:
            for alt2 in alts2:
                add(_substitute(base, [(start1, end1, alt1), (start2, end2, alt2)]))
                if len(candidates) >= cap:
                    break
            if len(candidates) >= cap:
                break
        if len(candidates) >= cap:
            break
    return candidates[:cap]


def subscript_variants(form: str) -> List[str]:
    """Restore a dropped iota subscript on each single η position.

    Documentary spellings regularly omit the iota subscript, and ``normalize``
    strips the combining mark, so a variant like υγιαινης no longer matches the
    subjunctive paradigm entry the stemlib keeps as υγιαινῃς (the cruncher's
    accent-insensitive mode does not ignore the subscript). Callers retry the
    restored spelling as an extra candidate.
    """
    variants: List[str] = []
    for index, char in enumerate(form):
        if char == "η":
            variants.append(form[:index] + "ῃ" + form[index + 1:])
    return variants


def name_candidates(form: str, cap: int = NAME_CAP) -> List[str]:
    """Case-ending → nominative candidates for name-like surfaces.

    Returns unaccented lower-case nominatives (the caller re-accents them from
    the active frequency table when possible). Empty for forms with a stem
    shorter than two letters.
    """
    base = normalize(form)
    candidates: List[str] = []
    seen = set()
    for suffix, replacement in NAME_RULES:
        if len(base) - len(suffix) < 2:
            continue
        if base.endswith(suffix):
            candidate = base[: len(base) - len(suffix)] + replacement
            if candidate != base and candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)
        if len(candidates) >= cap:
            break
    return candidates


def recover(
    surfaces: Sequence[str],
    analyses: List[List[Analysis]],
    runner,
    frequencies: Optional[Dict[str, int]] = None,
) -> int:
    """Attach recovery proposals in place for tokens with no analyses.

    ``surfaces[i]`` is the token text and ``analyses[i]`` its candidate list
    (possibly empty); only empty lists are touched, so analyzed tokens are
    never changed. Spelling variants are re-analyzed against the stemlib and
    attached with the variant in ``recovered_from``; name candidates are
    confirmed against the stemlib when a nominal reading matches the candidate,
    else proposed directly with the rule-generated nominative as the lemma,
    re-accented from ``frequencies`` when it knows the form. All proposals are
    flagged ``proposed=True``; callers rank them with the regular passes.

    Returns the number of tokens that received proposals.
    """
    misses = [
        (index, surface)
        for index, (surface, candidates) in enumerate(zip(surfaces, analyses))
        if not candidates and surface
    ]
    if not misses:
        return 0
    queries: Dict[int, List[Tuple[str, str]]] = {}
    for index, surface in misses:
        variants = spelling_variants(surface)
        candidates = [(variant, "spelling") for variant in variants]
        # Retry η positions with the iota subscript restored (documentary
        # spellings drop it; the stemlib needs it for ῃ forms).
        for variant in variants:
            candidates += [(restored, "spelling")
                           for restored in subscript_variants(variant)]
        candidates += [(name, "name") for name in name_candidates(surface)]
        if candidates:
            queries[index] = candidates
    if not queries:
        return 0
    distinct = sorted(
        {candidate for candidates in queries.values() for candidate, _ in candidates}
    )
    analyzed: Dict[str, List[Analysis]] = {}
    for start in range(0, len(distinct), 2000):
        chunk = distinct[start:start + 2000]
        betas = [to_beta(candidate) for candidate in chunk]
        for candidate, found in zip(chunk, runner.analyze_beta(betas, ignore_accents=True)):
            if found:
                analyzed[candidate] = found
    # Accent index over the active table (unaccented key -> canonical key) so
    # name proposals match the table's accentuation (δωριων -> δωρίων).
    accent_index: Dict[str, str] = {}
    for key in frequencies or {}:
        accent_index.setdefault(strip_accents(key), key)

    def key_of(analysis: Analysis) -> Tuple:
        return (
            normalize_lemma(analysis.lemma),
            analysis.pos,
            analysis.stemtype,
            tuple(sorted(analysis.features.items())),
        )

    recovered = 0
    for index, surface in misses:
        proposals: List[Analysis] = []
        seen = set()
        for candidate, kind in queries.get(index, ()):
            if kind == "spelling":
                for analysis in analyzed.get(candidate, ()):
                    key = key_of(analysis)
                    if key in seen:
                        continue
                    seen.add(key)
                    proposals.append(
                        replace(analysis, proposed=True, recovered_from=candidate)
                    )
                continue
            confirmed = [
                analysis
                for analysis in analyzed.get(candidate, ())
                if strip_accents(normalize_lemma(analysis.lemma)) == candidate
            ]
            if confirmed:
                for analysis in confirmed:
                    key = key_of(analysis)
                    if key in seen:
                        continue
                    seen.add(key)
                    proposals.append(
                        replace(analysis, proposed=True, recovered_from=candidate)
                    )
            else:
                lemma = accent_index.get(candidate, candidate)
                if surface[:1].isupper():
                    lemma = lemma[:1].upper() + lemma[1:]
                key = (normalize_lemma(lemma), "N", "proper", ())
                if key in seen:
                    continue
                seen.add(key)
                proposals.append(
                    Analysis(
                        lemma=lemma,
                        lemma_beta=to_beta(lemma),
                        pos="N",
                        raw_pos="N",
                        stemtype="proper",
                        features={"case": ("nom",), "number": ("sg",)},
                        proposed=True,
                        recovered_from=candidate,
                    )
                )
        if proposals:
            analyses[index][:] = proposals
            recovered += 1
    return recovered
