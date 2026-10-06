# morpheus-toolkit

A Unicode/JSON layer around the [Morpheus](../) Ancient Greek morphological
analyzer. Morpheus itself speaks beta code and prints Perseus-format analyses;
this package makes it usable on arbitrary Greek texts:

- **Unicode in/out** — converts UTF-8 Greek to beta code (and back) with
  [`beta-code`](https://pypi.org/project/beta-code/).
- **Structured output** — parses Morpheus's analyses into records with lemma,
  fine-grained POS, and morphological features; emits JSON.
- **Ranking** — re-orders candidate analyses by lemma frequency (and optional
  context). Morpheus sorts candidates alphabetically by lemma, which puts the
  wrong reading first surprisingly often (e.g. `θεοῦ` → the verb θεάομαι).
- **Tokenization** — splits raw Greek text into tokens.
- **Alignment** — uses the engine's `-q` delimiter so misses stay in position.

## Install

Build the analyzer first (from the repository root):

```bash
scripts/build.sh            # -> bin/cruncher
```

Then install the toolkit:

```bash
python3 -m venv .venv
.venv/bin/pip install -e python/ pytest
```

## CLI

```bash
# raw UTF-8 text
.venv/bin/morpheus-toolkit analyze text.txt --json out.jsonl

# a columnar token file (MorphGNT / Apostolic Fathers); token is column 5
.venv/bin/morpheus-toolkit analyze data/morph/011-didache.txt --morphgnt
```

For a whole corpus, `scripts/analyze_corpus.py` keeps the reference/gold columns,
writes JSONL, and prints a coverage summary:

```bash
scripts/analyze_corpus.py ../apostolic-fathers/data/morph/*.txt \
    --ref-field 1 --token-field 5 --lemma-field 7 --lang-field 8 --lang-value grc
```

The Apostolic Fathers (Greek, 63,222 tokens) come out at **98.2% analyzed**.

## Python

```python
from morpheus_toolkit import Morpheus

morpheus = Morpheus()                      # uses ./bin/cruncher + bundled frequencies
for result in morpheus.analyze_text("ἐν ἀρχῇ ἦν ὁ λόγος"):
    best = result.best
    print(result.token, best.pos, best.lemma, best.feature_string())
```

## Ranking

The bundled frequency table is derived from the MorphGNT SBLGNT (CC-BY-SA 4.0).
Rebuild it with:

```bash
scripts/build_lemma_frequencies.py --morphgnt-dir /path/to/morphgnt
```

Measure agreement against a gold corpus with `scripts/agreement_report.py`:

```bash
scripts/agreement_report.py --morphgnt-dir /path/to/morphgnt          # SBLGNT
scripts/agreement_report.py ../apostolic-fathers/data/morph/*.txt \
    --lemma-field 7 --pos-field 2 --source-field 9 --lang-field 8 --by-source
```

Measured effect of ranking (gold = the corpus lemma; "top1" = gold is the first
candidate; "before" = Morpheus order, "freq" = after frequency ranking):

| Corpus | tokens | coverage | top-1 before | top-1 freq | POS |
| --- | ---: | ---: | ---: | ---: | ---: |
| SBLGNT (MorphGNT) | 137,554 | 93.7% | 86.7% | **93.0%** | 76.6% |
| Apostolic Fathers (all) | 63,222 | 90.9% | 84.5% | **89.9%** | 74.6% |
| — of which MorphGNT-sourced | 52,094 | 96.4% | 89.7% | **95.7%** | 75.9% |

Ranking adds ~6 points of top-1 lemma accuracy over Morpheus's native order,
out of domain. The lower numbers on the `grc_proiel_lg` subset reflect the noise
in that (machine-generated) reference more than Morpheus itself.

Two contextual approaches were built and measured but do **not** beat plain
frequency ranking, so both are off by default:

- a POS-bigram Viterbi tagger (`tagger.py`, `--tagger`): 92.9% vs 93.0%;
- joint (lemma, POS) frequency (`--joint`): 91.9% top-1 but 77.8% POS (vs 76.2%).

They need a *learned* emission model (P(lemma | tag)) and a proper tagger to pay
off; the bundled hand-built model is not enough.

## Known limitations

- **POS granularity.** Morpheus tags nouns, adjectives, pronouns, articles and
  prepositions all as `N`; the stem type recovers most of them, but noun vs
  adjective remains ambiguous. POS agreement is therefore lower than lemma
  agreement.
- **Contextual ranking is experimental.** The hand-written context rules in
  `ranking.py` *hurt* accuracy and the POS-bigram Viterbi tagger in `tagger.py`
  merely matches frequency ranking; both are off by default.
- **Coverage.** ~1.6% of NT tokens get no analysis, and the large majority are
  **biblical proper names** (Δαυίδ, Φαρές, Ἀμιναδάβ, …) absent from `stemlib`.
  A proper-name stemlib (or an explicit unknown-name fallback) is the highest-value
  next step for coverage; ~6% of tokens are analyzed but with a different lemma
  than the gold corpus.

## Tests

```bash
cd python && ../.venv/bin/pytest -q
```
