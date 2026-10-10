#!/usr/bin/env python3
"""
Produce a full Morpheus morphological analysis of the Apostolic Fathers corpus.

Reads every *.txt file in --corpus-dir (the 9-column reference layout), runs
Morpheus over each distinct Greek word form in accent-insensitive mode with
AF frequency ranking, disambiguates with the Viterbi POS-bigram tagger trained
on this corpus, and writes re-annotated files to --out-dir in the same column
layout:

    reference  pos  parse8  text  word  normalized  lemma  language  source

pos/parse8/lemma come from Morpheus (the source column becomes "morpheus"); all
other columns are copied through. Only Greek lines (language field == grc) are
annotated; every other line passes through unchanged. Tokens Morpheus cannot
analyze fall back to the corpus's own annotation (its original fields, including
source); fallbacks are counted in the summary report and listed in *.fb files.

Convention mode:
  --conventions   rewrite the lemma column to the reference's dictionary-form
                  convention where the two differ systematically (reduplication,
                  augment, aorist-of-base-verb lemmas, accent placement). The
                  mapping is derived at run time from the corpus's own
                  MorphGNT-derived gold lines: only pairs that are consistent
                  (one target per source lemma) and frequent (>=10 tokens) are
                  applied. No shared stemlib/lemma data changes; NT/LXX output
                  is untouched.

By default each token gets its top-ranked candidate (plain lemma frequency),
which maximizes lemma accuracy on this corpus. Options:

  --tagger        disambiguate with the Viterbi POS-bigram tagger over contiguous
                  token runs — trades ~1pp of lemma for +1-2pp of POS (the
                  reference tags adjectives N where Morpheus says A; joint-style
                  demotion helps there).
  --joint         rank by joint (lemma, POS) frequency instead of plain lemma
                  frequency — the same trade in ranking terms.

Usage:
  scripts/build_morph_af.py --corpus-dir /path/to/af-corpus/data/morph \
      [--out-dir tmp/af/morph-af] [--frequencies .../lemma_frequencies_af.json]
      [--model .../pos_bigram_af.json] [--conventions] [--tagger] [--joint]
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys
import unicodedata

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.api import Morpheus  # noqa: E402
from morpheus_toolkit.beta import to_beta  # noqa: E402
from morpheus_toolkit.morphgnt import parsing_code, pos_code  # noqa: E402
from morpheus_toolkit.ranking import Ranker  # noqa: E402
from morpheus_toolkit.tagger import PosTagger  # noqa: E402

# A convention pair is applied only when at least this many gold tokens agree.
MIN_CONVENTION_TOKENS = 10


def deacc(s: str) -> str:
    """Lowercase and strip all diacritics (incl. breathings)."""
    return "".join(ch for ch in unicodedata.normalize("NFD", s.lower())
                   if not unicodedata.combining(ch))


def is_token_line(line: str) -> bool:
    fields = line.split()
    return len(fields) >= 9 and fields[7] == "grc"


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def pos_compatible(chosen_pos: str, gold_code: str) -> bool:
    """Coarse POS agreement between a Morpheus analysis and the reference code.

    Single-letter reference classes (V-, N-, C-, ...) match on first letter —
    except that an adjective candidate never counts as matching a noun class;
    two-letter R-codes must match exactly (Morpheus has no demonstrative POS,
    so RD gold lines are excluded from convention derivation).
    """
    g = gold_code.rstrip("-")
    if len(g) == 1:
        return chosen_pos[0] == g and not (g == "N" and chosen_pos in ("A",))
    return chosen_pos == g


def derive_conventions(per_file_lines, choices_by_file):
    """Derive the reference's lemma-convention table from its own gold.

    For every MorphGNT-derived line whose ranked choice disagrees with the gold
    lemma (accent-insensitively) within the same coarse POS class, record the
    pair. A source lemma enters the table only when
      * all of its mismatching tokens map to a single target,
      * at least MIN_CONVENTION_TOKENS of them do so, and
      * no MorphGNT token with this choice agrees with the gold (M == 0) —
        otherwise the "convention" is form-dependent (e.g. a gender or
        enclitic split) and rewriting every occurrence would break tokens
        where Morpheus and the reference already agree.
    The emitted spelling is the majority raw gold form.

    Returns (table, considered, rejected): table maps deacc(source lemma) ->
    target surface form; considered counts mismatching lines examined;
    rejected lists (source, reason, counts) for pairs that failed a guard.
    """
    targets = collections.defaultdict(collections.Counter)   # src key -> Counter(tgt keys)
    surfaces = collections.defaultdict(collections.Counter)  # src key -> Counter(raw gold forms)
    matching = collections.Counter()                         # src key -> agreeing lines
    considered = 0
    for path, lines in per_file_lines.items():
        choices = choices_by_file[path]
        for line, chosen in zip(lines, choices):
            if not is_token_line(line):
                continue
            fields = line.split()
            if "MorphGNT" not in fields[8]:
                continue  # only the trustworthy gold defines conventions
            if chosen is None or chosen.proposed:
                continue
            src_key = deacc(chosen.lemma)
            tgt_key = deacc(fields[6])
            if src_key == tgt_key:
                matching[src_key] += 1  # already agrees (accent-insensitively)
                continue
            if not pos_compatible(chosen.pos, fields[1]):
                continue
            considered += 1
            targets[src_key][tgt_key] += 1
            surfaces[src_key][fields[6]] += 1

    table = {}
    rejected = []
    for src_key, tgt_counts in sorted(targets.items()):
        count = sum(tgt_counts.values())
        if len(tgt_counts) > 1:
            rejected.append((src_key, "multiple targets", count))
        elif count < MIN_CONVENTION_TOKENS:
            rejected.append((src_key, f"< {MIN_CONVENTION_TOKENS} tokens", count))
        elif matching[src_key]:
            rejected.append((src_key, "source also attested in gold",
                             f"{count}/{matching[src_key]}"))
        else:
            table[src_key] = surfaces[src_key].most_common(1)[0][0]
    return table, considered, rejected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default=os.environ.get("AF_CORPUS_DIR", ""))
    parser.add_argument("--out-dir", default=os.path.join(REPO, "tmp", "af", "morph-af"))
    parser.add_argument(
        "--frequencies",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "lemma_frequencies_af.json"),
    )
    parser.add_argument(
        "--model",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "pos_bigram_af.json"),
    )
    parser.add_argument(
        "--conventions",
        action="store_true",
        help="rewrite the lemma column to the reference's dictionary-form convention "
             "(table derived at run time from the corpus's MorphGNT-derived gold)",
    )
    parser.add_argument(
        "--joint",
        action="store_true",
        help="rank by joint (lemma, POS) frequency — POS-optimized; trades ~1pp of lemma",
    )
    parser.add_argument(
        "--tagger",
        action="store_true",
        help="disambiguate with the Viterbi POS-bigram tagger (POS-optimized; "
             "trades ~1pp of lemma on this corpus)",
    )
    args = parser.parse_args()
    if not args.corpus_dir or not os.path.isdir(args.corpus_dir):
        parser.error("give --corpus-dir (or set AF_CORPUS_DIR) pointing at the corpus's data/morph directory")

    files = sorted(glob.glob(os.path.join(args.corpus_dir, "*.txt")))
    if not files:
        parser.error(f"no *.txt files under {args.corpus_dir}")

    # Pass 1: read every file; collect distinct word forms (beta) and raw lines.
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
                beta = to_beta(line.split()[4])
                if beta:
                    distinct.add(beta)

    print(f"files={len(files)} tokens={total_tokens} distinct_forms={len(distinct)}", flush=True)

    # Pass 2: analyze every distinct form (accent-insensitive + ranked candidates).
    freq_data = load_json(args.frequencies)
    morpheus = Morpheus(ignore_accents=True)
    morpheus.ranker = Ranker(
        freq_data.get("frequencies", freq_data),
        joint_frequencies=freq_data.get("by_pos") if args.joint else None,
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

    tagger = PosTagger(load_json(args.model)) if args.tagger else None

    # Pass 3a: choose one analysis per token — Viterbi over each contiguous
    # token run with --tagger, otherwise the top-ranked candidate; remember the
    # choice per line (None for non-token lines and misses).
    choices_by_file = {}
    for path in files:
        lines = per_file_lines[path]
        choices = [None] * len(lines)
        run_items = []  # (line index, candidates)

        def flush_run():
            if not run_items:
                return
            if tagger is None:
                chosen_list = [(cands[0] if cands else None) for _, cands in run_items]
            else:
                chosen_list = tagger.tag([cands for _, cands in run_items])
            for (index, _), chosen in zip(run_items, chosen_list):
                choices[index] = chosen
            run_items.clear()

        for index, line in enumerate(lines):
            if not is_token_line(line):
                flush_run()
                continue
            beta = to_beta(line.split()[4])
            run_items.append((index, candidates.get(beta, [])))
        flush_run()
        choices_by_file[path] = choices

    # Pass 3b: derive the convention table from the trustworthy gold.
    conv_table = {}
    considered = 0
    rejected = []
    if args.conventions:
        conv_table, considered, rejected = derive_conventions(per_file_lines, choices_by_file)
        print(f"conventions: {len(conv_table)} mappings derived "
              f"({considered} mismatching MorphGNT tokens examined; "
              f"{len(rejected)} pairs rejected by the guards)", flush=True)

    # Pass 3c: emit output (same column layout; source -> morpheus when analyzed).
    os.makedirs(args.out_dir, exist_ok=True)
    total_analyzed = 0
    total_fallback = 0
    fallback_by_type: collections.Counter = collections.Counter()
    rewritten_tokens = 0
    rewrite_pairs: collections.Counter = collections.Counter()
    book_stats = {}

    for path in files:
        book = os.path.basename(path)
        lines = per_file_lines[path]
        choices = choices_by_file[path]
        out_lines = []
        fallback_lines = []  # 1-based output line numbers using the corpus annotation

        for line, chosen in zip(lines, choices):
            if not is_token_line(line):
                out_lines.append(line)
                continue
            fields = line.split()
            if chosen is None or chosen.proposed:
                out_lines.append(line)  # fallback: corpus's own annotation
                fallback_lines.append(len(out_lines))
                total_fallback += 1
                fallback_by_type[fields[1]] += 1
                continue
            lemma_out = chosen.lemma
            if args.conventions and deacc(lemma_out) in conv_table:
                lemma_out = conv_table[deacc(lemma_out)]
                rewritten_tokens += 1
                rewrite_pairs[(chosen.lemma, lemma_out)] += 1
            out_lines.append(" ".join([
                fields[0], pos_code(chosen), parsing_code(chosen),
                fields[3], fields[4], fields[5], lemma_out, fields[7], "morpheus",
            ]))
            total_analyzed += 1

        with open(os.path.join(args.out_dir, book), "w", encoding="utf-8") as handle:
            handle.write("\n".join(out_lines) + "\n")
        if fallback_lines:
            with open(os.path.join(args.out_dir, book + ".fb"), "w", encoding="utf-8") as handle:
                handle.write("\n".join(str(n) for n in fallback_lines) + "\n")
        book_stats[book] = sum(1 for line in lines if is_token_line(line))

    # Summary report.
    summary = [
        "Morpheus AF annotation — summary",
        "corpus: Apostolic Fathers reference corpus (*.txt, 9-column layout)",
        f"ranking: {'joint (lemma, POS) frequency' if args.joint else 'plain lemma frequency'}"
        + (" (Viterbi disambiguation)" if args.tagger else " (top-1 candidate)"),
        f"conventions: {'af-conventions' if args.conventions else 'none (natural Morpheus output)'}",
        f"files={len(files)} tokens={total_tokens} distinct_forms={len(distinct)}",
        f"analyzed_by_morpheus={total_analyzed} ({100 * total_analyzed / max(total_tokens, 1):.2f}%)",
        f"fallback_to_corpus={total_fallback} ({100 * total_fallback / max(total_tokens, 1):.2f}%)",
    ]
    if args.conventions:
        summary.append(
            f"convention rewrites: {len(conv_table)} mappings applied to "
            f"{rewritten_tokens} tokens (derived from {considered} mismatching MorphGNT tokens)"
        )
        for (src, tgt), count in rewrite_pairs.most_common(20):
            summary.append(f"  {src} -> {tgt}   ({count})")
        if rejected:
            summary += ["", "pairs rejected by the guards (left contextual):"]
            for src_key, reason, detail in sorted(rejected, key=lambda r: -int(str(r[2]).split('/')[0]))[:15]:
                summary.append(f"  {src_key}: {reason} ({detail})")
    if fallback_by_type:
        summary += ["", "fallbacks by corpus type:"]
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
