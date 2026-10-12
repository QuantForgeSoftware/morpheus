#!/usr/bin/env python3
"""
Generate `stemlib/Greek/stemsrc/nom.papyri` — proper names and a few dialectal
words attested in the PapyGreek treebanks (Helsinki; CC BY-SA 4.0) that the
classical stemlibs do not cover: Egyptian deity/month/personal names, papyrus
spelling variants of personal pronouns, and Egyptian loanwords.

It runs Morpheus over the corpus's ORIGINAL spellings (editorial markers
stripped), keeps tokens that get **no** analysis whose gold POS is nominal or
pronominal and whose regularized-layer lemma is capitalized (i.e. a name) with
a total count of at least --min-count, and emits `:le:`/`:wd:` entries marking
them as indeclinable `pers_name`s — the same convention as nom.biblical.

A small curated section (pronoun variants, loanwords) is emitted from the
CURATED structure below; keep all curation in this script, never hand-edit
the managed region of the generated file.

Usage:
  scripts/build_papyri_stemlib.py --corpus-dir <papygreek-treebanks-root>
      [--min-count 2] [--out stemlib/Greek/stemsrc/nom.papyri]
"""
from __future__ import annotations

import argparse
import collections
import glob
import html
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.beta import from_beta, normalize_lemma, to_beta  # noqa: E402
from morpheus_toolkit.runner import MorpheusRunner  # noqa: E402

# PapyGreek ALDT postag (9 chars): pos person number tense mood voice GENDER CASE degree.
# Note the order differs from MorphGNT's code: gender precedes case, and both are
# lowercase here. Only positions we need: number = index 2, gender = index 6.
GENDER = {"m": "masc", "f": "fem", "n": "neut"}
NUMBER = {"s": "sg", "p": "pl", "d": "dual"}

# Editorial markers (LappEpiDoc + PapyGreek variants) stripped before analysis:
# |num:N| / |g:...| annotation spans, then supplement/uncertainty brackets in
# every bracket family the corpus uses, line-break marks, ellipses, and
# hyphenation. The apostrophes ʼ ’ are real elision marks and are kept;
# combining diacritics (͂ ͅ …) are Greek letters, not markers.
PIPE_ANN = re.compile(r"\|[a-z]+:[^|]*\|")
MARKERS = re.compile(
    r"[∼∽∤⋰⋱⸢⸣❨❩<>[\]{}()〚〛⊢⊣⸌⸍⎴⎵⦑⦒⸜⸝⧼?…-]+|̣")


def strip_markers(form: str) -> str:
    return MARKERS.sub("", PIPE_ANN.sub("", form)).strip()


# Lemmas to skip. The two entries below are declined forms of well-known
# names that the treebank occasionally uses as the lemma itself (Ἀχιλλᾶς is a
# variant genitive of Ἀχιλλεύς, Ἰωνᾶ an accusative of Ἰωνᾶς); Morpheus already
# analyzes both correctly, so generated entries would only duplicate them.
EXCLUDE: set = {"Ἀχιλλᾶς", "Ἰωνᾶ"}

# Curated non-name entries, emitted under a managed marker so re-runs are
# idempotent and curation stays in this script. Each value is the full
# `:wd:` payload after the form beta.
CURATED: dict = {
    # Dialectal dative-plural spellings of the personal pronouns (PapyGreek
    # attests -ε- where the classical stemlibs only carry ἡμῖν/ὑμῖν).
    "e)gw/": [("h(mei=n", "pron1 1st pl masc fem dat")],
    "su/": [("u(mei=n", "pron1 2nd pl masc fem dat")],
    # Egyptian loanword (diminutive 'little'); the treebank tags κίκιος as a
    # neuter genitive of κίκι.
    "ki/ki": [("ki/kios", "indecl neut gen sg")],
}

CURATED_MARKER = "# --- curated entries (managed by build_papyri_stemlib.py) ---"


