#!/usr/bin/env python3
"""
Build a lemma-frequency table used to rank Morpheus analyses.

Sources: the MorphGNT SBLGNT (CC-BY-SA 4.0), an LXX reference-corpus checkout
(*.mlxx), or AGLDT treebank XML (*-lat1.tb.xml / *-grc1.tb.xml from
PerseusDL/treebank_data, CC BY-SA 3.0 US). The table is a plain lemma -> count
map (plus joint (lemma, POS) counts for the Greek formats), shipped with the
toolkit so ranking works out of the box.

AGLDT note: only plain frequencies are emitted. Morpheus's Latin analyzer does
not separate adjectives from nouns (both surface as N unless a special stem
type fires), while AGLDT tags them separately; joint lemma x POS counts would
therefore systematically demote correct readings. The Greek formats keep their
joint tables because the reference POS maps cleanly onto Morpheus's codes.

Usage:
  scripts/build_lemma_frequencies.py --morphgnt-dir ~/Code/bibloi/data/morphgnt
  scripts/build_lemma_frequencies.py --format mlxx --corpus-dir /path/to/lxx-corpus \
      --out python/morpheus_toolkit/data/lemma_frequencies_lxx.json
  scripts/build_lemma_frequencies.py --format agldt \
      --corpus-dir /path/to/treebank_data/v2.1/Latin/texts \
      --out python/morpheus_toolkit/data/lemma_frequencies_latin.json
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import from_beta, normalize_lemma  # noqa: E402
from morpheus_toolkit.morphgnt import coarse_pos  # noqa: E402

# Corpus parse codes are bare [A-Z0-9]+; beta-code lemmas always contain other
# characters (vowels, diacritics), so this cleanly separates the columns.
PARSE_RE = re.compile(r"[A-Z0-9]+$")


def read_agldt(directory: str):
    """Yield ``(lemma, pos_char)`` from every AGLDT treebank XML under directory.

    AGLDT words are ``<word form="..." lemma="..." postag="..."/>`` elements;
    the lemma carries Perseus-style trailing homonym digits (``for1``), which
    :func:`normalize_lemma` strips. The first postag character is the part of
    speech (n/v/a/d/c/r/p/m/i/e/u in the Latin tagset).
    """
    for path in sorted(glob.glob(os.path.join(directory, "**", "*.tb.xml"), recursive=True)):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            print(f"warning: skipping unparseable {path}: {exc}", file=sys.stderr)
            continue
        for word in root.iter("word"):
            lemma = (word.get("lemma") or "").strip()
            postag = word.get("postag") or ""
            if not lemma or not postag:
                continue
            yield lemma, postag[0]


def agldt_source(directory: str) -> str:
    """Attribution label for an AGLDT directory (language + release version)."""
    lang = ""
    first = glob.glob(os.path.join(directory, "**", "*.tb.xml"), recursive=True)
    if first:
        try:
            root = ET.parse(first[0]).getroot()
            lang = root.get("{http://www.w3.org/XML/1998/namespace}lang") or ""
        except ET.ParseError:
            pass
    version = ""
    match = re.search(r"v\d+\.\d+", directory)
    if match:
        version = f" {match.group(0)}"
    name = {"la": "Latin", "grc": "Greek", "greek": "Greek"}.get(lang, lang or "")
    return f"AGLDT{version} {name} treebanks (PerseusDL/treebank_data), CC BY-SA 3.0 US"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["morphgnt", "mlxx", "agldt"], default="morphgnt")
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument("--corpus-dir", default=os.environ.get("LXX_CORPUS_DIR", ""))
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "lemma_frequencies.json"),
    )
    args = parser.parse_args()

    counts: collections.Counter = collections.Counter()
    by_pos: dict = collections.defaultdict(collections.Counter)

    if args.format == "agldt":
        directory, source = args.corpus_dir, agldt_source(args.corpus_dir)
        if not directory or not os.path.isdir(directory):
            parser.error("--corpus-dir must point at an AGLDT texts/ directory")
        for lemma, pos in read_agldt(directory):
            if pos == "u":  # punctuation tokens are not words
                continue
            key = normalize_lemma(lemma)
            # Drop editorial artifacts that are not whole words (enclitics like
            # -que, punctuated interjections, bracketed restorations).
            if key and all(ch.isalpha() for ch in key):
                counts[key] += 1
    else:
        if args.format == "mlxx":
            directory, pattern, source = (
                args.corpus_dir,
                "*.mlxx",
                "LXX reference corpus",
            )
        else:
            directory, pattern, source = (
                args.morphgnt_dir,
                "*.txt",
                "MorphGNT SBLGNT (https://github.com/morphgnt/sblgnt), CC-BY-SA 4.0",
            )
        if not directory or not os.path.isdir(directory):
            parser.error(f"--{args.format}-dir must point at the {source} files")
        for path in sorted(glob.glob(os.path.join(directory, pattern))):
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    fields = line.split()
                    # The letter guard is mlxx-only: LXX token lines start with a beta
                    # word while headers ("Gen 1:1") do not; MorphGNT-style files have
                    # numeric reference numbers in field 0 and no header lines.
                    if len(fields) < 3 or (args.format == "mlxx" and not re.search(r"[A-Za-z]", fields[0])):
                        continue
                    if args.format == "mlxx":
                        if len(fields) >= 4 and PARSE_RE.fullmatch(fields[2]):
                            lemma_b = fields[3]
                        else:
                            lemma_b = fields[2]
                        lemma = normalize_lemma(from_beta(lemma_b))
                        pos = coarse_pos(fields[1])
                    else:
                        if len(fields) < 7:
                            continue
                        lemma = normalize_lemma(fields[6])
                        pos = fields[1].rstrip("-")
                    counts[lemma] += 1
                    by_pos[lemma][pos] += 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    payload = {
        "source": source,
        "tokens": sum(counts.values()),
        "lemmas": len(counts),
        "frequencies": dict(counts.most_common()),
        # joint (lemma, POS) counts, for disambiguating homographs like o( (RA vs RR);
        # empty for AGLDT-derived tables (see module docstring)
        "by_pos": {lemma: dict(counter) for lemma, counter in by_pos.items()},
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=0)
    print(f"Wrote {len(counts)} lemmas ({payload['tokens']} tokens) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
