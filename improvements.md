# Morpheus: measured improvements since the fork

**Author of the improvements: John Baima (QuantForgeSoftware) — john.baima@quantforge.software**
Report compiled 2026-10-14 from the round records in [`completed.md`](completed.md),
[`python/README.md`](python/README.md), and fresh runs on the current build;
**Round 10 additions appended 2026-10-15; Round 11 (AGLDT pooling) appended 2026-10-15;
Round 14 (entity extraction) appended 2026-10-15.**

This file summarizes how much the analyzer improved, after the fork, when parsing
different Greek texts. It is an **estimate built from measurements**, not a claim of
absolute accuracy; the caveats at the end matter.

## What "before" means

The fork point is the stock Perseus analyzer (`perseids-tools/morpheus`). Before this
work:

- It accepted **only lowercase beta code** and printed Perseus-format strings. Fed a
  real Unicode Greek text, it echoes the token and produces **no analysis at all**
  (verified: `θεοῦ` and `ΛΟΓΟΣ` in → nothing out; `qeo/s` in → a parse).
- Its candidate analyses were in **alphabetical lemma order**, so the correct reading
  was frequently not first.

Two separable gains follow: **enablement** (from ~0% usable on real text to ~94–100%
coverage) and **accuracy** (picking the right reading among candidates).

## Coverage — can the analyzer handle the text at all

| Greek text (tokens) | Fork baseline | Now (default) | Now (opt-in flags) |
|---|---:|---:|---:|
| Septuagint / LXX (623,685) | 94.85% | **99.81%** | 99.81% |
| Classical Greek, AGLDT (469,254) | 92.8%¹ | **99.8%** | 99.8% |
| SBLGNT / NT (137,554) | 93.7% | **95.2%** | 100% (`unknown_as_proper`) |
| Apostolic Fathers (63,222) | 90.7% | 91.2% | **99.35%** (`-n` + elided stems) |
| PapyGreek papyri (36,455) | 89.9% | 92.9% | **95.1%** (`--numerals`) |
| PROIEL Greek NT — independent (132,366) | — | **99.6%** | — |
| PROIEL Herodotus — independent (83,819) | — | **99.8%** | — |

¹ Generous "before": that figure is *with* the new converter but before the elision
fix. A pure forked analyzer scores **0%** on Unicode AGLDT, since word-final `U+0313`
(δ̓, ~34K tokens) and Unicode itself both fail. After the fix, Homer goes 90.3% → 100.0%.

Missed tokens overall fell from ~6% of tokens to ~1% by default, or ~0.2–0.7% with the
opt-in fallbacks — a **~4–25× reduction in misses**, driven by new stemlib material
(`nom.lxx` ~14.8K lines, `nom.biblical`, `nom.papyri`, `nom.elided`) that did not exist
at the fork.

## Accuracy — top-1 lemma (is the gold reading first?)

| Greek text (tokens) | Before (Morpheus order) | After (frequency ranking) | Gain | Error cut |
|---|---:|---:|---:|---:|
| SBLGNT / NT (137,554)ᵃ | 88.1% | **94.6%** | +6.5 | 55% |
| Apostolic Fathers, all (63,222)ᵃ | 84.8% | **90.1%** | +5.3 | 35% |
| — AF, MorphGNT-sourced subset (52,094) | 89.8% | **95.9%** | +6.1 | 60% |
| Classical Greek, AGLDT (469,254) | 79.9% | **91.4%** | +11.5 | 57% |
| PROIEL Greek NT — independent (132,366) | 78.0% | **90.7%** | +12.7 | 58% |
| PROIEL Herodotus — independent (83,819) | 79.9% | **90.2%** | +10.3 | 51% |
| PapyGreek papyri (36,455) | 78.3% | **85.9%** | +7.6 | 35% |
| LXX (623,685, corpus-agreement) | 90.25% | **94.23%** | +4.0 | 41% |

ᵃ Re-measured 2026-10-14 on the current build. The AF row reproduces the committed
README exactly; the SBLGNT row is now *better* than the README's, which was never
re-run after the proper-name additions.

Notes on the before/after:

- The "after" for SBLGNT / AF / AGLDT / PROIEL-Herodotus is plain frequency ranking
  with bundled domain tables (`lemma_frequencies.json`, `_af`, `_grc`). The domain
  table matters for independent texts: on PROIEL Herodotus the classical table beats
  the Koine one by **+4 points** (90.2 vs 86.3).
