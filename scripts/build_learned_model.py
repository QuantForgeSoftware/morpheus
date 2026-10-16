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
import html
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
from morpheus_toolkit.recovery import recover  # noqa: E402
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402


WORD_RE = re.compile(r'<word id="\d+" form="([^"]*)" lemma="([^"]*)"(?: postag="([a-z]))?')
# AGLDT Greek postag position 1 -> coarse Morpheus POS (used only as a tie-break
# among candidates; see tmp/grc/eval_grc.py for the empirical mapping).
AGLDT_POS = {"n": "N", "a": "A", "v": "V", "d": "D", "g": "X", "l": "RA",
             "p": "RP", "r": "P", "c": "C", "i": "I"}

# PapyGreek ALDT pos1 -> coarse Morpheus POS, same convention (used only as a
# gold tie-break among candidates; the evaluation classes live in
# scripts/benchmark.py PG_CLASSES). Numerals (m) and unannotated (u) are skipped.
PG_POS = {"n": "N", "a": "A", "v": "V", "d": "D", "g": "X", "l": "RA",
          "p": "RP", "r": "P", "c": "C", "i": "I", "x": "X"}

# PapyGreek editorial markers (same inventory as scripts/benchmark.py): strip
# |num:N| / |g:...| annotation spans, then supplement/uncertainty brackets and
# line-break marks. The apostrophes ʼ ’ are real elision marks and are kept.
PG_PIPE_ANN = re.compile(r"\|[a-z]+:[^|]*\|")
PG_MARKERS = re.compile(
    r"[∼∽∤⋰⋱⸢⸣❨❩<>[\]{}()〚〛⊢⊣⸌⸍⎴⎵⦑⦒⸜⸝⧼?…-]+|[̣̅]")
PG_GREEK = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
PG_WORD = re.compile(r"<word\s+([^>]+)/>")


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


def read_papygreek(directory: str) -> List[Tuple[str, str, str, str]]:
    """Return (ref, token, lemma, pos) rows from the PapyGreek treebanks.

    ALDT XML with dual layers: the ORIGINAL spelling (editorial markers stripped)
    is what Morpheus sees, the REGULARIZED lemma is the gold. One document per
    ``ref`` so the held-out split can be document-level. Punctuation (``u``) and
    numerals (``m``; Morpheus has no numeral POS) are skipped, as in the AGLDT
    reader. PapyGreek Treebanks v1.01, CC-BY-SA 4.0.
    """
    rows: List[Tuple[str, str, str, str]] = []
    for path in sorted(glob.glob(os.path.join(directory, "**", "*.xml"), recursive=True)):
        try:
            content = html.unescape(open(path, encoding="utf-8", errors="replace").read())
        except OSError:
            continue
        doc = os.path.basename(path)
        for match in PG_WORD.finditer(content):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))
            if attrs.get("lang", "grc") != "grc":
                continue
            form = PG_MARKERS.sub("", PG_PIPE_ANN.sub("", attrs.get("form_orig", ""))).strip()
            lemma = PG_PIPE_ANN.sub("", attrs.get("lemma_reg", ""))
            postag = attrs.get("postag_reg", "")
            pos1 = postag[0] if postag else ""
            if not form or not lemma or pos1 in ("", "u", "m"):
                continue
            if not PG_GREEK.search(form):
                continue  # illegible-text placeholders ($ etc.)
            rows.append((doc, form, lemma, PG_POS.get(pos1, "")))
    return rows


def split_documents(
    rows: List[Tuple[str, str, str, str]], holdout_fraction: float
) -> Tuple[List[Tuple[str, str, str, str]], List[Tuple[str, str, str, str]]]:
    """Deterministically hold out whole documents (every Nth by sorted name)."""
    if holdout_fraction <= 0:
        return rows, []
    docs = sorted({ref for ref, _, _, _ in rows})
    stride = max(2, round(1.0 / holdout_fraction))
    held = {doc for index, doc in enumerate(docs) if index % stride == 0}
    train = [row for row in rows if row[0] not in held]
    holdout = [row for row in rows if row[0] in held]
    return train, holdout


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
    """Index of the candidate matching the gold reading (None if absent).

    Canonical lemmas first: the variant list also contains the *form* elements
    Morpheus matched (``form,lemma``), and a Doric/alternate stem can make one
    entry's form element coincide with a different word's gold lemma (πηρός's
    Doric παρά vs the preposition). Variants remain a fallback so references
    that use a listed variant lemma still match.
    """
    target = normalize_lemma(gold_lemma)
    matches = [
        i for i, a in enumerate(analyses)
        if normalize_lemma(a.lemma) == target
    ] or [
        i for i, a in enumerate(analyses)
        if any(normalize_lemma(v) == target for v in a.variants())
    ]
    if not matches:
        return None
    for i in matches:
        if analyses[i].pos == gold_pos:
            return i
    return matches[0]


