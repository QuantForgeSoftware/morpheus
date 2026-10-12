#!/usr/bin/env python3
"""Build the papyrus letter-numeral table (Round 9 item 3).

Papyri write numbers as bare Greek letters (β = 2, κθ = 90, λϛ = 36 …); the
stemlib has no entries for them. This script reads the PapyGreek treebank's
numeral gold (postag `m`, CC BY-SA), keeps only the tokens Morpheus currently
MISSES (the ones the opt-in feature addresses), and records each form's
majority-vote gold lemma, keyed by beta code — the same key the analyzer sees.

Gold-lemma hygiene: editorial pipe annotations (`|num:N|`) are stripped from
lemmas as well as forms, and only pure Greek-letter lemmas count as reliable
gold (a handful of tokens carry decimal values like `1300` instead). Forms
whose reliable count is below --min-count are dropped.

The table is applied behind an opt-in flag (`Morpheus(numerals=True)` / CLI
--numerals); default Morpheus behavior is unchanged, and analyzed tokens are
never overridden (only unanalyzed ones get a synthetic analysis).

Usage:
  scripts/build_papyrus_numerals.py [--pg-dir DIR] [--min-count N] [--out PATH]
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
import unicodedata

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import to_beta  # noqa: E402
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402

# PapyGreek editorial markers (same inventory as the other PG readers).
PIPE_ANN = re.compile(r"\|[a-z]+:[^|]*\|")
MARKERS = re.compile(
    r"[∼∽∤⋰⋱⸢⸣❨❩<>[\]{}()〚〛⊢⊣⸌⸍⎴⎵⦑⦒⸜⸝⧼?…-]+|̣")
GREEK_LETTERS = re.compile(r"^[\u0370-\u03ff\u1f00-\u1fff]+$")


def strip_markers(text: str) -> str:
    return MARKERS.sub("", PIPE_ANN.sub("", text)).strip()


def read_numeral_gold(directory):
    """Yield (form_clean, lemma) for every Greek numeral token in the treebank."""
    for path in sorted(glob.glob(os.path.join(directory, "**", "*.xml"), recursive=True)):
        with open(path, encoding="utf-8") as fh:
            content = html.unescape(fh.read())
        for m in re.finditer(r"<word\s+([^>]+)/>", content):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            if a.get("lang", "grc") != "grc":
                continue
            postag = a.get("postag_reg", "")
            if not postag or postag[0] != "m":
                continue
            clean = strip_markers(a.get("form_orig", ""))
            lemma = unicodedata.normalize(
                "NFC", strip_markers(a.get("lemma_reg", "")))
            if not clean or not GREEK_LETTERS.match(lemma):
                continue  # unanalyzable forms / decimal-annotated lemmas
            yield clean, lemma


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--pg-dir",
        default=os.path.join(REPO, "tmp", "papygreek",
                             "ezhenrik-papygreek-treebanks-b87127c"),
    )
    ap.add_argument("--min-count", type=int, default=2)
    ap.add_argument(
        "--out",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data",
                             "papyrus_numerals.json"),
    )
    args = ap.parse_args()

    tokens = list(read_numeral_gold(args.pg_dir))
    print(f"numeral gold tokens (reliable lemmas): {len(tokens)}")

    # Keep only the forms Morpheus misses under the PG evaluation config.
    runner = MorpheusRunner(language="greek")
    tally: dict[str, collections.Counter] = {}
    dropped_analyzed = 0
    CHUNK = 5000
    for i in range(0, len(tokens), CHUNK):
        chunk = tokens[i:i + CHUNK]
        betas = [to_beta(form).lower() for form, _ in chunk]
        results = runner.analyze_beta(betas, ignore_accents=True)
        for (form, lemma), beta, analyses in zip(chunk, betas, results):
            if analyses:
                dropped_analyzed += 1
                continue
            tally.setdefault(beta, collections.Counter())[lemma] += 1

    missed = sum(sum(c.values()) for c in tally.values())
    print(f"missed by Morpheus (table candidates): {missed} "
          f"(already analyzed: {dropped_analyzed})")

    forms = {}
    dropped_tokens = 0
    for beta, counts in sorted(tally.items()):
        lemma, count = counts.most_common(1)[0]
        if count < args.min_count:
            dropped_tokens += sum(counts.values())
            continue
        forms[beta] = {"lemma": lemma, "count": count}

    out = {
        "source": ("Greek letter numerals from the PapyGreek Treebanks v1.01 "
                   "(CC BY-SA 4.0); Round 9 item 3"),
        "tokens_trained": missed,
        "min_count": args.min_count,
        "forms": forms,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    print(f"table -> {args.out} ({len(forms)} forms; "
          f"{dropped_tokens} tokens below min_count={args.min_count})")
    for beta, entry in list(forms.items())[:12]:
        print(f"   {beta!r:8s} -> {entry['lemma']} (×{entry['count']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