- The LXX row uses the `--dictionary-forms --base-lemmas` convention layer (natural
  output is 90.25%); it measures agreement with the reference corpus, so treat it as
  a floor.

**Opt-in contextual re-ranking** (`--homographs`) adds a further +0.6 to +1.6 points on
top, and it transfers to unseen text: SBLGNT 93.6→94.4, AF 89.0→89.7, PapyGreek
83.8→85.4, independent PROIEL 92.4→93.0.

## Round 10 additions (2026-10-15)

The tables above use the **default frequency path** and are unchanged (drift from the
new stemlib is within build noise). Round 10 added further measured gains — opt-in
features plus correctness fixes — all on the current build:

- **Learned re-ranker** (`--learned`, opt-in): top-1 lemma on top of frequency ranking —
  SBLGNT 94.6 → **95.0**, AF 90.1 → **90.6**, independent PROIEL 90.7 → **91.5**,
  AGLDT classical 91.4 → **92.1** — uniformly positive, including out-of-register
  classical (every AGLDT author).
- **Adaptive domain-table selection** (`--adaptive-tables`, opt-in): picks the
  best-fitting bundled table automatically. On AGLDT classical it recovers **+6.1**
  points (85.3 → 91.4) that a user who left the Koine default would lose; on the
  Apostolic Fathers it selects the AF table (+0.4).
- **Confidence calibration**: the reported confidence is now temperature-scaled on
  held-out gold (top-1 ECE **0.21 → 0.14** on SBLGNT and AF).
- **Correctness fixes**: interjections now carry POS `I`; the aorist passive of `-έλλω`
  verbs resolves (`ἀπηγγέλη` → `ἀπαγγέλλω`); the `pers_name` `-πλ` lemma artifact is gone
  (SBLGNT 4/40K and AGLDT 26/120K bogus top-1 lemmas → 0, no coverage loss).
- **Reproducible gate**: `scripts/benchmark.py` + `benchmarks/expected_greek.json`
  (offline, tolerance-gated, bootstrap CIs); analysis parallelizes **3.06×** at
  `jobs=4`.

## Round 11 additions (2026-10-15)

The AGLDT v2.1 Greek treebank (which was used only to *evaluate* and to build the
classical frequency table) is now also **pooled into the learned re-ranker**. Trained on
SBLGNT + Apostolic Fathers + AGLDT (385,758 tokens; `--agldt-limit 200000` balances the
pool), the model is much stronger on classical text while keeping the Koine corpora
within build noise:

| corpus | frequency ranking | learned (Koine model) | learned (pooled) |
| --- | ---: | ---: | ---: |
| AGLDT v2.1 Greek (classical) | 91.4% | 92.1% | **93.2%** |
| PROIEL greek-nt (independent) | 91.7% | 91.5% | **92.2%** |
| SBLGNT | 94.6% | 95.0% | 94.7% |
| Apostolic Fathers | 90.1% | 90.6% | 90.3% |

(A ~0.3pp Koine drift, inside the ±0.5pp build-noise band; the unbalanced pool cost
~0.7pp — hence the `--agldt-limit` balance.) The same gold now also builds a classical
POS bigram model (`data/pos_bigram_grc.json`); it is the better bigram for classical text
*if* the Viterbi tagger is used (Homer POS 87.3% vs 84.8%), but the tagger still trails
plain frequency-ranked POS (85.2% on AGLDT) — the long-standing negative result stands.
The offline benchmark thresholds were re-baselined to this model.

## Round 14 additions (2026-10-15): entity extraction on documentary papyri

Round 14 evaluated Morpheus as the morphology layer under an external
entity-extraction task (economic entities in documentary papyri, measured on a
public 115-document gold set; measurement only — no corpus text is committed).
The analyzer is not the extractor; it is the **canonicalize / soft-validate**
layer on top of a fine-tuned NER model. Measured on that gold:

- **Canonicalization gain**: matching entities in Morpheus lemma space (instead
  of surface strings) lifts micro F1 on the NER route 0.580 → **0.594** and on a
  raw-LLM route 0.229 → **0.274** — the analyzer recovers agreement between
  inflected variants. After gold fine-tuning (strict 0.717) the gain is +0.8pp
  (0.717 → 0.725): real, but it shrinks as the extractor improves.
