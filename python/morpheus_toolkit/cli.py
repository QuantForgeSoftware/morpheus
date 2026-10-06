"""Command-line interface: `morpheus-toolkit analyze ...`."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List

from .api import Morpheus


def _read_tokens(args) -> List[str]:
    with open(args.path, encoding="utf-8") as handle:
        content = handle.read()
    if not args.morphgnt:
        from .tokenize import tokenize

        return tokenize(content)
    tokens = []
    index = args.token_field - 1
    for line in content.splitlines():
        fields = line.split()
        if len(fields) > index:
            tokens.append(fields[index])
    return tokens


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="morpheus-toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="analyze a UTF-8 Greek text or a columnar token file")
    analyze.add_argument("path")
    analyze.add_argument("--json", help="write JSONL results here")
    analyze.add_argument("--morphgnt", action="store_true", help="columnar input (e.g. MorphGNT/AF)")
    analyze.add_argument("--token-field", type=int, default=5, help="1-based token column in --morphgnt mode")
    analyze.add_argument("--sample", type=int, default=20)
    analyze.add_argument("--top", type=int, default=3, help="analyses to show per sampled token")
    analyze.add_argument("--context", action="store_true", help="enable experimental contextual re-ranking")
    args = parser.parse_args(argv)

    morpheus = Morpheus(use_context=args.context)
    tokens = _read_tokens(args)
    results = morpheus.analyze_tokens(tokens)

    analyzed = sum(1 for result in results if result.analyses)
    total = len(results)
    print(f"{total} tokens, {analyzed} analyzed ({100 * analyzed / max(total, 1):.1f}%), {total - analyzed} misses")

    for result in results:
        if not result.analyses:
            continue
        top = result.analyses[: args.top]
        rendered = "; ".join(f"{a.pos} {a.lemma} [{a.feature_string()}]" for a in top)
        print(f"  {result.token:<18} {result.beta:<18} {rendered}")
        args.sample -= 1
        if args.sample <= 0:
            break

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        print(f"\nWrote {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
