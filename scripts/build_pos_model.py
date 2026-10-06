#!/usr/bin/env python3
"""
Build a POS unigram/bigram model from a gold corpus (MorphGNT) for the Viterbi
tagger. The tagset is the MorphGNT/CCAT POS code (N, V, A, RA, RP, ...).

Usage:
  scripts/build_pos_model.py --morphgnt-dir ~/Code/bibloi/data/morphgnt
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "pos_bigram.json"),
    )
    args = parser.parse_args()
    if not args.morphgnt_dir or not os.path.isdir(args.morphgnt_dir):
        parser.error("--morphgnt-dir must point at the MorphGNT *.txt files")

    unigram: collections.Counter = collections.Counter()
    bigram: dict = collections.defaultdict(collections.Counter)
    start: collections.Counter = collections.Counter()

    for path in sorted(glob.glob(os.path.join(args.morphgnt_dir, "*.txt"))):
        previous = "<s>"
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if len(fields) < 3:
                    continue
                pos = fields[1].rstrip("-")
                unigram[pos] += 1
                bigram[previous][pos] += 1
                if previous == "<s>":
                    start[pos] += 1
                previous = pos

    payload = {
        "source": "MorphGNT SBLGNT (CC-BY-SA 4.0)",
        "unigrams": dict(unigram),
        "bigrams": {key: dict(value) for key, value in bigram.items()},
        "starts": dict(start),
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    print(f"Wrote POS model ({len(unigram)} tags) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