- **Soft validation is informative but must not filter**: predicted entities
  whose morphology is fully known strict-match gold **62.7%** of the time vs
  **55.3%** for the rest (53% of predictions are fully known, 31% not at all).
  Hard-filtering to known words drops strict F1 0.580 → **0.422**, so validation
  stays a *confidence signal*, never a filter. On the fine-tuned model the same
  pattern holds more weakly (70.5% vs 66.4%; filter 0.717 → 0.522).
- **Candidate generation for recall**: 46% of the extractor's missed entities
  (425/931) contain a content word Morpheus flags (unanalysed or numeral); a
  whitelist-filtered LLM pass over just those candidates raises strict recall
  +4.6pp (strict F1 0.580 → **0.585**, relaxed 0.683 → **0.689**) at one extra
  LLM call per document — versus a naive unfiltered pass, which is F1-negative.
  On a stronger (gold-fine-tuned) extractor the same pass is net-negative
  (0.717 → 0.700): the boost is a crutch for a weak extractor, not a permanent
  layer.

Two toolkit gaps surfaced (carried as follow-ups, not fixed here):

- **Letter-numerals are opt-in and incomplete**: the PapyGreek numeral table
  (`Morpheus(numerals=True)`, 50 forms) resolves common letter-numerals, but the
  lowercase letter for 1 is absent (its capital form is present) and the table
  is off by default.
- **False-friend analyses outrank name proposals**: an *unanalysed* token gets a
  proper-name proposal, but a capitalized genitive name that collides with a
  rare stemlib verb entry keeps the verb lemma — name-like entity keys therefore
  need a surface fallback (implemented in the Round 14 canonicalizer, not in the
  toolkit).

## Bottom line

- **Coverage**: ~94% of tokens analyzable at the fork's best → **~99% now** (and
  ~99.5%+ with the opt-in fallbacks); on true Unicode input the fork was 0%.
- **Top-1 lemma accuracy**: token-weighted across ~1.55M tokens, roughly
  **84.8% → 92.5%** — the top-1 lemma **error rate is about halved** (15.2% → 7.5%),
  with per-corpus gains of +4 to +13 points.

## Caveats

- **"Before" for top-1 is "raw Morpheus order",** measured on the current stemlib; the
  pure forked analyzer was a touch lower still (SBLGNT 86.7 at fork-time toolkit).
- **LXX and the LXX/AF/PG tables are corpus-trained**, so their agreement numbers
  measure domain consistency, not absolute accuracy. The two PROIEL corpora are
  independent gold and show the same magnitude of gain, which is the strongest
  evidence the ranking is real and not convention-fitted.
- **POS is the weak dimension** (~74–85%), because Morpheus collapses
  noun/adjective/pronoun/article into `N`; lemma accuracy is the headline.
- **PapyGreek numerals and the false-hit letter numerals** remain a known limitation
  (only partially addressed by the opt-in `--numerals`).

## Reproducing the spot checks

```bash
# SBLGNT (current build: coverage 95.2%, top-1 88.1 -> 94.6, POS 77.4)
.venv/bin/python scripts/agreement_report.py --morphgnt-dir /path/to/morphgnt

# Apostolic Fathers (coverage 91.2%, top-1 84.8 -> 90.1, POS 74.3)
.venv/bin/python scripts/agreement_report.py \
    ../apostolic-fathers/data/morph/*.txt \
    --lemma-field 7 --pos-field 2 --source-field 9 --lang-field 8 --by-source
```

The classical (AGLDT), PROIEL, and PapyGreek figures come from the per-round
evaluators recorded in `completed.md` (Rounds 8–9).

The whole table (raw → frequency-ranked → learned, plus coarse POS, with bootstrap
CIs and a tolerance gate) is reproducible in one command:

```bash
MORPHGNT_DIR=/path/to/morphgnt AF_CORPUS_DIR=/path/to/apostolic-fathers/data/morph \
AGLDT_DIR=/path/to/agldt/v2.1/Greek/texts PROIEL_DIR=/path/to/greek-nt.conll \
    .venv/bin/python scripts/benchmark.py --learned --bootstrap 300
```
