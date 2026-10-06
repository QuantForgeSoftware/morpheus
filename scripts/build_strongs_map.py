#!/usr/bin/env python3
"""
Build a lemma -> Strong's number table for Greek, so Morpheus analyses can link
to lexicons keyed by Strong's.

Source: the SBLGNT token data (each word carries a `Lemma` and a `Strongs`
number). Strong's numbers are public domain; the lemma mapping is derived from
the GNT data.

Usage:
  scripts/build_strongs_map.py --src ~/Code/bibloi/data/bibloi-rtdb-fixed.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import normalize_lemma  # noqa: E402


def collect(obj, counts) -> None:
    if isinstance(obj, dict):
        if "Lemma" in obj and "Strongs" in obj:
            try:
                strongs = int(obj["Strongs"])
            except (TypeError, ValueError):
                return
            if strongs > 0:
                counts[normalize_lemma(obj["Lemma"])][strongs] += 1
            return
        for value in obj.values():
            collect(value, counts)
    elif isinstance(obj, list):
        for item in obj:
            collect(item, counts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="GNT token JSON export")
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "lemma_strongs.json"),
    )
    args = parser.parse_args()

    with open(args.src, encoding="utf-8") as handle:
        data = json.load(handle)

    counts: dict = collections.defaultdict(collections.Counter)
    collect(data, counts)

    # Most frequent Strong's number per lemma.
    mapping = {lemma: counter.most_common(1)[0][0] for lemma, counter in counts.items() if counter}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    payload = {
        "source": "SBLGNT token data (Strong's numbers, public domain)",
        "lemmas": len(mapping),
        "strongs": mapping,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    print(f"Wrote {len(mapping)} lemma -> Strong's mappings to {os.path.relpath(args.out, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
