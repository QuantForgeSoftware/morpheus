#!/usr/bin/env python3
"""
Build a POS unigram/bigram model from a gold corpus for the Viterbi tagger.
The tagset is the coarse MorphGNT-style POS code (N, V, A, RA, RP, ...).

Sources: MorphGNT (*.txt) or an LXX reference-corpus checkout (*.mlxx); with
the latter, fine-grained type codes are mapped to coarse POS first.

Usage:
  scripts/build_pos_model.py --morphgnt-dir ~/Code/bibloi/data/morphgnt
  scripts/build_pos_model.py --format mlxx --corpus-dir /path/to/lxx-corpus \
      --out python/morpheus_toolkit/data/pos_bigram_lxx.json
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

from morpheus_toolkit.morphgnt import coarse_pos  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["morphgnt", "mlxx"], default="morphgnt")
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument("--corpus-dir", default=os.environ.get("LXX_CORPUS_DIR", ""))
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "pos_bigram.json"),
    )
    args = parser.parse_args()

    if args.format == "mlxx":
        directory, pattern, source = args.corpus_dir, "*.mlxx", "LXX reference corpus"
    else:
        directory, pattern, source = (
            args.morphgnt_dir,
            "*.txt",
            "MorphGNT SBLGNT (CC-BY-SA 4.0)",
        )
    if not directory or not os.path.isdir(directory):
        parser.error(f"--{args.format}-dir must point at the {source} files")

    unigram: collections.Counter = collections.Counter()
    bigram: dict = collections.defaultdict(collections.Counter)
    start: collections.Counter = collections.Counter()

    for path in sorted(glob.glob(os.path.join(directory, pattern))):
        previous = "<s>"
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                fields = line.split()
                if len(fields) < 3 or (args.format == "mlxx" and not re.search(r"[A-Za-z]", fields[0])):
                    continue  # blank / chapter-verse header lines
                pos = coarse_pos(fields[1]) if args.format == "mlxx" else fields[1].rstrip("-")
                unigram[pos] += 1
                bigram[previous][pos] += 1
                if previous == "<s>":
                    start[pos] += 1
                previous = pos

    payload = {
        "source": source,
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
