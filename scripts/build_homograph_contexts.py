#!/usr/bin/env python3
"""Build a context-conditional lemma table for homograph disambiguation.

Round 9 item 2: the stable residual errors across SBLGNT and PROIEL are a few
function-word homographs (ὡς/ὅς, εἰ/εἰμί, τε/σύ, ὃ/ὁ, ...) that global lemma
frequency cannot resolve — their correct reading depends on the neighbours.

Training uses commit-safe gold only (SBLGNT + Apostolic Fathers + PapyGreek,
all CC BY-SA). For every token whose form has >=2 candidate lemmas in Morpheus
and whose gold lemma is among them, we record which lemma the gold chose,
conditioned on the neighbours' frequency-ranked top-1 POS — the same context
the opt-in re-ranker sees at inference time (no train/test mismatch; verse and
sentence boundaries reset the context).

The table is applied behind an opt-in flag (`use_homograph_context` / CLI
--homographs); default Morpheus behavior is unchanged.

Usage:
  scripts/build_homograph_contexts.py \
      --morphgnt-dir /path/to/morphgnt [--af-dir ...] [--pg-dir ...] \
      [--min-form N] [--min-ctx N] [--out PATH]
"""
from __future__ import annotations

import argparse
import collections
import glob
import html
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import normalize_lemma, to_beta  # noqa: E402
from morpheus_toolkit.ranking import Ranker, load_default_frequencies  # noqa: E402
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402

# PapyGreek editorial markers (same inventory as tmp/papygreek/eval_pg.py).
PIPE_ANN = re.compile(r"\|[a-z]+:[^|]*\|")
MARKERS = re.compile(
    r"[∼∽∤⋰⋱⸢⸣❨❩<>[\]{}()〚〛⊢⊣⸌⸍⎴⎵⦑⦒⸜⸝⧼?…-]+|̣")


def strip_markers(form: str) -> str:
    return MARKERS.sub("", PIPE_ANN.sub("", form)).strip()


def read_morphgnt_style(directory, need_lang):
    """Yield (ref, token, lemma) from MorphGNT/AF columnar files.

    Both formats are header-free; the AF files carry two extra columns
    (language, source) which double as a filter for Greek rows.
    """
    for path in sorted(glob.glob(os.path.join(directory, "*.txt"))):
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                f = line.split()
                if len(f) < 7:
                    continue
                if need_lang and (len(f) < 9 or f[7] != "grc"):
                    continue
                yield f[0], f[4], f[6]