def train_mlp(examples, holdout_examples, feature_names, args, source):
    """Optional MLP head-to-head on the same candidate examples (CPU torch).

    Listwise softmax cross-entropy over each token's candidates; the sparse
    candidate features are gathered from the first layer's weight columns, so
    the input dimension is the feature vocabulary. Tokens with a single
    candidate contribute no gradient but count in evaluation. Returns the model
    payload dict (with its own held-out numbers).
    """
    import time

    import torch

    torch.manual_seed(args.seed)
    hidden = args.mlp_hidden
    index = {name: i + 1 for i, name in enumerate(feature_names)}
    W1 = torch.zeros(hidden, len(feature_names) + 1, requires_grad=True)
    b1 = torch.zeros(hidden, requires_grad=True)
    w2 = torch.zeros(hidden, requires_grad=True)
    b2 = torch.zeros(1, requires_grad=True)
    with torch.no_grad():
        W1[:, 1:].normal_(0.0, 0.05)
        w2.normal_(0.0, 0.05)
    optimizer = torch.optim.Adam([W1, b1, w2, b2], lr=args.mlp_lr)

    def encode(cand_feats):
        return [[index.get(key, 0) for key in keys] for keys in cand_feats]

    train = [(encode(cf), gi) for cf, gi, _ in examples if len(cf) > 1]
    hold = [(encode(cf), gi) for cf, gi, _ in holdout_examples] if holdout_examples else []

    def buckets(encoded):
        out = {}
        for i, (ids, _gi) in enumerate(encoded):
            out.setdefault(len(ids), []).append(i)
        return out

    def forward(batch):
        n, k = len(batch), len(batch[0][0])
        width = max(len(feat_ids) for ids, _ in batch for feat_ids in ids)
        ids_t = torch.zeros(n, k, width, dtype=torch.long)
        mask = torch.zeros(n, k, width)
        tgt = torch.zeros(n, dtype=torch.long)
        for r, (ids, gi) in enumerate(batch):
            for j, feat_ids in enumerate(ids):
                ids_t[r, j, :len(feat_ids)] = torch.tensor(feat_ids, dtype=torch.long)
                mask[r, j, :len(feat_ids)] = 1.0
            tgt[r] = gi
        cols = W1[:, ids_t.reshape(-1)].t().reshape(n, k, width, hidden)
        h = (cols * mask.unsqueeze(-1)).sum(dim=2) + b1
        h = torch.relu(h)
        return (h * w2).sum(dim=2) + b2, tgt

    def evaluate(encoded, groups):
        hits = len(groups.get(1, []))  # single-candidate tokens are top-1 by default
        with torch.no_grad():
            for k, idxs in groups.items():
                if k < 2:
                    continue
                for start in range(0, len(idxs), 512):
                    chunk = [encoded[i] for i in idxs[start:start + 512]]
                    scores, tgt = forward(chunk)
                    hits += int((scores.argmax(dim=1) == tgt).sum())
        return hits / max(len(encoded), 1)

    best_acc = None
    best_state = None
    for epoch in range(args.mlp_epochs):
        started = time.time()
        groups = buckets(train)
        for idxs in groups.values():
            random.shuffle(idxs)
        for k, idxs in groups.items():
            if k < 2:
                continue
            for start in range(0, len(idxs), 128):
                chunk = [train[i] for i in idxs[start:start + 128]]
                scores, tgt = forward(chunk)
                loss = torch.nn.functional.cross_entropy(scores, tgt)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        line = f"mlp epoch {epoch + 1} ({time.time() - started:.0f}s):"
        if hold:
            acc = evaluate(hold, buckets(hold))
            line += f" held-out top-1 {100 * acc:.2f}%"
            if best_acc is None or acc > best_acc:
                best_acc = acc
                best_state = [t.detach().clone() for t in (W1, b1, w2, b2)]
        print(line, flush=True)
    if best_state is None:
        best_state = [t.detach().clone() for t in (W1, b1, w2, b2)]
    W1b, b1b, w2b, b2b = best_state

    payload = {
        "source": source,
        "type": "mlp",
        "notes": "CPU-trained MLP re-ranker over the perceptron's candidate "
                 "features; see scripts/build_learned_model.py --mlp.",
        "hidden": hidden,
        "features": len(feature_names),
        "feature_index": feature_names,
        "w1": [[round(v, 6) for v in row] for row in W1b.tolist()],
        "b1": [round(v, 6) for v in b1b.tolist()],
        "w2": [round(v, 6) for v in w2b.tolist()],
        "b2": round(float(b2b.item()), 6),
    }
    if hold:
        payload["papygreek_holdout"] = {"tokens": len(hold),
                                        "learned_top1": round(100 * best_acc, 2)}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    parser.add_argument("--agldt-dir", default=os.environ.get("AGLDT_DIR", ""),
                        help="AGLDT v2.1 Greek *.tb.xml directory to pool (CC BY-SA 3.0 US)")
    parser.add_argument("--agldt-limit", type=int, default=0,
                        help="uniformly subsample AGLDT to this many tokens (0 = all) — "
                             "balances the pool against the Koine corpora")
    parser.add_argument("--papygreek-dir", default=os.environ.get("PAPYGREEK_DIR", ""),
                        help="PapyGreek treebanks directory (*.xml, CC-BY-SA 4.0) to pool")
    parser.add_argument("--papygreek-holdout", type=float, default=0.2,
                        help="fraction of PapyGreek DOCUMENTS held out for honest "
                             "evaluation (0 = train on everything)")
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
    parser.add_argument("--mlp", action="store_true",
                        help="also train a CPU MLP on the same examples (requires torch) "
                             "and report a held-out head-to-head")
    parser.add_argument("--mlp-hidden", type=int, default=64)
    parser.add_argument("--mlp-epochs", type=int, default=8)
    parser.add_argument("--mlp-lr", type=float, default=1e-3)
    parser.add_argument("--mlp-out", default="",
                        help="write the MLP payload here (default: <out>.mlp.json)")
    args = parser.parse_args()

    paths = list(args.paths)
    if args.morphgnt_dir:
        paths += sorted(glob.glob(os.path.join(args.morphgnt_dir, "*.txt")))
    if not paths and not args.agldt_dir and not args.papygreek_dir:
        parser.error("give file paths, --morphgnt-dir, --agldt-dir, or --papygreek-dir")

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
    holdout_rows: List[Tuple[str, str, str, str]] = []
    if args.agldt_dir:
        agldt_rows = read_agldt(args.agldt_dir)
        if args.agldt_limit and len(agldt_rows) > args.agldt_limit:
            step = len(agldt_rows) / args.agldt_limit
            agldt_rows = [agldt_rows[int(i * step)] for i in range(args.agldt_limit)]
        print(f"  AGLDT: {len(agldt_rows)} tokens from {args.agldt_dir}")
        rows += agldt_rows
        source += " + Apostolic Fathers + AGLDT v2.1 Greek (CC BY-SA 3.0 US)"
    if args.papygreek_dir:
        pg_rows = read_papygreek(args.papygreek_dir)
        pg_train, pg_holdout = split_documents(pg_rows, args.papygreek_holdout)
        docs_held = len({ref for ref, _, _, _ in pg_holdout})
        print(f"  PapyGreek: {len(pg_rows)} tokens from {args.papygreek_dir} "
              f"({len(pg_rows) - len(pg_train)} held out from {docs_held} documents)")
        rows += pg_train
        holdout_rows = assign_chunks(pg_holdout)
        source += " + PapyGreek Treebanks v1.01 (CC-BY-SA 4.0)"
    rows = assign_chunks(rows)
    if args.limit:
        rows = rows[: args.limit]
    print(f"read {len(rows)} gold tokens")

    extractor = LearnedRanker({"weights": {}, "lemma_context": args.lemma_context},
                              frequencies=frequencies, joint=joint or {})
    runner = MorpheusRunner()

    # Build examples: (candidate-feature tuples, gold index, frequency-top-1?).
    feature_counts: Counter = Counter()

    def build_examples(
        chunk_rows: List[Tuple[str, str, str, str]], track_features: bool
    ) -> List[Tuple[List[Tuple[str, ...]], int, bool]]:
        """Candidate features + gold index for each analyzable token.

        Mirrors the shipped candidate distribution: the recovery pre-pass runs
        for unanalyzed tokens (spelling variants + names), so ranking recovered
        proposals is part of the task (Round 15 lesson: candidate generation
        defines it). The third tuple element records whether the gold reading is
        first in frequency order.
        """
        by_chunk: Dict[str, List[Tuple[str, str, str]]] = {}
        for cid, token, lemma, pos in chunk_rows:
            by_chunk.setdefault(cid, []).append((token, lemma, pos))
        out: List[Tuple[List[Tuple[str, ...]], int, bool]] = []
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
            misses = [
                (i, betas[i]) for i in range(len(chunk))
                if betas[i] and not analyses_list[i]
            ]
            if misses:
                recovered_lists: List[List[Analysis]] = [[] for _ in misses]
                recover(
                    [chunk[i][0] for i, _ in misses],
                    recovered_lists,
                    runner,
                    frequencies,
                )
                for (i, _), found in zip(misses, recovered_lists):
                    if found:
                        analyses_list[i] = found
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
                    if track_features:
                        feature_counts.update(keys)
                    cand_feats.append(keys)
                out.append((cand_feats, gi, ordered[0] == gi))
            if track_features and len(out) and len(out) % 20000 < len(chunk) + 1:
                print(f"  prepared {len(out)} tokens", flush=True)
        return out

    examples = build_examples(rows, track_features=True)
    analyzed = len(examples)
    print(f"{analyzed} analyzable tokens, {len(feature_counts)} distinct features")
    if not examples:
        parser.error("no training examples (gold lemmas never matched Morpheus?)")

    holdout_examples: List[Tuple[List[Tuple[str, ...]], int, bool]] = []
    if holdout_rows:
        holdout_examples = build_examples(holdout_rows, track_features=False)
        print(f"{len(holdout_examples)} analyzable held-out PapyGreek tokens "
              f"(of {len(holdout_rows)})")

    random.seed(args.seed)
    model = AveragedPerceptron()
    for epoch in range(args.epochs):
        order = list(range(len(examples)))
        random.shuffle(order)
        mistakes = 0
        for idx in order:
            cand_feats, gi, _ = examples[idx]
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

    holdout_eval = None
    if holdout_examples:
        freq_hits = sum(1 for _, _, freq_top in holdout_examples if freq_top)
        learned_hits = 0
        for cand_feats, gi, _ in holdout_examples:
            best_j, best_score = 0, None
            for j, keys in enumerate(cand_feats):
                score = sum(kept.get(k, 0.0) for k in keys)
                if best_score is None or score > best_score:
                    best_score, best_j = score, j
            learned_hits += int(best_j == gi)
        n_hold = len(holdout_examples)
        holdout_eval = {
            "tokens": n_hold,
            "frequency_top1": round(100 * freq_hits / n_hold, 2),
            "learned_top1": round(100 * learned_hits / n_hold, 2),
        }
        print(f"PapyGreek held-out (n={n_hold} analyzable of {len(holdout_rows)}): "
              f"frequency top-1 {holdout_eval['frequency_top1']}%, "
              f"learned top-1 {holdout_eval['learned_top1']}%")

    if args.mlp:
        try:
            import torch  # noqa: F401
        except ImportError:
            print("--mlp requires torch in the training environment "
                  "(e.g. .venv/bin/pip install torch); skipping MLP training.",
                  flush=True)
        else:
            feature_names = sorted(
                f for f, count in feature_counts.items() if count >= args.min_count
            )
            print(f"training MLP ({args.mlp_hidden} hidden, {args.mlp_epochs} epochs, "
                  f"{len(feature_names)} features)", flush=True)
            mlp_payload = train_mlp(examples, holdout_examples, feature_names, args, source)
            if holdout_eval:
                print(f"head-to-head held-out: perceptron {holdout_eval['learned_top1']}% "
                      f"vs MLP {mlp_payload.get('papygreek_holdout', {}).get('learned_top1')}%")
            mlp_out = args.mlp_out or (
                args.out[:-5] + ".mlp.json" if args.out.endswith(".json") else args.out + ".mlp.json"
            )
            os.makedirs(os.path.dirname(mlp_out) or ".", exist_ok=True)
            with open(mlp_out, "w", encoding="utf-8") as handle:
                json.dump(mlp_payload, handle, ensure_ascii=False)
            print(f"Wrote MLP model to {mlp_out}")

    payload = {
        "source": source,
        "features": len(kept),
        "lemma_context": args.lemma_context,
        "notes": "Averaged-perceptron learned re-ranker; see scripts/build_learned_model.py.",
        "weights": kept,
    }
    if holdout_eval:
        payload["papygreek_holdout"] = holdout_eval
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    print(f"Wrote {len(kept)} feature weights to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
