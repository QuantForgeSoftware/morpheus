#!/usr/bin/env python3
"""
Build a lemma-frequency table used to rank Morpheus analyses.

Source: the MorphGNT SBLGNT (CC-BY-SA 4.0) or an LXX reference-corpus checkout
(*.mlxx); the table is a plain lemma -> count map plus joint (lemma, POS) counts,
shipped with the toolkit so ranking works out of the box.

Usage:
  scripts/build_lemma_frequencies.py --morphgnt-dir ~/Code/bibloi/data/morphgnt
  scripts/build_lemma_frequencies.py --format mlxx --corpus-dir /path/to/lxx-corpus \
      --out python/morpheus_toolkit/data/lemma_frequencies_lxx.json
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import from_beta, normalize_lemma  # noqa: E402
from morpheus_toolkit.morphgnt import coarse_pos  # noqa: E402

# Corpus parse codes are bare [A-Z0-9]+; beta-code lemmas always contain other
# characters (vowels, diacritics), so this cleanly separates the columns.
PARSE_RE = re.compile(r"[A-Z0-9]+$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["morphgnt", "mlxx"], default="morphgnt")
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument("--corpus-dir", default=os.environ.get("LXX_CORPUS_DIR", ""))
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "lemma_frequencies.json"),
    )
    args = parser.parse_args()

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

    counts: collections.Counter = collections.Counter()
    by_pos: dict = collections.defaultdict(collections.Counter)
    for path in sorted(glob.glob(os.path.join(directory, pattern))):
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                fields = line.split()
                if len(fields) < 3 or not re.search(r"[A-Za-z]", fields[0]):
                    continue  # blank / chapter-verse header lines
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
        # joint (lemma, POS) counts, for disambiguating homographs like o( (RA vs RR)
        "by_pos": {lemma: dict(counter) for lemma, counter in by_pos.items()},
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=0)
    print(f"Wrote {len(counts)} lemmas ({payload['tokens']} tokens) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