def read_papygreek(directory):
    """Yield (ref, token, lemma) from PapyGreek ALDT XML (per-sentence refs)."""
    for path in sorted(glob.glob(os.path.join(directory, "**", "*.xml"), recursive=True)):
        doc = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            content = html.unescape(fh.read())
        sentence = 0
        for m in re.finditer(r"<sentence\s+[^>]*>|<word\s+([^>]+)/>", content):
            if m.group(1) is None:  # a <sentence ...> tag (context boundary)
                sentence += 1
                continue
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            if a.get("lang", "grc") != "grc":
                continue
            clean = strip_markers(a.get("form_orig", ""))
            lemma = a.get("lemma_reg", "")
            postag = a.get("postag_reg", "")
            if not clean or not lemma or (postag and postag[0] == "u"):
                continue
            if not re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", clean):
                continue
            yield f"{doc}#{sentence}", clean, lemma


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--morphgnt-dir", default=os.environ.get("MORPHGNT_DIR", ""))
    ap.add_argument("--af-dir", default=os.path.join(REPO, "tmp", "af", "morph-grc"))
    ap.add_argument(
        "--pg-dir",
        default=os.path.join(REPO, "tmp", "papygreek",
                             "ezhenrik-papygreek-treebanks-b87127c"),
    )
    ap.add_argument("--min-form", type=int, default=20)
    ap.add_argument("--min-ctx", type=int, default=5)
    ap.add_argument(
        "--out",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data",
                             "homograph_contexts.json"),
    )
    args = ap.parse_args()

    # ---- collect the token stream (gold lemma per token) -------------------
    tokens = []  # (ref, form_unicode, lemma_gold); ref change resets context
    sources = []
    if args.morphgnt_dir and os.path.isdir(args.morphgnt_dir):
        tokens.extend(read_morphgnt_style(args.morphgnt_dir, need_lang=False))
        sources.append("SBLGNT")
    if os.path.isdir(args.af_dir) and glob.glob(os.path.join(args.af_dir, "*.txt")):
        tokens.extend(read_morphgnt_style(args.af_dir, need_lang=True))
        sources.append("Apostolic Fathers")
    if os.path.isdir(args.pg_dir):
        tokens.extend(read_papygreek(args.pg_dir))
        sources.append("PapyGreek")
    if not tokens:
        ap.error("no training gold found (pass --morphgnt-dir / --af-dir / --pg-dir)")
    print(f"training tokens={len(tokens)}  from: {', '.join(sources)}", flush=True)

    # ---- Morpheus candidates + frequency ranking ---------------------------
    runner = MorpheusRunner()
    ranker = Ranker(load_default_frequencies())
    distinct = sorted({to_beta(t[1]) for t in tokens if to_beta(t[1])})
    print(f"distinct forms={len(distinct)}", flush=True)
    ranked = {}
    BATCH = 2000
    for i in range(0, len(distinct), BATCH):
        chunk = distinct[i:i + BATCH]
        res = runner.analyze_beta(chunk, ignore_accents=True)
        for beta, analyses in zip(chunk, res):
            if analyses:
                ranked[beta] = ranker.rank(list(analyses))
        print(f"  analyzed {min(i + BATCH, len(distinct))}/{len(distinct)}", flush=True)

    def top_pos(beta):
        cands = ranked.get(beta) or []
        return cands[0].pos if cands else None

    # ---- aggregate P(gold lemma | form, prev POS, next POS) ----------------
    betas = [to_beta(tok) if to_beta(tok) else "" for _ref, tok, _lem in tokens]
    refs = [ref for ref, _tok, _lem in tokens]
    marginal = collections.defaultdict(collections.Counter)
    contexts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    totals = collections.Counter()
    ambiguous = 0
    n = len(tokens)
    for i, (ref, _tok, lem) in enumerate(tokens):
        beta = betas[i]
        cands = ranked.get(beta) or []
        if not cands:
            continue
        gold = normalize_lemma(lem)
        cand_lemmas = {normalize_lemma(v) for a in cands for v in a.variants()}
        if len(cand_lemmas) < 2 or gold not in cand_lemmas:
            continue
        ambiguous += 1
        prev_beta = betas[i - 1] if i > 0 and refs[i] == refs[i - 1] else ""
        next_beta = betas[i + 1] if i + 1 < n and refs[i] == refs[i + 1] else ""
        totals[beta] += 1
        marginal[beta][gold] += 1
        prev_pos, next_pos = top_pos(prev_beta), top_pos(next_beta)
        if prev_pos and next_pos:
            contexts[beta][(prev_pos, next_pos)][gold] += 1

    print(f"ambiguous tokens (>=2 candidate lemmas, gold among them): {ambiguous}", flush=True)

    # ---- write the table ----------------------------------------------------
    forms = {}
    for beta, total in totals.most_common():
        if total < args.min_form:
            continue
        ctxs = {}
        for (prev_pos, next_pos), counter in contexts[beta].items():
            if sum(counter.values()) >= args.min_ctx:
                ctxs[f"{prev_pos} {next_pos}"] = dict(counter.most_common())
        forms[beta] = {
            "total": total,
            "marginal": dict(marginal[beta].most_common()),
            "contexts": ctxs,
        }
    payload = {
        "source": (f"Context-conditional lemma counts trained on {' + '.join(sources)} "
                   f"(all CC BY-SA); Round 9 item 2"),
        "tokens_trained": len(tokens),
        "ambiguous_tokens": ambiguous,
        "min_form": args.min_form,
        "min_ctx": args.min_ctx,
        "forms": forms,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=0)
    print(f"Wrote {len(forms)} ambiguous forms to {args.out}")
    for beta, entry in list(forms.items())[:12]:
        top = ", ".join(f"{g}:{c}" for g, c in list(entry["marginal"].items())[:4])
        print(f"  {beta:10s} total={entry['total']:<6d} ctxs={len(entry['contexts']):<3d} {top}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
