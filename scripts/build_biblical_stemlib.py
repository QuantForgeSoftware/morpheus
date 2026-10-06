#!/usr/bin/env python3
"""
Generate `stemlib/Greek/stemsrc/nom.biblical` — biblical proper names absent
from the classical stemlibs (Smith's biographies etc.).

It runs Morpheus over a gold corpus, keeps the tokens that get **no** analysis and
whose gold POS is nominal and whose lemma is capitalized (i.e. names), and emits
`:le:`/`:wd:` entries marking them as indeclinable `pers_name`s. This is how the
analyzer learns names such as Δαυίδ, Βαρναβᾶς, Ἐλισάβετ, Βηθλέεμ.

Usage:
  scripts/build_biblical_stemlib.py --morphgnt-dir ~/Code/bibloi/data/morphgnt \
      --extra ~/Code/apostolic-fathers/data/morph/*.txt
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import from_beta, normalize_lemma, to_beta  # noqa: E402
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402

GENDER = {"M": "masc", "F": "fem", "N": "neut"}
NUMBER = {"S": "sg", "P": "pl", "D": "dual"}

# Artifacts and common nouns that the Apostolic Fathers' machine-generated POS
# occasionally mistags as proper nouns.
EXCLUDE = {
    "Ῥεβέκξ", "Ἀγαθόποδις", "Ἀγαθόπους", "Ἀλλ", "Ὀξυχολία", "Θεγρί",
    "Χριστιανισμός", "Χριστιανισμόν",
}


def read_rows(
    paths,
    token_field,
    lemma_field,
    pos_field,
    parsing_field,
    lang_field,
    source_field,
    source_values,
    pos_require,
):
    rows = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if len(fields) < max(token_field, lemma_field, pos_field):
                    continue
                # Language/source/POS filters apply only where the column exists,
                # so a single run can mix a 7-column corpus (MorphGNT) and a
                # 9-column one (the Apostolic Fathers).
                if lang_field and len(fields) >= lang_field and fields[lang_field - 1] != "grc":
                    continue
                if source_values and len(fields) >= source_field and fields[source_field - 1] not in source_values:
                    continue
                if pos_require and fields[pos_field - 1] not in pos_require:
                    continue
                rows.append(
                    (
                        fields[token_field - 1],
                        fields[lemma_field - 1],
                        fields[pos_field - 1],
                        fields[parsing_field - 1] if parsing_field else "",
                    )
                )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument("--extra", nargs="*", default=[], help="extra columnar corpora")
    parser.add_argument("--token-field", type=int, default=5)
    parser.add_argument("--lemma-field", type=int, default=7)
    parser.add_argument("--pos-field", type=int, default=2)
    parser.add_argument("--parsing-field", type=int, default=3)
    parser.add_argument("--lang-field", type=int, default=0)
    parser.add_argument("--source-field", type=int, default=0)
    parser.add_argument(
        "--source-values",
        default="",
        help="comma-separated allowlist for --source-field (e.g. MorphGNT)",
    )
    parser.add_argument(
        "--pos-require",
        default="",
        help="comma-separated POS codes to keep (e.g. NP for the Apostolic Fathers)",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "stemlib", "Greek", "stemsrc", "nom.biblical"),
    )
    args = parser.parse_args()

    paths = sorted(glob.glob(os.path.join(args.morphgnt_dir, "*.txt"))) if args.morphgnt_dir else []
    for pattern in args.extra:
        paths.extend(sorted(glob.glob(pattern)) or [pattern])
    if not paths:
        parser.error("give --morphgnt-dir and/or --extra")

    source_values = [value for value in args.source_values.split(",") if value]
    pos_require = [value for value in args.pos_require.split(",") if value]
    rows = read_rows(
        paths,
        args.token_field,
        args.lemma_field,
        args.pos_field,
        args.parsing_field,
        args.lang_field,
        args.source_field,
        source_values,
        pos_require,
    )
    sent = [(token, to_beta(token), lemma, pos, parsing) for token, lemma, pos, parsing in rows if to_beta(token)]

    runner = MorpheusRunner()

    # Collect candidate names keyed by their dictionary form, together with the
    # attested forms and the dictionary form itself.
    candidates: dict = collections.defaultdict(set)
    for token, beta, lemma, pos, parsing in sent:
        if not pos.startswith("N"):
            continue
        if not lemma or not lemma[0].isupper():
            continue  # names are capitalized; skips σάββατον etc.
        if len(lemma) < 3 or lemma.isupper() or lemma in EXCLUDE:
            continue  # drop all-caps artifacts and known non-names
        lemma_beta = to_beta(lemma)
        if not lemma_beta:
            continue
        gender = GENDER.get(parsing[6] if len(parsing) > 6 else "-", "masc")
        number = NUMBER.get(parsing[5] if len(parsing) > 5 else "-", "sg")
        candidates[lemma_beta].add((beta, gender, number))
        candidates[lemma_beta].add((lemma_beta, gender, number))

    # Keep the names whose *dictionary form* Morpheus does not already analyze with
    # the right lemma — this catches both misses and names it mistakes for a common
    # word (e.g. Μαρκίων -> Μάρκιος). Merge with any existing file so re-running is
    # idempotent.
    lemma_betas = list(candidates)
    recognized = runner.analyze_beta(lemma_betas)
    names: dict = load_existing(args.out)
    for lemma_beta, result in zip(lemma_betas, recognized):
        gold = normalize_lemma(from_beta(lemma_beta))
        if result and any(analysis.matches_lemma(gold) for analysis in result):
            continue
        names[lemma_beta] |= candidates[lemma_beta]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    entries = 0
    with open(args.out, "w", encoding="utf-8") as out:
        out.write("# Biblical proper names absent from the classical stemlibs.\n")
        out.write("# Generated by scripts/build_biblical_stemlib.py (SBLGNT + Apostolic Fathers).\n\n")
        for lemma_beta in sorted(names):
            out.write(f":le:{lemma_beta}\n")
            for form_beta, gender, number in sorted(names[lemma_beta]):
                out.write(f":wd:{form_beta}\tindecl {gender} nom voc gen dat acc {number} pers_name\n")
                entries += 1
            out.write("\n")
    print(f"Wrote {len(names)} names ({entries} forms) to {os.path.relpath(args.out, REPO)}")
    return 0


def load_existing(path: str) -> dict:
    """Parse an existing nom.biblical back into {lemma_beta: {(form, gender, number)}}."""
    names: dict = collections.defaultdict(set)
    if not os.path.exists(path):
        return names
    excluded = {to_beta(item) for item in EXCLUDE}
    current = None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith(":le:"):
            current = line[4:].strip()
            if current in excluded:
                current = None
        elif line.startswith(":wd:") and current:
            parts = line[4:].split()
            if len(parts) >= 3:
                names[current].add((parts[0], parts[2], parts[-2]))
    return names


if __name__ == "__main__":
    sys.exit(main())
