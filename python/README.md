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
| SBLGNT (MorphGNT) | 137,554 | 93.6% | 86.5% | **92.9%** | 76.8% |
| Apostolic Fathers (all) | 63,222 | 90.7% | 84.2% | **89.7%** | 74.8% |
| — of which MorphGNT-sourced | 52,094 | 96.3% | 89.5% | **95.6%** | 76.1% |

Ranking adds ~6 points of top-1 lemma accuracy over Morpheus's native order,
out of domain. The lower numbers on the `grc_proiel_lg` subset reflect the noise
in that (machine-generated) reference more than Morpheus itself.

## Known limitations

- **POS granularity.** Morpheus tags nouns, adjectives, pronouns, articles and
  prepositions all as `N`; the stem type recovers most of them, but noun vs
  adjective remains ambiguous. POS agreement is therefore lower than lemma
  agreement.
- **Contextual ranking is experimental.** The hand-written context rules in
  `ranking.py` currently *hurt* accuracy (they are off by default); a learned
  tagger over the candidate set is the real fix.
- **Coverage.** ~1.5–2% of tokens get no analysis at all (proper names,
  post-classical forms); AF-specific stems would need adding to `stemlib`.

## Tests

```bash
cd python && ../.venv/bin/pytest -q
```
