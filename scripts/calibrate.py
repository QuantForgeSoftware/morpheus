#!/usr/bin/env python3
"""
Fit the softmax temperature for the reported analysis confidence.

The ranker's scores are ordering scores, so the raw softmax ``confidence`` is
miscalibrated (top-1 is systematically over-confident). This grid-searches a
single temperature T that minimises the negative log-likelihood of the gold
reading under softmax(scores / T), writes it to ``data/calibration.json``, and
reports the top-1 expected calibration error (ECE) before/after — for the score
path in use: plain frequency (``temperature``), joint (lemma, POS)
(``temperature_joint``, ``--joint``) or learned (``temperature_learned``,
``--learned``).

It also fits the POS confidence: the class-mass estimate
(``calibration.class_masses``) is peaked for the lemma, not for the class, so a
per-class reliability (P(top class correct | predicted class)) is fitted and
reported with the ECE of the mass, of the reliability, and of their product (the
estimator ``api._annotate`` uses). One table is written per score path.

Fit on one commit-safe corpus and check the number transfers to another:

  scripts/calibrate.py --morphgnt-dir ~/Code/bibloi/data/morphgnt \\
      --af-corpus-dir /path/to/apostolic-fathers/data/morph

Proposal priors (``--proposal-priors --papygreek-dir DIR``): tokens whose
candidates are all proposals get a confidence *conditional on the generated
candidate set*, so a lone proposal reports 1.0; this mode measures the top-1
accuracy per proposal strategy through the shipped API path and writes
``proposal_priors`` for ``api._annotate`` to scale by.
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import math
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import normalize_lemma, to_beta  # noqa: E402
from morpheus_toolkit.calibration import (  # noqa: E402
    class_masses,
    coarse_pos,
    expected_calibration_error,
    softmax_confidences,
)
from morpheus_toolkit.ranking import (  # noqa: E402
    Ranker,
    load_default_frequencies,
    load_default_joint_frequencies,
)
from morpheus_toolkit.recovery import proposal_strategy  # noqa: E402
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402

# PapyGreek editorial markers (same inventory as scripts/benchmark.py).
PG_PIPE_ANN = re.compile(r"\|[a-z]+:[^|]*\|")
PG_MARKERS = re.compile(
    r"[∼∽∤⋰⋱⸢⸣❨❩<>[\]{}()〚〛⊢⊣⸌⸍⎴⎵⦑⦒⸜⸝⧼?…-]+|[̣̅]")
PG_GREEK = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
PG_WORD = re.compile(r"<word\s+([^>]+)/>")


def gold_class(pos_field: str) -> str:
    """Coarse class of a reference-corpus POS tag (MorphGNT/AF style)."""
    return coarse_pos(pos_field.rstrip("-"))


def read_morphgnt(directory: str) -> List[Tuple[str, str, str]]:
    rows = []
    for path in sorted(glob.glob(os.path.join(directory, "*.txt"))):
        for line in open(path, encoding="utf-8", errors="replace"):
            f = line.split()
            if len(f) >= 7:
                rows.append((f[4], f[6], gold_class(f[1])))
    return rows


def read_columnar(paths: List[str]) -> List[Tuple[str, str, str]]:
    rows = []
    for path in paths:
        for line in open(path, encoding="utf-8", errors="replace"):
            f = line.split()
            if len(f) >= 7 and (len(f) < 8 or f[7] == "grc"):
                rows.append((f[4], f[6], gold_class(f[1])))
    return rows


def read_papygreek(directory: str) -> List[Tuple[str, str]]:
    """(surface, regularized gold lemma) rows from the PapyGreek treebanks."""
    rows: List[Tuple[str, str]] = []
    for path in sorted(glob.glob(os.path.join(directory, "**", "*.xml"), recursive=True)):
        try:
            content = html.unescape(open(path, encoding="utf-8", errors="replace").read())
        except OSError:
            continue
        for match in PG_WORD.finditer(content):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))
            if attrs.get("lang", "grc") != "grc":
                continue
            form = PG_MARKERS.sub("", PG_PIPE_ANN.sub("", attrs.get("form_orig", ""))).strip()
            lemma = PG_PIPE_ANN.sub("", attrs.get("lemma_reg", ""))
            postag = attrs.get("postag_reg", "")
            if not form or not lemma or (postag[:1] or "") in ("", "u"):
                continue
            if not PG_GREEK.search(form):
                continue
            rows.append((form, lemma))
    return rows


def collect(rows, runner, ranker, learned=None):
    """Return (scores, gold-index, classes, gold-class) for covered tokens.

    With ``learned`` the candidates are re-ranked by the bundled learned model
    (per 2000-token chunk, mirroring the shipped per-input sequence) and its
    scores are collected; otherwise the frequency ranker's scores are used.
    """
    betas = [to_beta(token) for token, _, _ in rows]
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
            examples.append((
                [a.score for a in ranked],
                match,
                [coarse_pos(a.pos) for a in ranked],
                gold_row[2],
            ))
    return examples


def nll(examples, temperature: float) -> float:
    total = 0.0
    for scores, gold, _classes, _gold_class in examples:
        probs = softmax_confidences(scores, temperature)
        total += -math.log(max(probs[gold], 1e-12))
    return total / max(len(examples), 1)


def top1_calibration(examples, temperature: float):
    confidences, correct = [], []
    for scores, gold, _classes, _gold_class in examples:
        probs = softmax_confidences(scores, temperature)
        confidences.append(probs[0])
        correct.append(1 if gold == 0 else 0)
    return expected_calibration_error(confidences, correct), sum(correct) / max(len(correct), 1)


def pos_report(examples, temperature: float):
    """POS-confidence calibration: class-mass vs per-class reliability.

    Returns (report, reliability): ``report`` carries the ECE of the class mass,
    of the per-class reliability alone, and of their product (the estimator the
    API uses); ``reliability`` maps coarse class -> P(top class correct), which
    is what gets stored for the API to multiply the class mass by.
    """
    counts = defaultdict(lambda: [0, 0])
    rows = []
    for scores, _gold, classes, gold_class in examples:
        probs = softmax_confidences(scores, temperature)
        masses = class_masses(classes, probs)
        top = classes[0]
        correct = 1 if top == gold_class else 0
        counts[top][0] += correct
        counts[top][1] += 1
        rows.append((masses[0], top, correct))
    total = [sum(v[0] for v in counts.values()), sum(v[1] for v in counts.values())]
    overall = total[0] / max(total[1], 1)
    reliability = {key: hits / n for key, (hits, n) in counts.items() if n}
    reliability["other"] = overall

    mass_conf, rel_conf, prod_conf, correct = [], [], [], []
    for mass, top, ok in rows:
        rel = reliability.get(top, overall)
        mass_conf.append(mass)
        rel_conf.append(rel)
        prod_conf.append(mass * rel)
        correct.append(ok)
    report = {
        "mass_ece": expected_calibration_error(mass_conf, correct),
        "reliability_ece": expected_calibration_error(rel_conf, correct),
        "product_ece": expected_calibration_error(prod_conf, correct),
        "accuracy": overall,
        "classes": {key: counts[key] for key in sorted(counts)},
    }
    return report, reliability


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


def fit_proposal_priors(rows, analyzer) -> Tuple[Dict[str, float], Dict[str, list]]:
    """Top-1 accuracy per proposal strategy through the shipped API path."""
    counts: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    batch = 2000
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        results = analyzer.analyze_tokens([token for token, _ in chunk])
        for result, (_token, gold) in zip(results, chunk):
            analyses = result.analyses
            if not analyses or not all(a.proposed for a in analyses):
                continue
            surface = result.token or ""
            strategy = proposal_strategy(analyses[0], surface) or "other"
            hit = int(normalize_lemma(analyses[0].lemma) == normalize_lemma(gold))
            counts[strategy][0] += hit
            counts[strategy][1] += 1
    priors = {key: round(hits / n, 4) for key, (hits, n) in counts.items() if n}
    totals = [sum(v[0] for v in counts.values()), sum(v[1] for v in counts.values())]
    if totals[1]:
        priors["other"] = round(totals[0] / totals[1], 4)
    return priors, {key: counts[key] for key in sorted(counts)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    ap.add_argument("--af-corpus-dir", default=os.environ.get("AF_CORPUS_DIR", ""))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--learned", action="store_true",
                    help="fit the temperature for the learned path (stores temperature_learned)")
    ap.add_argument("--joint", action="store_true",
                    help="fit the temperature for the joint (lemma, POS) path "
                         "(stores temperature_joint)")
    ap.add_argument("--papygreek-dir", default=os.environ.get("PAPYGREEK_DIR", ""),
                    help="PapyGreek treebanks directory (for --proposal-priors)")
    ap.add_argument("--proposal-priors", action="store_true",
                    help="measure per-strategy proposal accuracy on --papygreek-dir "
                         "through the shipped API path and store proposal_priors")
    ap.add_argument("--out", default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "calibration.json"))
    args = ap.parse_args()

    payload: Dict[str, object] = {}

    if args.proposal_priors:
        if not args.papygreek_dir:
            ap.error("--proposal-priors requires --papygreek-dir")
        from morpheus_toolkit.api import Morpheus

        rows = read_papygreek(args.papygreek_dir)
        if args.limit:
            rows = rows[: args.limit]
        analyzer = Morpheus(use_learned=args.learned)
        priors, counts = fit_proposal_priors(rows, analyzer)
        print(f"proposal priors on PapyGreek ({len(rows)} tokens):")
        for key in sorted(counts):
            hits, n = counts[key]
            print(f"  {key:9s} {hits}/{n} = {hits / n:.3f}" if n else f"  {key}: 0")
        payload["proposal_priors"] = priors
        payload["proposal_prior_counts"] = counts
        payload["proposal_prior_source"] = (
            "PapyGreek Treebanks v1.01 (CC-BY-SA 4.0), shipped API path"
        )

    if args.morphgnt_dir:
        runner = MorpheusRunner()
        ranker = Ranker(
            load_default_frequencies(),
            joint_frequencies=load_default_joint_frequencies() if args.joint else None,
        )
        learned = None
        if args.learned:
            from morpheus_toolkit.learned import LearnedRanker, load_default_model

            learned = LearnedRanker(load_default_model(), frequencies=ranker.frequencies)

        rows = read_morphgnt(args.morphgnt_dir)
        if args.limit:
            rows = rows[: args.limit]
        fit_examples = collect(rows, runner, ranker, learned)
        print(f"fit corpus: {len(fit_examples)} covered tokens (SBLGNT)")
        if not fit_examples:
            ap.error("no fit examples")

        temperature = fit(fit_examples)
        ece1, acc1 = top1_calibration(fit_examples, 1.0)
        eceT, accT = top1_calibration(fit_examples, temperature)
        pos1, _rel1 = pos_report(fit_examples, 1.0)
        posT, reliability = pos_report(fit_examples, temperature)
        print(f"fit:   T=1.0 ECE={ece1:.3f}  acc={acc1:.3f} | T={temperature:.2f} ECE={eceT:.3f} acc={accT:.3f}")
        print(f"pos:   mass ECE={posT['mass_ece']:.3f} | reliability ECE={posT['reliability_ece']:.3f} | "
              f"product ECE={posT['product_ece']:.3f} acc={posT['accuracy']:.3f}")

        suffix = "_learned" if args.learned else ("_joint" if args.joint else "")
        payload[f"temperature{suffix}"] = round(temperature, 3)
        payload["method"] = "temperature scaling, NLL grid search"
        payload["source"] = "MorphGNT SBLGNT (CC-BY-SA 4.0); see scripts/calibrate.py"
        payload[f"fit_ece_t1{suffix}"] = round(ece1, 4)
        payload[f"fit_ece_calibrated{suffix}"] = round(eceT, 4)
        payload[f"fit_pos_ece{suffix}"] = round(posT["product_ece"], 4)
        payload[f"fit_pos_acc{suffix}"] = round(posT["accuracy"], 4)
        payload[f"fit_pos_mass_ece{suffix}"] = round(posT["mass_ece"], 4)
        payload[f"fit_pos_reliability_ece{suffix}"] = round(posT["reliability_ece"], 4)
        payload[f"pos_reliability{suffix}"] = {
            key: round(value, 4) for key, value in reliability.items()
        }
        payload["pos_reliability_source"] = "MorphGNT SBLGNT (CC-BY-SA 4.0); see scripts/calibrate.py"
        if args.af_corpus_dir:
            rows = read_columnar(sorted(glob.glob(os.path.join(args.af_corpus_dir, "*.txt"))))
            if args.limit:
                rows = rows[: args.limit]
            eval_examples = collect(rows, runner, ranker, learned)
            e1, a1 = top1_calibration(eval_examples, 1.0)
            eT, aT = top1_calibration(eval_examples, temperature)
            peval, _rel = pos_report(eval_examples, temperature)
            print(f"eval:  Apostolic Fathers {len(eval_examples)} tokens | "
                  f"T=1.0 ECE={e1:.3f} | T={temperature:.2f} ECE={eT:.3f} | "
                  f"pos product ECE={peval['product_ece']:.3f} acc={peval['accuracy']:.3f}")
            payload[f"af_ece_t1{suffix}"] = round(e1, 4)
            payload[f"af_ece_calibrated{suffix}"] = round(eT, 4)
            payload[f"af_pos_ece{suffix}"] = round(peval["product_ece"], 4)
            payload[f"af_pos_acc{suffix}"] = round(peval["accuracy"], 4)
    elif not payload:
        ap.error("--morphgnt-dir required (no fit examples)")

    # Merge into any existing calibration file so the fits coexist.
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as handle:
            existing = json.load(handle)
        existing.update(payload)
        payload = existing

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    if "temperature" in payload or "temperature_joint" in payload or "temperature_learned" in payload:
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
