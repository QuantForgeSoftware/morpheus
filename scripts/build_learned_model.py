#!/usr/bin/env python3
"""
Train the learned candidate re-ranker (``data/learned_reranker.json``).

A structured (per-token) averaged perceptron over Morpheus's candidate analyses:
at each token it scores every candidate with the shared feature extractor in
``morpheus_toolkit.learned`` and, when the gold reading is not ranked first,
nudges the weights toward it. Features include lemma frequency and its *rank*,
fine POS, stem type, and POS interactions with the neighbouring tokens — the
signals frequency ranking alone cannot use.

Training gold must be commit-safe: MorphGNT SBLGNT (CC-BY-SA 4.0) and/or the
Apostolic Fathers corpus. PROIEL is CC BY-NC-SA and must never be used here.

Usage:
  scripts/build_learned_model.py --morphgnt-dir ~/Code/bibloi/data/morphgnt \\
      ../apostolic-fathers/data/morph/*.txt \\
      --lemma-field 7 --pos-field 2 --lang-field 8 --lang-value grc

Then evaluate with ``scripts/agreement_report.py --learned``.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import re
import sys
from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.analysis import Analysis  # noqa: E402
from morpheus_toolkit.beta import normalize_lemma, to_beta  # noqa: E402
from morpheus_toolkit.learned import LearnedRanker  # noqa: E402
from morpheus_toolkit.ranking import (  # noqa: E402
    load_default_frequencies,
    load_default_joint_frequencies,
)
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402


WORD_RE = re.compile(r'<word id="\d+" form="([^"]*)" lemma="([^"]*)"(?: postag="([a-z]))?')
# AGLDT Greek postag position 1 -> coarse Morpheus POS (used only as a tie-break
# among candidates; see tmp/grc/eval_grc.py for the empirical mapping).
AGLDT_POS = {"n": "N", "a": "A", "v": "V", "d": "D", "g": "X", "l": "RA",
             "p": "RP", "r": "P", "c": "C", "i": "I"}


class AveragedPerceptron:
    """Averaged perceptron with the timestamp trick (sparse weights)."""

    def __init__(self) -> None:
        self.weights: Dict[str, float] = {}
        self._totals: Dict[str, float] = {}
        self._tstamps: Dict[str, int] = {}
        self.i = 0

    def _update(self, feat: str, delta: float) -> None:
        self._totals[feat] = self._totals.get(feat, 0.0) + (
            self.i - self._tstamps.get(feat, 0)
        ) * self.weights.get(feat, 0.0)
        self._tstamps[feat] = self.i
        self.weights[feat] = self.weights.get(feat, 0.0) + delta

    def update(self, gold: Sequence[str], pred: Sequence[str]) -> None:
        for feat in gold:
            self._update(feat, 1.0)
        for feat in pred:
            self._update(feat, -1.0)
        self.i += 1

    def averaged(self) -> Dict[str, float]:
        total = self.i or 1
        out: Dict[str, float] = {}
        for feat, weight in self.weights.items():
            accumulated = self._totals.get(feat, 0.0) + (
                self.i - self._tstamps.get(feat, 0)
            ) * weight
            out[feat] = accumulated / total
        return out


def read_columnar(paths: List[str], args) -> List[Tuple[str, str, str, str]]:
    """Return (ref, token, lemma, pos) rows from columnar MorphGNT/AF files."""
    rows: List[Tuple[str, str, str, str]] = []
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                fields = line.split()
                need = max(args.token_field, args.lemma_field, args.pos_field)
                if len(fields) < need:
                    continue
                if args.lang_field and (
                    len(fields) >= args.lang_field
                    and fields[args.lang_field - 1] != args.lang_value
                ):
                    continue
                rows.append((
                    f"{path}#{fields[0]}",
                    fields[args.token_field - 1],
                    fields[args.lemma_field - 1],
                    fields[args.pos_field - 1].rstrip("-"),
                ))
    return rows


def read_agldt(directory: str) -> List[Tuple[str, str, str, str]]:
    """Return (ref, token, lemma, pos) rows from AGLDT v2.1 Greek *.tb.xml files.

    Each file is one context chunk (ref carries the path). Perseus-style trailing
    homonym digits in the lemma are left for ``normalize_lemma`` to strip; numerals
    (postag `m`) and unannotated words (`u`) are skipped (Morpheus has no numeral
    POS, and they add no training signal here).
    """
    rows: List[Tuple[str, str, str, str]] = []
    for path in sorted(glob.glob(os.path.join(directory, "*.tb.xml"))):
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for match in WORD_RE.finditer(text):
            form, lemma, pos1 = match.group(1), match.group(2), match.group(3) or ""
            if not form or not lemma or pos1 in ("", "u", "m"):
                continue
            rows.append((f"{path}#", form, lemma, AGLDT_POS.get(pos1, "")))
    return rows


def assign_chunks(rows: List[Tuple[str, str, str, str]]) -> List[Tuple[str, str, str, str]]:
    """Give each contiguous same-ref run a sequential chunk id."""
    out: List[Tuple[str, str, str, str]] = []
    previous: Optional[str] = None
    cid = -1
    for ref, token, lemma, pos in rows:
        if ref != previous:
            cid += 1
            previous = ref
        out.append((str(cid), token, lemma, pos))
    return out


def gold_index(analyses: List[Analysis], gold_lemma: str, gold_pos: str) -> Optional[int]:
    target = normalize_lemma(gold_lemma)
    matches = [
        i for i, a in enumerate(analyses)
        if any(normalize_lemma(v) == target for v in a.variants())
    ]
    if not matches:
        return None
    for i in matches:
        if analyses[i].pos == gold_pos:
            return i
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument("--agldt-dir", default=os.environ.get("AGLDT_DIR", ""),
                        help="AGLDT v2.1 Greek *.tb.xml directory to pool (CC BY-SA 3.0 US)")
    parser.add_argument("--agldt-limit", type=int, default=0,
                        help="uniformly subsample AGLDT to this many tokens (0 = all) — "
                             "balances the pool against the Koine corpora")
    parser.add_argument("--token-field", type=int, default=5)
    parser.add_argument("--lemma-field", type=int, default=7)
    parser.add_argument("--pos-field", type=int, default=2)
    parser.add_argument("--lang-field", type=int, default=0)
    parser.add_argument("--lang-value", default="grc")
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--min-count", type=int, default=2,
                        help="prune features seen fewer than this many times")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--frequencies", default="")
    parser.add_argument("--joint", action="store_true")
    parser.add_argument("--lemma-context", action="store_true",
                        help="add neighbour closed-class lemma features (measured to "
                             "overfit / propagate context noise — off by default)")
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "learned_reranker.json"),
    )
    args = parser.parse_args()

    paths = list(args.paths)
    if args.morphgnt_dir:
        paths += sorted(glob.glob(os.path.join(args.morphgnt_dir, "*.txt")))
    if not paths and not args.agldt_dir:
        parser.error("give file paths, --morphgnt-dir, or --agldt-dir")

    if args.frequencies:
        with open(args.frequencies, encoding="utf-8") as handle:
            freq_data = json.load(handle)
        frequencies = freq_data.get("frequencies", freq_data)
        joint = freq_data.get("by_pos") if args.joint else None
        source = os.path.basename(args.frequencies)
    else:
        frequencies = load_default_frequencies()
        joint = load_default_joint_frequencies() if args.joint else None
        source = "MorphGNT SBLGNT (CC-BY-SA 4.0)"

    rows = read_columnar(paths, args)
    if args.agldt_dir:
        agldt_rows = read_agldt(args.agldt_dir)
        if args.agldt_limit and len(agldt_rows) > args.agldt_limit:
            step = len(agldt_rows) / args.agldt_limit
            agldt_rows = [agldt_rows[int(i * step)] for i in range(args.agldt_limit)]
        print(f"  AGLDT: {len(agldt_rows)} tokens from {args.agldt_dir}")
        rows += agldt_rows
        source += " + Apostolic Fathers + AGLDT v2.1 Greek (CC BY-SA 3.0 US)"
    rows = assign_chunks(rows)
    if args.limit:
        rows = rows[: args.limit]
    print(f"read {len(rows)} gold tokens")

    extractor = LearnedRanker({"weights": {}, "lemma_context": args.lemma_context},
                              frequencies=frequencies, joint=joint or {})
    runner = MorpheusRunner()

    # Build training examples: (list of candidate-feature tuples, gold index).
    examples: List[Tuple[List[Tuple[str, ...]], int]] = []
    feature_counts: Counter = Counter()
    by_chunk: Dict[str, List[Tuple[str, str, str]]] = {}
    for cid, token, lemma, pos in rows:
        by_chunk.setdefault(cid, []).append((token, lemma, pos))

    analyzed = 0
    for cid in sorted(by_chunk, key=lambda c: int(c)):
        chunk = by_chunk[cid]
        betas = [to_beta(token) for token, _, _ in chunk]
        valid = [(i, b) for i, b in enumerate(betas) if b]
        analyses_list: List[List[Analysis]] = [[] for _ in chunk]
        if valid:
            batch = 4000
            for start in range(0, len(valid), batch):
                sub = valid[start:start + batch]
                raw = runner.analyze_beta([b for _, b in sub])
                for (i, _), analyses in zip(sub, raw):
                    analyses_list[i] = analyses
        # Context = frequency-ranked top-1 (POS, lemma) of the neighbours.
        tops: List[Optional[Tuple[str, str]]] = []
        for analyses in analyses_list:
            if analyses:
                best = max(analyses, key=lambda a: (extractor._best_frequency(a), a.lemma))
                tops.append((best.pos, normalize_lemma(best.lemma)))
            else:
                tops.append(None)
        for index, (_, lemma, pos) in enumerate(chunk):
            analyses = analyses_list[index]
            if not analyses:
                continue
            gi = gold_index(analyses, lemma, pos)
            if gi is None:
                continue
            ordered = sorted(
                range(len(analyses)),
                key=lambda j: (-extractor._best_frequency(analyses[j]), analyses[j].lemma),
            )
            rank_of = {j: r for r, j in enumerate(ordered)}
            prev_ctx = tops[index - 1] if index > 0 else None
            next_ctx = tops[index + 1] if index + 1 < len(tops) else None
            cand_feats: List[Tuple[str, ...]] = []
            for j, analysis in enumerate(analyses):
                feats = extractor.features(
                    analysis, betas[index], prev_ctx, next_ctx, rank_of[j]
                )
                keys = tuple(feats)
                feature_counts.update(keys)
                cand_feats.append(keys)
            examples.append((cand_feats, gi))
            analyzed += 1
        if analyzed and analyzed % 20000 < len(chunk) + 1:
            print(f"  prepared {analyzed} tokens")

    print(f"{analyzed} analyzable tokens, {len(feature_counts)} distinct features")
    if not examples:
        parser.error("no training examples (gold lemmas never matched Morpheus?)")

    random.seed(args.seed)
    model = AveragedPerceptron()
    for epoch in range(args.epochs):
        order = list(range(len(examples)))
        random.shuffle(order)
        mistakes = 0
        for idx in order:
            cand_feats, gi = examples[idx]
            best_j = 0
            best_score = None
            for j, keys in enumerate(cand_feats):
                score = sum(model.weights.get(k, 0.0) for k in keys)
                if best_score is None or score > best_score:
                    best_score, best_j = score, j
            if best_j != gi:
                model.update(cand_feats[gi], cand_feats[best_j])
                mistakes += 1
        print(f"epoch {epoch + 1}: train top-1 errors {mistakes}/{len(examples)}")

    averaged = model.averaged()
    kept = {
        feat: round(weight, 6)
        for feat, weight in averaged.items()
        if feature_counts.get(feat, 0) >= args.min_count and abs(weight) > 1e-9
    }
    payload = {
        "source": source,
        "features": len(kept),
        "lemma_context": args.lemma_context,
        "notes": "Averaged-perceptron learned re-ranker; see scripts/build_learned_model.py.",
        "weights": kept,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    print(f"Wrote {len(kept)} feature weights to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
