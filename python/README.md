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
- **Case handling** — Greek input is normalized to lowercase beta code before it
  reaches the analyzer (which only matches lowercase), so corpus-style uppercase
  input works as-is; Latin passes through untouched.

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

The Apostolic Fathers (Greek, 63,222 tokens) come out at **98.4% analyzed**.

## Python

```python
from morpheus_toolkit import Morpheus

morpheus = Morpheus()                      # uses ./bin/cruncher + bundled frequencies
for result in morpheus.analyze_text("ἐν ἀρχῇ ἦν ὁ λόγος"):
    best = result.best
    print(result.token, best.pos, best.lemma, best.feature_string())
```

## Languages

Morpheus parses Latin as well as Greek. Set `language="latin"` (CLI:
`--language latin`) and the tokens are passed through untouched (no beta-code
round-trip):

```python
Morpheus(language="latin").analyze_text("femina amo dominus")
```

## Strong's numbers and confidence

Every Greek analysis carries a **Strong's number** (from the SBLGNT lemma mapping)
and a softmax **confidence**; Latin analyses have neither:

```python
best = morpheus.analyze_text("θεοῦ")[0].best
best.strongs      # 2316
best.confidence   # 0.32
```

The Strong's table is MorphGNT-convention, so a few Morpheus spelling variants
(γίγνομαι vs γίνομαι) resolve through their lemma variants when possible.

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
| Apostolic Fathers (all) | 63,222 | 91.2% | 84.8% | **90.1%** | 74.3% |
| — of which MorphGNT-sourced | 52,094 | 96.5% | 89.8% | **95.9%** | 75.5% |

The Apostolic Fathers rows were re-measured after the LXX stemlib additions (see
below); the SBLGNT row predates them and was not re-run.

Ranking adds ~6 points of top-1 lemma accuracy over Morpheus's native order,
out of domain. The lower numbers on the `grc_proiel_lg` subset reflect the noise
in that (machine-generated) reference more than Morpheus itself.

Two contextual approaches were built and measured but do **not** beat plain
frequency ranking, so both are off by default:

- a POS-bigram Viterbi tagger (`tagger.py`, `--tagger`): 92.9% vs 93.0%;
- joint (lemma, POS) frequency (`--joint`): 91.9% top-1 but 77.8% POS (vs 76.2%).

They need a *learned* emission model (P(lemma | tag)) and a proper tagger to pay
off; the bundled hand-built model is not enough.

## The Septuagint (LXX)

Morpheus's Greek stemlibs carry a generated `nom.lxx` with ~4,500 proper names and
curated common words taken from a reference morphological analysis of the LXX, plus
explicit verb entries for inflections the generative paradigms miss. Against that
corpus (623,685 tokens) Morpheus now analyzes **99.81%**; the residual 0.19% is
interjections and a handful of rare forms. The stemlib entries are regenerated with
`scripts/build_lxx_stemlib.py` — see the root [README](../README.md#septuagint-lxx).

Two disambiguation models trained on that corpus are bundled in `data/`:
`pos_bigram_lxx.json` (16 coarse POS tags) and `lemma_frequencies_lxx.json`
(12,943 lemmas, with plain frequencies plus joint lemma×POS counts). Rebuild
them from a local checkout of the reference corpus:

```bash
scripts/build_pos_model.py --format mlxx --corpus-dir /path/to/lxx-corpus
scripts/build_lemma_frequencies.py --format mlxx --corpus-dir /path/to/lxx-corpus
```

### Full-corpus annotation

`scripts/build_morph_lxx.py` analyzes every token of the corpus with Morpheus —
two-pass accent handling, frequency ranking, Viterbi POS-bigram disambiguation — and
writes re-annotated files in the reference format (`form type parse lemma [prefix]`,
with `parse` = Morpheus's full 8-char parsing code):

```bash
scripts/build_morph_lxx.py --corpus-dir /path/to/lxx-corpus \
    [--out-dir tmp/lxx/morph-lxx] [--dictionary-forms] [--base-lemmas]
```

Tokens with no candidate fall back to the corpus's own annotation (counted per book
in `summary.txt`), so the output is complete. Lemma convention is compound lemmas in
canonical beta, uppercased to match the corpus style.

Two opt-in convention modes align the output with the reference's dictionary-form
practice (both off = natural Morpheus output):

- **`--dictionary-forms`** — closed-set surface forms get the reference's
  dictionary-form convention: articles → ὁ/RA, personal pronouns → ἐγώ|σύ/RP,
  demonstratives → family nominative/RD (three embedded tables derived from the
  corpus; unambiguous forms are forced before Viterbi, homographic article/relative
  pairs stay contextual). Where Morpheus offers the target lemma in several same-POS
  feature readings (masc/neut homographs), a per-spelling tie-break table decides —
  the reference's own accent notation correlates strongly with the reading
  (`AU)TOU=` is 97% GSM, `AU)TOU\S` ~100% APM).
- **`--base-lemmas`** — compound verbs lemmatize to the base verb (the preverb stays
  in the prefix column). A preverb is stripped only when the remainder resolves as an
  attested verb; contracted compounds (δια+ἔρχομαι → διέρχομαι) are recovered by
  tail-matching guarded on attested preverb remnants.

Agreement with the reference corpus on Morpheus-analyzed tokens, natural output vs
both conventions enabled:

| mode | lemma | coarse POS | parse fields |
|---|---|---|---|
| natural (no flags) | 90.25% | 85.09% | 76.26% |
| `--dictionary-forms --base-lemmas` | **94.23%** | **90.54%** | **79.75%** |

Both models were trained on this same corpus, so these numbers measure domain
consistency as much as absolute accuracy — a floor for untagged LXX text, not a
celling claim. Residual disagreement is dominated by documented reference quirks
(surface-form lemmas like τοῦ→τοῦ; ἰδοὺ lemmatized as ὁράω), the ἕως/ἠώς homograph
(277 tokens), and ~286 compound verbs the reference keeps unstripped while the
base-lemma heuristic strips (etymologically they are compounds).

## Known limitations

- **POS granularity.** Morpheus tags nouns, adjectives, pronouns, articles and
  prepositions all as `N`; the stem type recovers most of them, but noun vs
  adjective remains ambiguous. POS agreement is therefore lower than lemma
  agreement.
- **Contextual ranking is experimental.** The hand-written context rules in
  `ranking.py` *hurt* accuracy and the POS-bigram Viterbi tagger in `tagger.py`
  merely matches frequency ranking; both are off by default.
- **Coverage.** A small fraction of NT tokens gets no analysis, historically dominated
  by **biblical proper names** (Δαυίδ, Φαρές, Ἀμιναδάβ, …) absent from `stemlib`;
  coverage improved slightly after the LXX additions (`nom.lxx`) since many biblical
  names are shared. Enable
  `unknown_as_proper=True` (CLI: `--unknown-as-proper`) to give unanalyzed tokens a
  synthetic proper-noun analysis (lemma = surface, POS `N`/`NP`, flagged
  `proposed=True`). This brings the analysis rate to **100%** on both the SBLGNT and
  the Apostolic Fathers. ~6% of tokens are analyzed but with a different lemma than
  the gold corpus.

## Tests

```bash
cd python && ../.venv/bin/pytest -q
```
