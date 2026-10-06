#!/usr/bin/env python3
"""
Measure Morpheus's agreement with a gold token set, and the effect of ranking.

Gold input is whitespace-separated columns (MorphGNT or the Apostolic Fathers
edition); the column indices are configurable. For every token we report:

  coverage      the gold lemma appears among Morpheus's candidates
  top-1 lemma   the first candidate equals the gold lemma (before vs after ranking)
  top-3 lemma   the gold lemma is among the first three after ranking
  POS           fine-grained POS equals the gold POS

Ranking is frequency-based (and optionally contextual); the reference frequency
table is the bundled NT table.

Examples:
  scripts/agreement_report.py --morphgnt-dir ~/Code/bibloi/data/morphgnt --limit 20000
  scripts/agreement_report.py ~/Code/apostolic-fathers/data/morph/011-didache.txt \
      --lemma-field 7 --pos-field 2 --lang-field 8 --lang-value grc --by-source
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.analysis import Analysis  # noqa: E402
from morpheus_toolkit.beta import normalize_lemma, to_beta  # noqa: E402
from morpheus_toolkit.ranking import Ranker, load_default_frequencies  # noqa: E402
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402
from morpheus_toolkit.tagger import PosTagger, load_default_pos_model  # noqa: E402


@dataclass
class Row:
    token: str
    beta: str
    lemma: str
    pos: str
    source: str = ""


@dataclass
class Counters:
    total: int = 0
    misses: int = 0
    coverage: int = 0
    top1_before: int = 0
    top1_freq: int = 0
    top1_context: int = 0
    top1_tagger: int = 0
    top3_freq: int = 0
    pos_agree: int = 0

    def add(self, other: "Counters") -> None:
        for name in self.__dataclass_fields__:  # type: ignore[attr-defined]
            setattr(self, name, getattr(self, name) + getattr(other, name))

    def line(self, label: str, show_context: bool = False, show_tagger: bool = False) -> str:
        def pct(value: int) -> str:
            return f"{100 * value / self.total:5.1f}%" if self.total else "  n/a"

        context = f"(ctx {pct(self.top1_context)}) " if show_context else ""
        tagger = f"tagger={pct(self.top1_tagger)} " if show_tagger else ""
        return (
            f"{label:<22} n={self.total:<7} misses={self.misses:<6} "
            f"coverage={pct(self.coverage)} top1={pct(self.top1_before)}->{pct(self.top1_freq)} "
            f"{context}{tagger}top3={pct(self.top3_freq)} pos={pct(self.pos_agree)}"
        )


def read_rows(paths: List[str], args) -> List[Row]:
    rows: List[Row] = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if len(fields) < max(args.token_field, args.lemma_field, args.pos_field):
                    continue
                if args.lang_field and (
                    len(fields) < args.lang_field or fields[args.lang_field - 1] != args.lang_value
                ):
                    continue
                rows.append(
                    Row(
                        token=fields[args.token_field - 1],
                        beta="",
                        lemma=fields[args.lemma_field - 1],
                        pos=fields[args.pos_field - 1].rstrip("-"),
                        source=fields[args.source_field - 1] if args.source_field and len(fields) >= args.source_field else "",
                    )
                )
    return rows


def first_match(analyses: List[Analysis], gold: str) -> Optional[int]:
    for index, analysis in enumerate(analyses):
        if analysis.matches_lemma(gold):
            return index
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--token-field", type=int, default=5)
    parser.add_argument("--lemma-field", type=int, default=7)
    parser.add_argument("--pos-field", type=int, default=2)
    parser.add_argument("--source-field", type=int, default=0)
    parser.add_argument("--lang-field", type=int, default=0)
    parser.add_argument("--lang-value", default="grc")
    parser.add_argument("--by-source", action="store_true")
    parser.add_argument("--context", action="store_true", help="also evaluate hand-written contextual re-ranking")
    parser.add_argument("--tagger", action="store_true", help="also evaluate the POS-bigram Viterbi tagger")
    parser.add_argument("--emission-weight", type=float, default=3.0)
    args = parser.parse_args()

    paths = list(args.paths)
    if args.morphgnt_dir:
        paths += sorted(glob.glob(os.path.join(args.morphgnt_dir, "*.txt")))
    if not paths:
        parser.error("give file paths or --morphgnt-dir")

    rows = read_rows(paths, args)
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        parser.error("no rows read")

    for row in rows:
        row.beta = to_beta(row.token)

    runner = MorpheusRunner()
    ranker = Ranker(load_default_frequencies(), use_context=False)

    sent = [row for row in rows if row.beta]
    analyses_by_token = runner.analyze_beta([row.beta for row in sent])

    overall = Counters()
    by_source: Dict[str, Counters] = {}

    # Frequency-scored copies (used for the freq metrics and the tagger).
    scored = [ranker.rank(list(analyses)) for analyses in analyses_by_token]

    # Context re-ranking needs the whole sequence, so compute it up front.
    context_ranked: List[List[Analysis]] = []
    if args.context:
        for analyses in analyses_by_token:
            context_ranked.append([Analysis(**{**a.__dict__}) for a in analyses])
        ranker.rerank_with_context(context_ranked)

    tagger_chosen = None
    if args.tagger:
        tagger_chosen = PosTagger(
            load_default_pos_model(), emission_weight=args.emission_weight
        ).tag(scored)

    for index, row in enumerate(sent):
        analyses = analyses_by_token[index]
        gold = normalize_lemma(row.lemma)
        counters = Counters(total=1)
        if not analyses:
            counters.misses = 1
        else:
            if first_match(analyses, gold) is not None:
                counters.coverage = 1
            if first_match(analyses, gold) == 0:
                counters.top1_before = 1
            freq_ranked = scored[index]
            freq_index = first_match(freq_ranked, gold)
            if freq_index == 0:
                counters.top1_freq = 1
            if freq_index is not None and freq_index < 3:
                counters.top3_freq = 1
            if tagger_chosen is not None:
                chosen = tagger_chosen[index]
                if chosen is not None and chosen.matches_lemma(gold):
                    counters.top1_tagger = 1
            if args.context:
                ctx_index = first_match(context_ranked[index], gold)
                if ctx_index == 0:
                    counters.top1_context = 1
            if freq_ranked and freq_ranked[0].pos == row.pos:
                counters.pos_agree = 1
        overall.add(counters)
        if args.by_source:
            by_source.setdefault(row.source or "(none)", Counters()).add(counters)

    print(overall.line("ALL", show_context=args.context, show_tagger=args.tagger))
    if args.by_source:
        for source, counters in sorted(by_source.items(), key=lambda item: -item[1].total):
            print(counters.line(f"  source={source}", show_context=args.context, show_tagger=args.tagger))
    print(
        "\nLegend: top1 = gold lemma is the first candidate; "
        "before = Morpheus order, freq/ctx = after ranking."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
