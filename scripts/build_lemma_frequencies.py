#!/usr/bin/env python3
"""
Build the bundled lemma-frequency table used to rank Morpheus analyses.

Source: the MorphGNT SBLGNT (CC-BY-SA 4.0), whose tokens carry a lemma. The table
is a plain lemma -> count map and is shipped with the toolkit so ranking works out
of the box.

Usage:
  scripts/build_lemma_frequencies.py --morphgnt-dir ~/Code/bibloi/data/morphgnt
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import normalize_lemma  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "lemma_frequencies.json"),
    )
    args = parser.parse_args()
    if not args.morphgnt_dir or not os.path.isdir(args.morphgnt_dir):
        parser.error("--morphgnt-dir must point at the MorphGNT *.txt files")

    counts: collections.Counter = collections.Counter()
    by_pos: dict = collections.defaultdict(collections.Counter)
    for path in sorted(glob.glob(os.path.join(args.morphgnt_dir, "*.txt"))):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if len(fields) < 7:
                    continue
                lemma = normalize_lemma(fields[6])
                pos = fields[1].rstrip("-")
                counts[lemma] += 1
                by_pos[lemma][pos] += 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    payload = {
        "source": "MorphGNT SBLGNT (https://github.com/morphgnt/sblgnt), CC-BY-SA 4.0",
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