def read_rows(corpus_dir: str):
    """Yield (form_clean, lemma_reg, pos1, postag_reg) for every Greek word."""
    rows = []
    for path in sorted(glob.glob(os.path.join(corpus_dir, "**", "*.xml"), recursive=True)):
        with open(path, encoding="utf-8") as fh:
            content = html.unescape(fh.read())
        for m in re.finditer(r"<word\s+([^>]+)/>", content):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            if a.get("lang", "grc") != "grc":
                continue
            clean = strip_markers(a.get("form_orig", ""))
            lemma = a.get("lemma_reg", "")
            postag = a.get("postag_reg", "")
            pos1 = postag[0] if postag else ""
            if not clean or not lemma:
                continue  # unanalyzable editorial tokens / unannotated
            if not re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", clean):
                continue  # illegible-text placeholders ($ etc.) — no word to analyze
            rows.append((clean, lemma, pos1, postag))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus-dir",
        default=os.environ.get("PAPYGREEK_DIR", ""),
        help="root of the extracted PapyGreek treebanks (ALDT XML)",
    )
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument(
        "--out",
        default=os.path.join(REPO, "stemlib", "Greek", "stemsrc", "nom.papyri"),
    )
    args = parser.parse_args()
    if not args.corpus_dir or not os.path.isdir(args.corpus_dir):
        parser.error("give --corpus-dir (or set PAPYGREEK_DIR) pointing at the treebanks")

    rows = read_rows(args.corpus_dir)
    print(f"rows={len(rows)}", flush=True)

    runner = MorpheusRunner()
    distinct = sorted({to_beta(r[0]) for r in rows if to_beta(r[0])})
    recognized: dict = {}
    BATCH = 2000
    for i in range(0, len(distinct), BATCH):
        chunk = distinct[i:i + BATCH]
        for beta, analyses in zip(chunk, runner.analyze_beta(chunk, ignore_accents=True)):
            if analyses:
                recognized[beta] = list(analyses)
        print(f"  analyzed {min(i + BATCH, len(distinct))}/{len(distinct)}", flush=True)

    # Count missed tokens per (lemma, form); keep nominal/pronominal names.
    counts: dict = collections.defaultdict(lambda: [0, set()])   # lemma_beta -> [tokens, forms]
    features: dict = collections.defaultdict(set)                # lemma_beta -> {(form, gender, number)}
    for clean, lemma, pos1, postag in rows:
        if pos1 not in ("n", "p"):
            continue
        if not lemma or not lemma[0].isupper():
            continue  # names are capitalized; skips common nouns and pronouns
        beta = to_beta(clean)
        if not beta or recognized.get(beta):
            continue  # covered — nothing to add
        lemma_beta = to_beta(lemma)
        if not lemma_beta:
            continue
        counts[lemma_beta][0] += 1
        counts[lemma_beta][1].add(beta)
        gender = GENDER.get(postag[6] if len(postag) > 6 else "-", "masc")
        number = NUMBER.get(postag[2] if len(postag) > 2 else "-", "sg")
        features[lemma_beta].add((beta, gender, number))

    # Threshold: papyri carry more scribal noise than LXX/AF, so one-off forms
    # are dropped (Round 2 added all missed biblical names; here count >= N).
    candidates = {lb: features[lb] for lb, (tok, _forms) in counts.items() if tok >= args.min_count}
    print(f"missed name lemmas above threshold: "
          f"{len(candidates)} ({sum(v[0] for v in counts.values() if v[0] >= args.min_count)} tokens)", flush=True)

    # Keep the names whose *dictionary form* Morpheus does not already analyze with
    # the right lemma — this catches both misses and names it mistakes for a common
    # word. Merge with any existing file so re-running is idempotent.
    excluded = {to_beta(item) for item in EXCLUDE}
    candidates = {lb: f for lb, f in candidates.items() if lb not in excluded}
    lemma_betas = sorted(candidates)
    names: dict = load_existing(args.out)
    if lemma_betas:
        recognized_lemmas = runner.analyze_beta(lemma_betas)
        for lemma_beta, result in zip(lemma_betas, recognized_lemmas):
            gold = normalize_lemma(from_beta(lemma_beta))
            if result and any(a.matches_lemma(gold) for a in result):
                continue  # already known with the right lemma
            names[lemma_beta] |= candidates[lemma_beta]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    entries = 0
    with open(args.out, "w", encoding="utf-8") as out:
        out.write("# Papyrological proper names and dialectal words absent from the\n")
        out.write("# classical stemlibs (PapyGreek treebanks v1.01, CC BY-SA 4.0).\n")
        out.write(f"# Generated by scripts/build_papyri_stemlib.py (--min-count {args.min_count}).\n\n")
        for lemma_beta in sorted(names):
            if lemma_beta in excluded:
                continue
            out.write(f":le:{lemma_beta}\n")
            for form_beta, gender, number in sorted(names[lemma_beta]):
                out.write(f":wd:{form_beta}\tindecl {gender} nom voc gen dat acc {number} pers_name\n")
                entries += 1
            out.write("\n")
        out.write(CURATED_MARKER + "\n")
        for lemma_beta in sorted(CURATED):
            out.write(f":le:{lemma_beta}\n")
            for form_beta, payload in CURATED[lemma_beta]:
                out.write(f":wd:{form_beta}\t{payload}\n")
                entries += 1
            out.write("\n")
    print(f"Wrote {len(names)} names + curated to {os.path.relpath(args.out, REPO)} ({entries} forms)")
    return 0


def load_existing(path: str) -> dict:
    """Parse an existing nom.papyri back into {lemma_beta: {(form, gender, number)}}.

    Only the generated (pers_name) region is merged; the curated section is
    re-emitted from CURATED and excluded here so it cannot drift. Excluded
    lemmas are dropped on merge.
    """
    names: dict = collections.defaultdict(set)
    if not os.path.exists(path):
        return names
    excluded = {to_beta(item) for item in EXCLUDE}
    curated_keys = set(CURATED)
    current = None
    curated = False
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if CURATED_MARKER in line:
            curated = True
            continue
        if line.startswith(":le:"):
            current = line[4:].strip()
            if current in excluded or (curated and current not in curated_keys):
                current = None
        elif line.startswith(":wd:") and current and not curated:
            parts = line[4:].split()
            if len(parts) >= 3 and "pers_name" in parts:
                names[current].add((parts[0], parts[2], parts[-2]))
    return names


if __name__ == "__main__":
    sys.exit(main())
