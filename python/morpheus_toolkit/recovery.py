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
  documentary ο/οι, ει/ε, ζ/σ, μψ/ψ and internal nasal assimilation
  (συνπροσγενόμενος → συμπροσγενόμενος); the final -ν/-ς toggle including
  sandhi spellings (μὲγ → μέν, ἐὰμ → ἐάν); and dropped iota subscripts restored
  on single η positions (:func:`subscript_variants`). Operations compose: every
  pair of single operations is tried (a class substitution combines with a
  geminate or a global rule, not just with another substitution). Closest-first
  (single operations before pairwise), deterministic, capped.
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
from typing import Dict, List, Optional, Sequence, Tuple

from .analysis import Analysis
from .beta import normalize_lemma, to_beta

# i-sound interchange first (longest digraphs before single letters), then the
# e- and o-classes. Documentary ο/οι is handled as a global rule below because
# οι is already claimed by the i-class. Within the i-class the alternatives are
# ordered ι-first (the dominant itacism): matching only requires υι to precede
# υ, so ι/ει/η may lead the tuple while every position still matches its
# longest member.
VOWEL_CLASSES: Tuple[Tuple[str, ...], ...] = (
    ("ι", "ει", "η", "υι", "υ", "οι", "ου"),
    ("αι", "ε"),
    ("ω", "ο"),
)
CONSONANT_CLASSES: Tuple[Tuple[str, ...], ...] = (
    ("τ", "δ", "θ"),
    ("κ", "γ", "χ"),
    ("π", "β", "φ"),
)
GEMINATES = ("ρρ", "σσ", "ττ", "λλ", "μμ", "νν", "ππ", "κκ",
             "ββ", "γγ", "δδ", "θθ", "φφ", "χχ")
DOUBLED = ("ρ", "σ", "τ")
# Whole-word substitutions that are not per-position classes: documentary ο/οι
# and ει/ε interchanges, ζ/σ (ζμῆνος for σμῆνος), μψ/ψ cluster simplification
# (ἀντιλήμψεως for ἀντιλήψεως), and internal nasal assimilation, where the
# nasal assimilates to a following labial/velar stop in spelling
# (συνπροσγενόμενος for συμπροσγενόμενος, ἐνγηαλλιούσαις for ἐγγηαλλιούσαις).
GLOBAL_RULES = (
    ("οι", "ο"), ("ει", "ε"), ("ζ", "σ"), ("μψ", "ψ"),
    ("νπ", "μπ"), ("νβ", "μβ"), ("νφ", "μφ"),
    ("νκ", "γκ"), ("νχ", "γχ"), ("νγ", "γγ"),
)

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

SPELLING_CAP = 96
NAME_CAP = 16
# In the pairwise tier only the first few alternatives of a class slot
# participate: with ~6 alternatives per vowel slot the pair space explodes, and
# the alternatives are ordered most-likely-first (ι leads the i-class), so the
# tail is diminishing returns. Singles keep every alternative.
PAIR_ALTERNATIVES = 3


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


def _slots(form: str) -> List[Tuple[int, int, Tuple[str, ...], bool]]:
    """Interchangeable positions: (start, end, alternative spellings, is_vowel)."""
    slots: List[Tuple[int, int, Tuple[str, ...], bool]] = []
    index = 0
    while index < len(form):
        match = None
        for is_vowel, classes in ((True, VOWEL_CLASSES), (False, CONSONANT_CLASSES)):
            for cls in classes:
                for member in cls:
                    if form.startswith(member, index):
                        match = (
                            index,
                            index + len(member),
                            tuple(other for other in cls if other != member),
                            is_vowel,
                        )
                        break
                if match:
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


