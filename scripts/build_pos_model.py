#!/usr/bin/env python3
"""
Build a POS unigram/bigram model from a gold corpus for the Viterbi tagger.
The tagset is the coarse Morpheus/MorphGNT-style POS code (N, V, A, RA, RP, ...).

Sources: MorphGNT (*.txt), an LXX reference-corpus checkout (*.mlxx), or the AGLDT
v2.1 Greek treebanks (*.tb.xml). With the latter two, source-specific type codes are
mapped to the coarse POS first.

Usage:
  scripts/build_pos_model.py --morphgnt-dir ~/Code/bibloi/data/morphgnt
  scripts/build_pos_model.py --format mlxx --corpus-dir /path/to/lxx-corpus \
      --out python/morpheus_toolkit/data/pos_bigram_lxx.json
  scripts/build_pos_model.py --format agldt --agldt-dir /path/to/treebank_data/v2.1/Greek/texts \
      --out python/morpheus_toolkit/data/pos_bigram_grc.json
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

WORD_RE = re.compile(r'<word id="\d+" form="([^"]*)" lemma="([^"]*)"(?: postag="([a-z]))?')
SENTENCE_RE = re.compile(r"<sentence[^>]*>(.*?)</sentence>", re.S)
# AGLDT Greek postag position 1 -> coarse Morpheus POS (empirical; see Round 9).
AGLDT_POS = {"n": "N", "a": "A", "v": "V", "d": "D", "g": "X", "l": "RA",
             "p": "RP", "r": "P", "c": "C", "i": "I"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["morphgnt", "mlxx", "agldt"], default="morphgnt")
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument("--agldt-dir", default=os.environ.get("AGLDT_DIR", ""))
    parser.add_argument("--corpus-dir", default=os.environ.get("LXX_CORPUS_DIR", ""))
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    unigram: collections.Counter = collections.Counter()
    bigram: dict = collections.defaultdict(collections.Counter)
    start: collections.Counter = collections.Counter()

    def observe(pos: str, previous: str) -> str:
        unigram[pos] += 1
        bigram[previous][pos] += 1
        if previous == "<s>":
            start[pos] += 1
        return pos

    if args.format == "agldt":
        if not args.agldt_dir or not os.path.isdir(args.agldt_dir):
            parser.error("--agldt-dir must point at AGLDT v2.1 Greek *.tb.xml files")
        source = "AGLDT v2.1 Greek (CC BY-SA 3.0 US)"
        default_out = "pos_bigram_grc.json"
        for path in sorted(glob.glob(os.path.join(args.agldt_dir, "*.tb.xml"))):
            text = open(path, encoding="utf-8", errors="replace").read()
            for sentence in SENTENCE_RE.findall(text):
                previous = "<s>"
                for match in WORD_RE.finditer(sentence):
                    pos = AGLDT_POS.get(match.group(3) or "")
                    if pos:
                        previous = observe(pos, previous)
    else:
        if args.format == "mlxx":
            directory, pattern, source = args.corpus_dir, "*.mlxx", "LXX reference corpus"
        else:
            directory, pattern, source = (
                args.morphgnt_dir, "*.txt", "MorphGNT SBLGNT (CC-BY-SA 4.0)"
            )
        if not directory or not os.path.isdir(directory):
            parser.error(f"--{args.format}-dir must point at the {source} files")
        default_out = "pos_bigram.json"
        for path in sorted(glob.glob(os.path.join(directory, pattern))):
            previous = "<s>"
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    fields = line.split()
                    if len(fields) < 3 or (
                        args.format == "mlxx" and not re.search(r"[A-Za-z]", fields[0])
                    ):
                        continue  # blank / chapter-verse header lines
                    pos = coarse_pos(fields[1]) if args.format == "mlxx" else fields[1].rstrip("-")
                    previous = observe(pos, previous)

    out = args.out or os.path.join(REPO, "python", "morpheus_toolkit", "data", default_out)
    payload = {
        "source": source,
        "unigrams": dict(unigram),
        "bigrams": {key: dict(value) for key, value in bigram.items()},
        "starts": dict(start),
    }
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    print(f"Wrote POS model ({len(unigram)} tags) to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
