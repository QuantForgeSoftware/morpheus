#!/usr/bin/env python3
"""Minimal reference integration: build a searchable lemma index from
`morpheus-toolkit analyze --json` output (JSONL).

Usage:
  morpheus-toolkit analyze transcript.txt --json out.jsonl
  python3 lemma_index.py out.jsonl                 # count lemmas
  python3 lemma_index.py out.jsonl λόγος           # every reading of a lemma
  python3 lemma_index.py out.jsonl --parse "case=acc number=sg"
"""
import json
import sys
from collections import Counter, defaultdict


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rows = load(sys.argv[1])

    if len(sys.argv) == 2:
        by_lemma = Counter()
        for row in rows:
            for a in row["analyses"]:
                by_lemma[a["lemma"]] += 1
        for lemma, n in by_lemma.most_common():
            print(f"{n:5d}  {lemma}")
        return

    if sys.argv[2] == "--parse":
        want = dict(p.split("=") for p in sys.argv[3].split())
        for row in rows:
            for a in row["analyses"]:
                if all(v in a["features"].get(k, []) for k, v in want.items()):
                    print(f"{row['token']:<16} {a['pos']} {a['lemma']}  {a['features']}")
        return

    lemma = sys.argv[2]
    for row in rows:
        for a in row["analyses"]:
            if a["lemma"] == lemma:
                print(f"{row['token']:<16} {a['pos']} {a['features']}  (conf {a['confidence']})")


if __name__ == "__main__":
    main()
