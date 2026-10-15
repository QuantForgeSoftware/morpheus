#!/usr/bin/env python3
"""
Fit the softmax temperature for the reported analysis confidence.

The ranker's scores are ordering scores, so the raw softmax ``confidence`` is
miscalibrated (top-1 is systematically over-confident). This grid-searches a
single temperature T that minimises the negative log-likelihood of the gold
reading under softmax(scores / T), writes it to ``data/calibration.json``, and
reports the top-1 expected calibration error (ECE) before/after.

Fit on one commit-safe corpus and check the number transfers to another:

  scripts/calibrate.py --morphgnt-dir ~/Code/bibloi/data/morphgnt \\
      --af-corpus-dir /path/to/apostolic-fathers/data/morph
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from typing import List, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import to_beta  # noqa: E402
from morpheus_toolkit.calibration import expected_calibration_error, softmax_confidences  # noqa: E402
from morpheus_toolkit.ranking import Ranker, load_default_frequencies  # noqa: E402
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402


def read_morphgnt(directory: str) -> List[Tuple[str, str]]:
    rows = []
    for path in sorted(glob.glob(os.path.join(directory, "*.txt"))):
        for line in open(path, encoding="utf-8", errors="replace"):
            f = line.split()
            if len(f) >= 7:
                rows.append((f[4], f[6]))
    return rows


def read_columnar(paths: List[str]) -> List[Tuple[str, str]]:
    rows = []
    for path in paths:
        for line in open(path, encoding="utf-8", errors="replace"):
            f = line.split()
            if len(f) >= 7 and (len(f) < 8 or f[7] == "grc"):
                rows.append((f[4], f[6]))
    return rows


def collect(rows, runner, ranker, learned=None):
    """Return (scores-per-token, gold-index, top1-correct) for covered tokens.

    With ``learned`` the candidates are re-ranked by the bundled learned model
    (per 2000-token chunk, mirroring the shipped per-input sequence) and its
    scores are collected; otherwise the frequency ranker's scores are used.
    """
    betas = [to_beta(token) for token, _ in rows]
    examples = []
    for i in range(0, len(betas), 2000):
        chunk = betas[i:i + 2000]
        valid = [(j, b) for j, b in enumerate(chunk) if b]
        analyses = runner.analyze_beta([b for _, b in valid])
        cands = [[] for _ in chunk]
        for (j, _), cand in zip(valid, analyses):
            cands[j] = list(cand)
        if learned is not None:
            ranked_chunk = learned.rank_sequence(
                [(chunk[j] or "", cands[j]) for j in range(len(chunk))]
            )
        else:
            ranked_chunk = [ranker.rank(list(c)) if c else [] for c in cands]
        for j in range(len(chunk)):
            ranked = ranked_chunk[j]
            if not ranked:
                continue
            gold_row = rows[i + j]
            match = next((k for k, a in enumerate(ranked) if a.matches_lemma(gold_row[1])), None)
            if match is None:
                continue
            examples.append(([a.score for a in ranked], match))
    return examples


def nll(examples, temperature: float) -> float:
    total = 0.0
    for scores, gold in examples:
        probs = softmax_confidences(scores, temperature)
        total += -math.log(max(probs[gold], 1e-12))
    return total / max(len(examples), 1)


def top1_calibration(examples, temperature: float):
    confidences, correct = [], []
    for scores, gold in examples:
        probs = softmax_confidences(scores, temperature)
        confidences.append(probs[0])
        correct.append(1 if gold == 0 else 0)
    return expected_calibration_error(confidences, correct), sum(correct) / max(len(correct), 1)


def fit(examples):
    best_t, best = 1.0, None
    for step in range(20, 300, 5):  # 0.20 .. 2.95
        temperature = step / 100.0
        value = nll(examples, temperature)
        if best is None or value < best:
            best, best_t = value, temperature
    for step in range(int(best_t * 100) - 40, int(best_t * 100) + 41, 2):  # refine +-0.4
        temperature = step / 100.0
        if temperature <= 0:
            continue
        value = nll(examples, temperature)
        if value < best:
            best, best_t = value, temperature
    return best_t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    ap.add_argument("--af-corpus-dir", default=os.environ.get("AF_CORPUS_DIR", ""))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--learned", action="store_true",
                    help="fit the temperature for the learned path (stores temperature_learned)")
    ap.add_argument("--out", default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "calibration.json"))
    args = ap.parse_args()

    runner = MorpheusRunner()
    ranker = Ranker(load_default_frequencies())
    learned = None
    if args.learned:
        from morpheus_toolkit.learned import LearnedRanker, load_default_model

        learned = LearnedRanker(load_default_model(), frequencies=ranker.frequencies)

    fit_examples = []
    if args.morphgnt_dir:
        rows = read_morphgnt(args.morphgnt_dir)
        if args.limit:
            rows = rows[: args.limit]
        fit_examples = collect(rows, runner, ranker, learned)
        print(f"fit corpus: {len(fit_examples)} covered tokens (SBLGNT)")
    if not fit_examples:
        ap.error("--morphgnt-dir required (no fit examples)")

    temperature = fit(fit_examples)
    ece1, acc1 = top1_calibration(fit_examples, 1.0)
    eceT, accT = top1_calibration(fit_examples, temperature)
    print(f"fit:   T=1.0 ECE={ece1:.3f}  acc={acc1:.3f} | T={temperature:.2f} ECE={eceT:.3f} acc={accT:.3f}")

    suffix = "_learned" if args.learned else ""
    payload = {
        f"temperature{suffix}": round(temperature, 3),
        "method": "temperature scaling, NLL grid search",
        "source": "MorphGNT SBLGNT (CC-BY-SA 4.0); see scripts/calibrate.py",
        f"fit_ece_t1{suffix}": round(ece1, 4),
        f"fit_ece_calibrated{suffix}": round(eceT, 4),
    }
    if args.af_corpus_dir:
        rows = read_columnar(sorted(glob.glob(os.path.join(args.af_corpus_dir, "*.txt"))))
        if args.limit:
            rows = rows[: args.limit]
        eval_examples = collect(rows, runner, ranker, learned)
        e1, a1 = top1_calibration(eval_examples, 1.0)
        eT, aT = top1_calibration(eval_examples, temperature)
        print(f"eval:  Apostolic Fathers {len(eval_examples)} tokens | "
              f"T=1.0 ECE={e1:.3f} | T={temperature:.2f} ECE={eT:.3f}")
        payload[f"af_ece_t1{suffix}"] = round(e1, 4)
        payload[f"af_ece_calibrated{suffix}"] = round(eT, 4)

    # Merge into any existing calibration file so the freq and learned fits coexist.
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as handle:
            existing = json.load(handle)
        existing.update(payload)
        payload = existing

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"wrote {args.out}: temperature{suffix}={payload[f'temperature{suffix}']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
