#!/usr/bin/env python3
"""
Analyze a columnar Greek token corpus with Morpheus and write JSONL.

Works with any whitespace-separated token file (MorphGNT, the Apostolic Fathers
edition, or your own): configure which columns hold the reference, token and
(optional) gold lemma. Output is one JSON object per token:

  {"ref": "...", "token": "...", "gold_lemma": "...", "analyses": [...]}

The analyses are ranked (most likely first). This is the tool for applying
Morpheus to a new Greek text.

Example:
  scripts/analyze_corpus.py ../apostolic-fathers/data/morph/011-didache.txt \
      --ref-field 1 --token-field 5 --lemma-field 7 --json /tmp/didache.jsonl
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import List

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.api import Morpheus  # noqa: E402


def read_rows(path: str, args) -> List[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            fields = line.split()
            if len(fields) < args.token_field:
                continue
            if args.lang_field and (
                len(fields) < args.lang_field or fields[args.lang_field - 1] != args.lang_value
            ):
                continue
            rows.append(
                {
                    "ref": fields[args.ref_field - 1] if args.ref_field else "",
                    "token": fields[args.token_field - 1],
                    "gold_lemma": fields[args.lemma_field - 1] if args.lemma_field else "",
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--ref-field", type=int, default=0)
    parser.add_argument("--token-field", type=int, default=5)
    parser.add_argument("--lemma-field", type=int, default=0)
    parser.add_argument("--lang-field", type=int, default=0, help="column holding a language code")
    parser.add_argument("--lang-value", default="grc", help="keep only rows with this language")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--json", help="write JSONL here (single input file only)")
    parser.add_argument("--context", action="store_true")
    parser.add_argument("--language", default="greek", choices=["greek", "latin"])
    parser.add_argument(
        "--unknown-as-proper",
        action="store_true",
        help="give unanalyzed tokens (proper names) a synthetic proper-noun analysis",
    )
    args = parser.parse_args()

    paths: List[str] = []
    for pattern in args.paths:
        paths.extend(sorted(glob.glob(pattern)) or [pattern])

    morpheus = Morpheus(
        use_context=args.context,
        unknown_as_proper=args.unknown_as_proper,
        language=args.language,
    )

    grand_total = grand_analyzed = 0
    for path in paths:
        rows = read_rows(path, args)
        if args.limit:
            rows = rows[: args.limit]
        results = morpheus.analyze_tokens([row["token"] for row in rows])
        analyzed = sum(1 for result in results if result.analyses)
        grand_total += len(rows)
        grand_analyzed += analyzed
        print(
            f"{os.path.basename(path):<28} {len(rows):>6} tokens  "
            f"{analyzed:>6} analyzed ({100 * analyzed / max(len(rows), 1):5.1f}%)"
        )
        if args.json:
            with open(args.json, "w", encoding="utf-8") as handle:
                for row, result in zip(rows, results):
                    handle.write(
                        json.dumps(
                            {**row, "analyses": [analysis.to_dict() for analysis in result.analyses]},
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            print(f"  wrote {args.json}")

    print(
        f"\nTOTAL {grand_total} tokens, {grand_analyzed} analyzed "
        f"({100 * grand_analyzed / max(grand_total, 1):.1f}%)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
