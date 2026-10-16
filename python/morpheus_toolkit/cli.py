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
    analyze.add_argument("--language", default="greek", choices=["greek", "latin"])
    analyze.add_argument("--context", action="store_true", help="enable experimental contextual re-ranking")
    analyze.add_argument(
        "--homographs",
        action="store_true",
        help="re-rank ambiguous forms by context-conditional gold counts (Greek)",
    )
    numerals_group = analyze.add_mutually_exclusive_group()
    numerals_group.add_argument(
        "--numerals",
        action="store_true",
        help="give unanalyzed Greek letter-numeral tokens a synthetic analysis (papyri)",
    )
    numerals_group.add_argument(
        "--numerals-auto",
        action="store_true",
        help="as --numerals, but only when adaptive table selection picks the papyri table",
    )
    analyze.add_argument(
        "--unknown-as-proper",
        action="store_true",
        help="give unanalyzed tokens (proper names) a synthetic proper-noun analysis",
    )
    analyze.add_argument(
        "--ignore-accents",
        action="store_true",
        help="retry accented misses without accents/breathings (unaccented text)",
    )
    analyze.add_argument(
        "--no-learned",
        dest="learned",
        action="store_false",
        help="disable the learned re-ranker (on by default for Greek)",
    )
    analyze.add_argument(
        "--no-adaptive-tables",
        dest="adaptive_tables",
        action="store_false",
        help="disable automatic frequency-table selection (on by default for Greek)",
    )
    analyze.add_argument(
        "--no-recovery",
        dest="recovery",
        action="store_false",
        help="disable the recovery pre-pass for unanalyzed tokens (on by default for Greek)",
    )
    # Accepted no-ops kept for compatibility with older command lines.
    analyze.add_argument("--learned", dest="learned", action="store_true",
                         help=argparse.SUPPRESS)
    analyze.add_argument("--adaptive-tables", dest="adaptive_tables", action="store_true",
                         help=argparse.SUPPRESS)
    analyze.add_argument("--recovery", dest="recovery", action="store_true",
                         help=argparse.SUPPRESS)
    analyze.set_defaults(learned=True, adaptive_tables=True, recovery=True)
    analyze.add_argument(
        "--profile",
        help="rewrite output to a named lemma/POS convention, comma-combinable "
             "(morphgnt | lxx | base-lemmas)",
    )
    analyze.add_argument("--jobs", type=int, default=1,
                         help="parallel cruncher processes for large inputs (default 1)")
    args = parser.parse_args(argv)
    if args.profile:
        from morpheus_toolkit.profiles import PROFILE_NAMES

        unknown = [
            part for part in (p.strip().lower() for p in args.profile.split(","))
            if part and part not in PROFILE_NAMES
        ]
        if unknown:
            parser.error(
                f"unknown profile(s): {', '.join(unknown)} "
                f"(choose from {', '.join(PROFILE_NAMES)})"
            )

    morpheus = Morpheus(
        use_context=args.context,
        unknown_as_proper=args.unknown_as_proper,
        ignore_accents=args.ignore_accents,
        use_homograph_context=args.homographs,
        numerals="auto" if args.numerals_auto else args.numerals,
        recovery=args.recovery,
        language=args.language,
        use_learned=args.learned,
        adaptive_tables=args.adaptive_tables,
        profile=args.profile,
        jobs=args.jobs,
    )
    tokens = _read_tokens(args)
    results = morpheus.analyze_tokens(tokens)

    analyzed = sum(1 for result in results if result.analyses)
    total = len(results)
    print(f"{total} tokens, {analyzed} analyzed ({100 * analyzed / max(total, 1):.1f}%), {total - analyzed} misses")

    for result in results:
        if not result.analyses:
            continue
        top = result.analyses[: args.top]
        rendered = "; ".join(
            f"{a.pos} {a.lemma}"
            + (f" G{a.strongs}" if a.strongs else "")
            + f" [{a.feature_string()}] ({a.confidence:.2f})"
            for a in top
        )
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
