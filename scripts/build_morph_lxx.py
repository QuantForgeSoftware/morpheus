#!/usr/bin/env python3
"""
Produce a full Morpheus morphological analysis of the LXX reference corpus.

Reads every *.mlxx file in the corpus, runs Morpheus over each distinct form
(two-pass accent handling + frequency ranking), disambiguates with the Viterbi
POS-bigram tagger trained on this corpus (pos_bigram_lxx.json), and writes
re-annotated files to --out-dir in the same column layout:

    form  type  parse  lemma  [prefix]

The type column carries Morpheus's coarse POS; the parse column its full 8-char
parsing code (person/tense/voice/mood/case/number/gender/degree) — a superset of
the corpus's 5-char codes. Lemma convention is compound lemmas in canonical beta,
uppercased to match the corpus style (see todo.md, Round 3). Tokens Morpheus
cannot analyze fall back to the corpus's own annotation; fallbacks are counted
in the summary report.

Usage:
  scripts/build_morph_lxx.py --corpus-dir /path/to/lxx-corpus \
      [--out-dir tmp/lxx/morph-lxx] [--model .../pos_bigram_lxx.json] \
      [--frequencies .../lemma_frequencies_lxx.json]
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.api import Morpheus  # noqa: E402
from morpheus_toolkit.beta import from_beta, to_beta  # noqa: E402
from morpheus_toolkit.morphgnt import parsing_code  # noqa: E402
from morpheus_toolkit.ranking import Ranker  # noqa: E402
from morpheus_toolkit.tagger import PosTagger  # noqa: E402

PARSE_RE = re.compile(r"[A-Z0-9]+$")
LETTER_RE = re.compile(r"[A-Za-z]")


def canon(form_beta: str) -> str:
    """Corpus beta code -> canonical lowercase beta via a Unicode round-trip."""
    return to_beta(from_beta(form_beta)) or form_beta.lower()


def is_token_line(line: str) -> bool:
    fields = line.split()
    return len(fields) >= 3 and bool(LETTER_RE.search(fields[0]))


def parse_fields(line: str):
    """form, type, parse, lemma, prefix (the corpus's column layout)."""
    fields = line.split()
    form_b, typ = fields[0], fields[1]
    if len(fields) >= 4 and PARSE_RE.fullmatch(fields[2]):
        parse_c, lemma_b = fields[2], fields[3]
        prefix = fields[4] if len(fields) > 4 else ""
    else:
        parse_c, lemma_b = "", fields[2]
        prefix = fields[3] if len(fields) > 3 else ""
    return form_b, typ, parse_c, lemma_b, prefix


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default=os.environ.get("LXX_CORPUS_DIR", ""))
    parser.add_argument(
        "--out-dir",
        default=os.path.join(REPO, "tmp", "lxx", "morph-lxx"),
    )
    parser.add_argument(
        "--model",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "pos_bigram_lxx.json"),
    )
    parser.add_argument(
        "--frequencies",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "lemma_frequencies_lxx.json"),
    )
    args = parser.parse_args()
    if not args.corpus_dir or not os.path.isdir(args.corpus_dir):
        parser.error("give --corpus-dir (or set LXX_CORPUS_DIR) pointing at the LXX reference corpus")

    files = sorted(glob.glob(os.path.join(args.corpus_dir, "*.mlxx")))
    if not files:
        parser.error(f"no *.mlxx files under {args.corpus_dir}")

    # Pass 1: read every file; collect distinct canonical forms and raw lines.
    per_file_lines = {}
    distinct = set()
    total_tokens = 0
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = [line.rstrip("\n") for line in handle]
        per_file_lines[path] = lines
        for line in lines:
            if is_token_line(line):
                total_tokens += 1
                distinct.add(canon(parse_fields(line)[0]))

    print(f"files={len(files)} tokens={total_tokens} distinct_forms={len(distinct)}", flush=True)

    # Pass 2: analyze every distinct form (two-pass accents + ranked candidates).
    freq_data = load_json(args.frequencies)
    morpheus = Morpheus(ignore_accents=True)
    morpheus.ranker = Ranker(
        freq_data.get("frequencies", freq_data),
        joint_frequencies=freq_data.get("by_pos"),
    )
    candidates: dict[str, list] = {}
    forms = sorted(distinct)
    BATCH = 2000
    for i in range(0, len(forms), BATCH):
        chunk = forms[i : i + BATCH]
        for result in morpheus.analyze_beta(chunk):
            if result.analyses:
                candidates[result.beta] = list(result.analyses)
        print(f"  analyzed {min(i + BATCH, len(forms))}/{len(forms)}", flush=True)

    tagger = PosTagger(load_json(args.model))

    # Pass 3: per file — Viterbi-tag each contiguous token run, emit output.
    os.makedirs(args.out_dir, exist_ok=True)
    total_analyzed = 0
    total_fallback = 0
    fallback_by_type: collections.Counter = collections.Counter()
    book_stats = {}

    for path in files:
        book = os.path.basename(path)
        out_lines = []
        fallback_lines = []  # 1-based output line numbers using the corpus annotation
        run_items = []  # (raw_line, candidates)

        def emit_run():
            nonlocal total_analyzed, total_fallback
            if not run_items:
                return
            chosen = tagger.tag([cands for _, cands in run_items])
            for (raw, _cands), analysis in zip(run_items, chosen):
                form_b, typ, parse_c, lemma_b, prefix = parse_fields(raw)
                if analysis is None or analysis.proposed:
                    out_lines.append(raw)  # fallback: corpus's own annotation
                    fallback_lines.append(len(out_lines))
                    total_fallback += 1
                    fallback_by_type[typ] += 1
                else:
                    fields = [form_b, analysis.pos, parsing_code(analysis), analysis.lemma_beta.upper()]
                    if prefix:
                        fields.append(prefix)
                    out_lines.append("  ".join(fields))
                    total_analyzed += 1
            run_items.clear()

        for line in per_file_lines[path]:
            if not line.strip() or not is_token_line(line):
                emit_run()
                out_lines.append(line)
                continue
            form_b = parse_fields(line)[0]
            run_items.append((line, candidates.get(canon(form_b), [])))
        emit_run()

        with open(os.path.join(args.out_dir, book), "w", encoding="utf-8") as handle:
            handle.write("\n".join(out_lines) + "\n")
        if fallback_lines:
            with open(os.path.join(args.out_dir, book + ".fb"), "w", encoding="utf-8") as handle:
                handle.write("\n".join(str(n) for n in fallback_lines) + "\n")
        book_tokens = sum(1 for line in per_file_lines[path] if is_token_line(line))
        book_stats[book] = book_tokens

    # Summary report.
    summary = [
        "Morpheus LXX annotation — summary",
        "corpus: LXX reference corpus (*.mlxx)",
        f"files={len(files)} tokens={total_tokens} distinct_forms={len(distinct)}",
        f"analyzed_by_morpheus={total_analyzed} ({100 * total_analyzed / max(total_tokens, 1):.2f}%)",
        f"fallback_to_corpus={total_fallback} ({100 * total_fallback / max(total_tokens, 1):.2f}%)",
        "",
        "fallbacks by corpus type:",
    ]
    for typ, count in fallback_by_type.most_common(15):
        summary.append(f"  {typ:6s} {count}")
    summary += ["", "tokens per book (all tokens; see output files for annotations):"]
    for book, count in sorted(book_stats.items()):
        summary.append(f"  {book:24s} {count}")

    out_summary = os.path.join(args.out_dir, "summary.txt")
    with open(out_summary, "w", encoding="utf-8") as handle:
        handle.write("\n".join(summary) + "\n")
    print(f"\nwrote {len(files)} files to {args.out_dir}; summary at {out_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
