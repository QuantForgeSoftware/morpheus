#!/usr/bin/env python3
"""
Generate `stemlib/Greek/stemsrc/nom.lxx` — LXX entries absent from the classical
stemlibs, derived from a reference morphological analysis of the Septuagint.

Source: `*.mlxx` files (beta code), one line per token:

    form  type  [parse]  lemma  [prefix]

e.g. `*ABRAAM  N  NSM  *ABRAAM` or `E)N  P  E)N`. See the corpus's own coding
sheet (`0-betacode.txt`, `*Morph-Coding`) for the conventions: type `N` alone
marks an indeclinable proper noun, and dictionary forms of proper nouns are
capitalized.

The script runs Morpheus over every distinct form and keeps the ones it cannot
analyze. Proper names (type `N`, or a capitalized dictionary lemma) become
indeclinable `pers_name` entries with the case/number/gender the corpus attests
— the same pattern as `nom.biblical`. A small curated set of missing common
words is emitted alongside, so re-running stays idempotent.

Usage:
  scripts/build_lxx_stemlib.py [--corpus-dir /path/to/lxx-corpus] \
      [--out stemlib/Greek/stemsrc/nom.lxx]
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import from_beta, to_beta  # noqa: E402
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402

GENDER = {"M": "masc", "F": "fem", "N": "neut"}
NUMBER = {"S": "sg", "P": "pl", "D": "dual"}

# Everything below this marker is generated; the curated entries above it are
# static. Re-runs merge with previously generated names (idempotent), so a name
# that Morpheus now recognizes is not dropped from the file.
GENERATED_MARKER = "# === generated entries begin (managed by build_lxx_stemlib.py) ==="

# Corpus parse codes are bare [A-Z0-9]+; beta-code lemmas always contain other
# characters (vowels, diacritics), so this cleanly separates the columns.
PARSE_RE = re.compile(r"[A-Z0-9]+$")


def canon(form_beta: str) -> str:
    """Reference-corpus beta code -> canonical lowercase beta via a round-trip.

    Corpus files use uppercase letters and occasionally omit iota subscripts;
    cruncher only accepts the canonical lowercase spelling, so route through
    Unicode first (``*ABRAAM`` -> ``Αβρααμ`` -> ``*abraam``).
    """
    return to_beta(from_beta(form_beta)) or ""


def standardize(form_beta: str) -> str:
    """Rewrite stored forms the way standword() rewrites inputs.

    The analyzer runs standword() on every input, which converts GRAVE to
    ACUTE (and drops accents after the first); CheckGenWords then compares
    accents exactly in normal mode. A stored word-final grave can therefore
    never match an accented input — store the acute spelling instead.
    Extra accents are harmless: both sides get zap2acc/stripacc treatment.
    """
    return form_beta.replace("\\", "/")


def parse_mlxx(path: str):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            fields = line.split()
            if len(fields) < 3 or not re.search(r"[A-Za-z]", fields[0]):
                continue  # blank / chapter-verse header lines
            form_b, typ = fields[0], fields[1]
            if len(fields) >= 4 and PARSE_RE.fullmatch(fields[2]):
                parse_c, lemma_b = fields[2], fields[3]
            else:
                parse_c, lemma_b = "", fields[2]
            yield form_b, typ, parse_c, lemma_b


def is_name(typ: str, lemma_beta: str) -> bool:
    """The corpus marks proper nouns by type `N` or a capitalized dictionary form."""
    if typ == "N":
        return True
    lemma_u = from_beta(lemma_beta)
    return bool(lemma_u) and lemma_u[0].isupper()


def load_existing(path: str) -> dict:
    """Parse previously generated names back into {lemma_beta: {(form, gender, number)}}.

    Only the section after GENERATED_MARKER is read; curated entries above it
    are left untouched.
    """
    names = collections.defaultdict(set)
    if not os.path.exists(path):
        return names
    in_generated = False
    current = None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith(GENERATED_MARKER):
            in_generated = True
            continue
        if not in_generated or not line.strip():
            continue
        if line.startswith(":le:"):
            current = line[4:].strip()
        elif line.startswith(":wd:") and current:
            parts = line[4:].split()
            # :wd:<form>\tindecl <gender> nom voc gen dat acc <number> pers_name
            if len(parts) >= 10:
                names[current].add((standardize(parts[0]), parts[2], parts[-2]))
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default=os.environ.get("LXX_CORPUS_DIR", ""))
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "stemlib", "Greek", "stemsrc", "nom.lxx"),
    )
    parser.add_argument(
        "--include-recognized",
        action="store_true",
        help="also emit names Morpheus already analyzes (recovery / full coverage)",
    )
    args = parser.parse_args()

    if not args.corpus_dir or not os.path.isdir(args.corpus_dir):
        parser.error("give --corpus-dir (or set LXX_CORPUS_DIR) pointing at the LXX reference corpus")

    # Pass 1: collect distinct forms with their corpus annotation and frequency.
    info = {}
    freq = collections.Counter()
    for fn in sorted(os.listdir(args.corpus_dir)):
        if not fn.endswith(".mlxx"):
            continue
        for form_b, typ, parse_c, lemma_b in parse_mlxx(os.path.join(args.corpus_dir, fn)):
            freq[form_b] += 1
            if form_b not in info:
                info[form_b] = (typ, parse_c, lemma_b)

    # Pass 2: ask Morpheus which of them it already handles (skipped with
    # --include-recognized).
    forms = sorted(info)
    recognized = set()
    if not args.include_recognized:
        runner = MorpheusRunner()
        BATCH = 2000
        for i in range(0, len(forms), BATCH):
            chunk = [canon(f) or f.lower() for f in forms[i : i + BATCH]]
            for form_b, analyses in zip(forms[i : i + BATCH], runner.analyze_beta(chunk)):
                if analyses:
                    recognized.add(form_b)

    # Pass 3: missed proper names -> {lemma_beta: {(form_beta, gender, number)}}.
    names = collections.defaultdict(set)
    for form_b in forms:
        typ, parse_c, lemma_b = info[form_b]
        if not is_name(typ, lemma_b):
            continue
        if form_b in recognized:
            continue
        lemma_u = from_beta(lemma_b)

        gender = GENDER.get(parse_c[2] if len(parse_c) > 2 else "-", "masc")
        number = NUMBER.get(parse_c[1] if len(parse_c) > 1 else "-", "sg")
        if lemma_u.isupper():
            continue  # drop all-caps artifacts
        if len(lemma_u) < 3 and gender == "neut":
            continue  # two-letter neuter tokens are transcription artifacts (e.g. IN);
            # two-letter masc/fem names like Ωγ/Ωρ/Ηρ are kept
        form_c = standardize(canon(form_b) or form_b.lower())
        lemma_c = canon(lemma_b) or lemma_b.lower()
        names.setdefault(lemma_c, set()).add((form_c, gender, number))
        # The dictionary form itself is only added when it is a capitalized name
        # (starred): unstarred lemmas can be common words used as place names
        # (e.g. ΠΟΛΙΣ-ΑΣΔΕΚ under lemma πόλις), and must not gain bare entries.
        if lemma_c.startswith("*"):
            names[lemma_c].add((standardize(lemma_c), gender, number))

    # Curated common words the classical stemlibs lack (attested in the LXX).
    # Generative entries mirror existing ones: cf. :le:dw=ron/:no:dwr os_ou neut
    # (nom02), :le:a)ggei=on (lsj.nom), :le:a)spidou=xos (nom01). Where the
    # generative pattern does not produce the attested forms (verified against
    # the built index), explicit :wd: lines are used instead — cf. the name
    # entries above and :wd:a)/leifa irreg_decl3 neut nom sg (nom01).
    generative = [
        ("sa/bbaton", "σάββατον 'Sabbath'", ":no:sabbat os_ou neut"),
        ("tamiei=on", "ταμιεῖον 'treasury'", ":no:tamiei os_ou neut stem_acc"),
        ("brou=xos", "βροῦχος 'cough'", ":no:br-ou_x os_ou stem_acc masc"),
        # Round 2:
        ("pastofo/rion", "παστοφόριον — generative 2nd-decl neuter",
         ":no:pastofori os_ou neut"),
    ]
    explicit = [
        (
            "a)mno/s",
            "ἀμνός — the nom01 entry is restricted to nom; full paradigm added",
            "masc",
            [
                ("a)mno/s", "nom", "sg"),
                ("a)mnou=", "gen", "sg"),
                ("a)mnw=|", "dat", "sg"),
                ("a)mno/n", "acc", "sg"),
                ("a)mnoi/", "nom", "pl"),
                ("a)mnw=n", "gen", "pl"),
                ("a)mnoi=s", "dat", "pl"),
                ("a)mnou/s", "acc", "pl"),
            ],
        ),
        (
            "a)delfido/s",
            "ἀδελφιδός 'half-brother'",
            "masc",
            [
                ("a)delfido/s", "nom", "sg"),
                ("a)delfi/dou", "gen", "sg"),
                ("a)delfi/dw|", "dat", "sg"),
                ("a)delfi/don", "acc", "sg"),
                ("a)delfide/", "voc", "sg"),
                ("a)delfi/des", "nom", "pl"),
                ("a)delfi/dwn", "gen", "pl"),
                ("a)delfi/dois", "dat", "pl"),
                ("a)delfi/das", "acc", "pl"),
            ],
        ),
        (
            "trubli/on",
            "τρυβλίον 'bowl'",
            "neut",
            [
                ("trubli/on", "nom", "sg"),
                ("trubli/ou", "gen", "sg"),
                ("trubli/w|", "dat", "sg"),
                ("trubli/a", "nom", "pl"),
                ("trubli/wn", "gen", "pl"),
                ("trubli/ois", "dat", "pl"),
            ],
        ),
        # Round 2:
        (
            "a)llhlou/i+a",
            "αλληλουία — the corpus codes it as an interjection; Morpheus has no such POS, so it is registered as an indeclinable (no gender). The lemma keeps the corpus's accented + diaeresis spelling for lemma matching; both surface spellings are indexed.",
            "",
            [("allhlouia", "nom", "sg"), ("a)llhlou/i+a", "nom", "sg")],
        ),
        (
            "a)ntilh/mptwr",
            "ἀντιλήμπτωρ 'one who receives against' (only two forms attested in LXX)",
            "masc",
            [("a)ntilh/mptwr", "nom", "sg"), ("a)ntilh/mptores", "nom", "pl")],
        ),
        (
            "nossi/a",
            "νοσσία — no -ία noun pattern exists, so explicit forms (all attested in LXX). standword() rewrites GRAVE to ACUTE on every input and CheckGenWords compares accents exactly in normal mode, so stored forms use the accent each corpus spelling standardizes to: word-final graves become acute (the corpus spells acc sg both ways), circumflexes are kept.",
            "fem",
            [
                ("nossia/n", "acc", "sg"),
                ("nossia=|", "dat", "sg"),
                ("nossiai/", "nom", "pl"),
                ("nossia=s", "gen", "sg"),
                ("nossia/s", "acc", "pl"),
            ],
        ),
    ]

    # Merge with previously generated names so re-runs are idempotent.
    for lemma_beta, existing in load_existing(args.out).items():
        names[lemma_beta] |= existing

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as out:
        out.write("# LXX entries absent from the classical stemlibs.\n")
        out.write("# Generated by scripts/build_lxx_stemlib.py (LXX reference corpus).\n\n")

        for lemma_beta, note, no_line in sorted(generative):
            out.write(f"# {note}\n:le:{lemma_beta}\n{no_line}\n\n")

        for lemma_beta, note, gender, forms in sorted(explicit):
            out.write(f"# {note}\n:le:{lemma_beta}\n")
            g = f" {gender}" if gender else ""
            for form_beta, case, number in forms:
                out.write(f":wd:{form_beta}\tindecl{g} {case} {number}\n")
            out.write("\n")

        out.write(GENERATED_MARKER + "\n\n")
        entries = 0
        for lemma_beta in sorted(names):
            out.write(f":le:{lemma_beta}\n")
            for form_beta, gender, number in sorted(names[lemma_beta]):
                out.write(
                    f":wd:{form_beta}\tindecl {gender} nom voc gen dat acc {number} pers_name\n"
                )
                entries += 1
            out.write("\n")

    print(
        f"Wrote {len(names)} names ({entries} forms) + {len(generative)} generative and "
        f"{len(explicit)} explicit curated words to {os.path.relpath(args.out, REPO)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
