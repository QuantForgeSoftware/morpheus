#!/usr/bin/env python3
"""
Offline Greek benchmark + regression gate.

Runs every available local gold corpus through the current build and reports a
consolidated table of coverage / top-1 lemma (raw Morpheus order, frequency
ranking, and optionally the learned re-ranker) / coarse POS. Compares the results
against the committed thresholds in ``benchmarks/expected_greek.json`` and exits
non-zero if any metric falls outside its tolerance.

**Offline only** (no CI/GitHub): run it by hand, or from a local pre-commit hook.
Corpora are read from environment variables / flags, never hardcoded paths:

  MORPHGNT_DIR   MorphGNT SBLGNT *.txt            (CC-BY-SA 4.0)
  AF_CORPUS_DIR  Apostolic Fathers data/morph     (CC-BY-SA 4.0)
  AGLDT_DIR      AGLDT v2.1 Greek texts *.tb.xml  (CC-BY-SA 3.0 US)
  PROIEL_DIR     syntacticus greek-nt.conll       (CC BY-NC-SA; measurement only)

Usage:
  scripts/benchmark.py                       # check against thresholds
  scripts/benchmark.py --update              # rewrite thresholds from this run
  scripts/benchmark.py --learned --bootstrap 200
  MORPHGNT_DIR=... AF_CORPUS_DIR=... scripts/benchmark.py
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import normalize_lemma, to_beta  # noqa: E402
from morpheus_toolkit.learned import LearnedRanker, load_default_model  # noqa: E402
from morpheus_toolkit.ranking import (  # noqa: E402
    Ranker,
    load_default_frequencies,
    load_default_joint_frequencies,
)
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402

EXPECTED = os.path.join(REPO, "benchmarks", "expected_greek.json")
WORD_RE = re.compile(r'<word id="\d+" form="([^"]*)" lemma="([^"]*)"(?: postag="([a-z]))?')

# AGLDT Greek postag position 1 -> acceptable Morpheus classes (see Round 9).
AGLDT_CLASSES = {
    "n": {"N", "A"}, "a": {"A", "N"}, "v": {"V"}, "d": {"D"}, "g": {"X", "D"},
    "i": {"I"}, "l": {"RA"}, "p": {"RP", "RR", "RD"}, "r": {"P"}, "c": {"C"},
}
# PROIEL UPOS -> acceptable Morpheus classes (see Round 8).
PROIEL_CLASSES = {
    "N": {"N", "A"}, "V": {"V"}, "S": {"RA"}, "P": {"RP", "RR", "RD"},
    "D": {"D", "C"}, "R": {"P"}, "C": {"C"}, "A": {"A"}, "G": {"C", "D"},
}


@dataclass
class Row:
    token: str
    lemma: str
    pos: str       # gold POS, already in Morpheus's coarse scheme (or "")
    ref: str       # context group id
    classes: Optional[frozenset] = None  # acceptable classes (external tagsets)


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if not 0x0300 <= ord(c) <= 0x036F
    )


def clean_proiel_lemma(lemma: str) -> str:
    lemma = re.sub(r"#\d+$", "", lemma)
    return re.sub(r"\(([^)]*)\)", r"\1", lemma)


# --------------------------------------------------------------------------- readers
def read_morphgnt(directory: str, limit: int = 0) -> List[Row]:
    rows: List[Row] = []
    for path in sorted(glob.glob(os.path.join(directory, "*.txt"))):
        for line in open(path, encoding="utf-8", errors="replace"):
            f = line.split()
            if len(f) < 7:
                continue
            rows.append(Row(f[4], f[6], f[1].rstrip("-"), f[0]))
            if limit and len(rows) >= limit:
                return rows
    return rows


def read_columnar(paths: List[str], limit: int = 0) -> List[Row]:
    rows: List[Row] = []
    for path in paths:
        for line in open(path, encoding="utf-8", errors="replace"):
            f = line.split()
            if len(f) < 7 or (len(f) >= 8 and f[7] != "grc"):
                continue
            rows.append(Row(f[4], f[6], f[1].rstrip("-"), f[0]))
            if limit and len(rows) >= limit:
                return rows
    return rows


def read_agldt(directory: str, limit: int = 0) -> List[Row]:
    rows: List[Row] = []
    for path in sorted(glob.glob(os.path.join(directory, "*.tb.xml"))):
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        for m in WORD_RE.finditer(text):
            form, lemma, pos1 = m.group(1), m.group(2), m.group(3) or ""
            if not form or not lemma or not pos1 or pos1 == "u":
                continue
            rows.append(Row(form, lemma, "", path, frozenset(AGLDT_CLASSES.get(pos1, ()))))
            if limit and len(rows) >= limit:
                return rows
    return rows


def read_proiel(path: str, limit: int = 0) -> List[Row]:
    rows: List[Row] = []
    ref = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line.strip():
            ref += 1
            continue
        f = line.split()
        if len(f) < 6 or not f[1] or not f[2]:
            continue
        rows.append(Row(f[1], clean_proiel_lemma(f[2]), "",
                        str(ref), frozenset(PROIEL_CLASSES.get(f[3], ()))))
        if limit and len(rows) >= limit:
            return rows
    return rows


# --------------------------------------------------------------------------- metrics
@dataclass
class Counters:
    n: int = 0
    misses: int = 0
    covered: int = 0
    raw: int = 0
    ranked: int = 0
    learned: int = 0
    pos_n: int = 0
    pos: int = 0
    raw_flags: List[int] = None
    ranked_flags: List[int] = None
    learned_flags: List[int] = None

    def pct(self, value: int) -> float:
        return 100.0 * value / self.n if self.n else 0.0

    def as_dict(self) -> Dict[str, float]:
        analyzed = self.n - self.misses
        return {
            "n": self.n,
            "analyzed": round(100.0 * analyzed / self.n, 2) if self.n else 0.0,
            "coverage": round(self.pct(self.covered), 2),
            "top1_raw": round(self.pct(self.raw), 2),
            "top1_ranked": round(self.pct(self.ranked), 2),
            "top1_learned": round(self.pct(self.learned), 2) if self.learned_flags else None,
            "pos": round(100.0 * self.pos / self.pos_n, 2) if self.pos_n else 0.0,
        }


def evaluate(rows: List[Row], runner: MorpheusRunner, ranker: Ranker,
             learned: Optional[LearnedRanker], ignore_accents: bool = False) -> Counters:
    counters = Counters(raw_flags=[], ranked_flags=[], learned_flags=[])
    groups: Dict[str, List[Row]] = {}
    for row in rows:
        groups.setdefault(row.ref, []).append(row)

    for group in groups.values():
        betas = [to_beta(row.token) for row in group]
        valid = [i for i, b in enumerate(betas) if b]
        analyses: List[list] = [[] for _ in group]
        if valid:
            batch = 4000
            for start in range(0, len(valid), batch):
                sub = valid[start:start + batch]
                for i, cand in zip(sub, runner.analyze_beta(
                        [betas[i] for i in sub], ignore_accents=ignore_accents)):
                    analyses[i] = cand
        raw = [list(a) for a in analyses]
        ranked = [ranker.rank(list(a)) for a in analyses]
        learned_ranked = None
        if learned is not None:
            learned_ranked = learned.rank_sequence(
                [(betas[i], list(analyses[i])) for i in range(len(group))]
            )
        for i, row in enumerate(group):
            counters.n += 1
            cand = analyses[i]
            if not cand:
                counters.misses += 1
                counters.raw_flags.append(0)
                counters.ranked_flags.append(0)
                counters.learned_flags.append(0)
                continue
            if any(a.matches_lemma(row.lemma) for a in cand):
                counters.covered += 1
            hit_raw = int(bool(raw[i]) and raw[i][0].matches_lemma(row.lemma))
            hit_rank = int(bool(ranked[i]) and ranked[i][0].matches_lemma(row.lemma))
            counters.raw += hit_raw
            counters.ranked += hit_rank
            counters.raw_flags.append(hit_raw)
            counters.ranked_flags.append(hit_rank)
            if learned_ranked is not None:
                top = learned_ranked[i]
                hit = int(bool(top) and top[0].matches_lemma(row.lemma))
                counters.learned += hit
                counters.learned_flags.append(hit)
            # POS: exact class for Morpheus-scheme corpora, membership otherwise.
            if row.classes is not None:
                if row.classes:
                    counters.pos_n += 1
                    counters.pos += int(ranked[i][0].pos in row.classes)
            else:
                counters.pos_n += 1
                counters.pos += int(ranked[i][0].pos == row.pos)
    return counters


def bootstrap_ci(flags_a: List[int], flags_b: List[int], rounds: int, seed: int = 1) -> Tuple[float, float]:
    """95% CI for (b - a) in percentage points, paired over tokens."""
    if not flags_a or len(flags_a) != len(flags_b):
        return (0.0, 0.0)
    diffs = [b - a for a, b in zip(flags_a, flags_b)]
    n = len(diffs)
    rng = random.Random(seed)
    estimates = []
    for _ in range(rounds):
        total = 0
        for _ in range(n):
            total += diffs[rng.randrange(n)]
        estimates.append(100.0 * total / n)
    estimates.sort()
    lo = estimates[int(0.025 * rounds)]
    hi = estimates[int(0.975 * rounds) - 1]
    return (round(lo, 2), round(hi, 2))


# --------------------------------------------------------------------------- driver
def discover(args) -> List[Tuple[str, List[Row], bool]]:
    corpora: List[Tuple[str, List[Row], bool]] = []
    morphgnt = args.morphgnt_dir or os.environ.get("MORPHGNT_DIR", "")
    if morphgnt and os.path.isdir(morphgnt):
        corpora.append(("SBLGNT", read_morphgnt(morphgnt, args.limit), False))
    af = args.af_corpus_dir or os.environ.get("AF_CORPUS_DIR", "")
    if af:
        paths = glob.glob(os.path.join(af, "*.txt")) if os.path.isdir(af) else [af]
        corpora.append(("Apostolic Fathers", read_columnar(sorted(paths), args.limit), False))
    agldt = args.agldt_dir or os.environ.get("AGLDT_DIR", "")
    if agldt and os.path.isdir(agldt):
        # Classical editions mark unaccented/elided forms; match that evaluator.
        corpora.append(("AGLDT classical", read_agldt(agldt, args.limit), True))
    proiel = args.proiel_dir or os.environ.get("PROIEL_DIR", "")
    if proiel and os.path.isfile(proiel):
        corpora.append(("PROIEL greek-nt", read_proiel(proiel, args.limit), True))
    return [(name, rows, acc) for name, rows, acc in corpora if rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--morphgnt-dir", default="")
    ap.add_argument("--af-corpus-dir", default="")
    ap.add_argument("--agldt-dir", default="")
    ap.add_argument("--proiel-dir", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--learned", action="store_true")
    ap.add_argument("--joint", action="store_true", help="rank by joint (lemma, POS) frequency")
    ap.add_argument("--bootstrap", type=int, default=0,
                    help="bootstrap rounds for the learned-vs-ranked 95%% CI")
    ap.add_argument("--update", action="store_true", help="rewrite the expected thresholds")
    ap.add_argument("--tolerance", type=float, default=0.5, help="allowed pp drop")
    args = ap.parse_args()

    corpora = discover(args)
    if not corpora:
        print("no corpora found — set MORPHGNT_DIR / AF_CORPUS_DIR / AGLDT_DIR / PROIEL_DIR")
        return 0

    runner = MorpheusRunner()
    ranker = Ranker(
        load_default_frequencies(),
        joint_frequencies=(load_default_joint_frequencies() or None) if args.joint else None,
    )
    learned = None
    if args.learned:
        model = load_default_model()
        if not model.get("weights"):
            print("no learned model; run scripts/build_learned_model.py")
            return 2
        learned = LearnedRanker(model, frequencies=ranker.frequencies, joint=ranker.joint)

    results: Dict[str, dict] = {}
    failures: List[str] = []
    expected: Dict[str, dict] = {}
    if os.path.exists(EXPECTED):
        expected = json.load(open(EXPECTED, encoding="utf-8")).get("corpora", {})

    for name, rows, ignore_accents in corpora:
        counters = evaluate(rows, runner, ranker, learned, ignore_accents)
        metrics = counters.as_dict()
        results[name] = metrics
        learned_str = f" learned={metrics['top1_learned']:5.1f}%" if metrics["top1_learned"] is not None else ""
        print(f"{name:<20} n={metrics['n']:<7} analyzed={metrics['analyzed']:5.1f}% "
              f"cov={metrics['coverage']:5.1f}% "
              f"raw={metrics['top1_raw']:5.1f}%->ranked={metrics['top1_ranked']:5.1f}%"
              f"{learned_str} pos={metrics['pos']:5.1f}%")
        if args.bootstrap and counters.learned_flags and metrics["top1_learned"] is not None:
            lo, hi = bootstrap_ci(counters.ranked_flags, counters.learned_flags, args.bootstrap)
            print(f"{'':<20} learned - ranked 95% CI: [{lo:+.2f}, {hi:+.2f}] pp")
        exp = expected.get(name)
        if exp and not args.update:
            for key in ("coverage", "top1_ranked", "pos"):
                if metrics[key] < exp[key] - args.tolerance:
                    failures.append(f"{name}.{key}: {metrics[key]} < {exp[key]} (tol {args.tolerance})")

    if args.update:
        os.makedirs(os.path.dirname(EXPECTED), exist_ok=True)
        with open(EXPECTED, "w", encoding="utf-8") as handle:
            json.dump({"note": "Offline regression thresholds (see scripts/benchmark.py).",
                       "corpora": results}, handle, ensure_ascii=False, indent=2)
        print(f"\nWrote thresholds to {EXPECTED}")
        return 0

    if failures:
        print("\nREGRESSION:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("\nOK (within tolerance)" if expected else "\nNo thresholds yet — run with --update")
    return 0


if __name__ == "__main__":
    sys.exit(main())