def _edits(form: str) -> List[Tuple[int, bool, List[Tuple[int, int, str]]]]:
    """Primitive normalization operations as (rank, pair-eligible, edits).

    Each operation is a list of ``(start, end, replacement)`` edits: one per
    alternative of a per-position class slot, one covering every occurrence of
    a geminate / doubling / global substitution, and one for the final -ν/-ς
    toggle. Operations compose by concatenating their edit lists (all positions
    refer to the original form, so merged edits never go stale); pairs whose
    edits overlap are skipped by the caller. The rank orders the pairwise
    search: vowel substitutions first (the dominant documentary phenomenon),
    then consonant substitutions, other rules, and the final toggle.
    """
    operations: List[Tuple[int, bool, List[Tuple[int, int, str]]]] = []
    for start, end, alternatives, is_vowel in _slots(form):
        for position, alternative in enumerate(alternatives):
            operations.append((
                0 if is_vowel else 1,
                position < PAIR_ALTERNATIVES,
                [(start, end, alternative)],
            ))
    for pattern, replacement, step in (
        *((geminate, geminate[0], 2) for geminate in GEMINATES),
        *((letter, letter * 2, 1) for letter in DOUBLED),
        *((source, target, len(source)) for source, target in GLOBAL_RULES),
    ):
        edits = []
        index = form.find(pattern)
        while index != -1:
            edits.append((index, index + len(pattern), replacement))
            index = form.find(pattern, index + step)
        if edits:
            operations.append((2, True, edits))
    if form.endswith("ν"):
        operations.append((3, True, [(len(form) - 1, len(form), "")]))
    elif form.endswith("σ"):
        operations.append((3, True, [(len(form) - 1, len(form), "ν")]))
    elif form.endswith("γ") or form.endswith("μ"):
        operations.append((3, True, [(len(form) - 1, len(form), "ν")]))  # μὲγ/ἐὰμ for μέν/ἐάν
    else:
        operations.append((3, True, [(len(form), len(form), "ν")]))
    return operations


def _overlapping(edits: List[Tuple[int, int, str]]) -> bool:
    ordered = sorted(edits)
    return any(b_start < a_end for (_, a_end, _), (b_start, _, _) in zip(ordered, ordered[1:]))


def spelling_variants(form: str, cap: int = SPELLING_CAP) -> List[str]:
    """Bounded orthographic normalization candidates, closest-first.

    Tier 1: every single normalization operation (class substitutions, geminate
    simplification/doubling, the global rules incl. nasal assimilation, the
    final -ν/-ς toggle). Tier 2: every pair of operations merged into one edit
    set — so a substitution also combines with a geminate or a global rule —
    searched vowel-pairs-first. Empty for forms shorter than two letters
    (single letters belong to ``numerals``).
    """
    base = normalize(form)
    if len(base) < 2:
        return []
    operations = sorted(_edits(base), key=lambda operation: operation[0])
    candidates: List[str] = []
    seen = set()

    def add(candidate: str) -> None:
        candidate = _display(candidate)
        if candidate and candidate != _display(base) and candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)

    for _, _, edits in operations:
        add(_substitute(base, edits))
    pairwise = [(rank, edits) for rank, eligible, edits in operations if eligible]
    for index, (_, first) in enumerate(pairwise):
        for _, second in pairwise[index + 1:]:
            merged = first + second
            if _overlapping(merged):
                continue
            add(_substitute(base, merged))
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


def proposal_strategy(analysis: Analysis, surface: str) -> str:
    """Strategy class of a proposed analysis, for the fitted proposal priors.

    ``spelling`` / ``name`` for recovery proposals (which carry the candidate
    they were generated from in ``recovered_from``), ``numeral`` for the numeral
    table's proposals, ``proper`` for the unknown-as-proper fallback. Returns
    ``""`` for native (non-proposed) analyses.
    """
    if not analysis.proposed:
        return ""
    if analysis.recovered_from is None:
        return "numeral" if analysis.stemtype == "numeral" else "proper"
    names = set(name_candidates(surface))
    return "name" if analysis.recovered_from in names else "spelling"


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
