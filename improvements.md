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

**Round 15 update:** since the B-item sprint the *shipped default* is learned
re-ranking + adaptive table selection, worth another **+7.2** on AGLDT (86.56 →
**93.74**), +0.5 on PROIEL (91.66 → **92.19**), +2.3 on the LXX (→ **90.7**) and
+4.5 on PapyGreek (→ **85.7**) — see the Round 15 section below.

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
new stemlib is within build noise). Round 10 added further measured gains — the
learned re-ranker and adaptive table selection (both shipped as defaults in Round 15)
plus correctness fixes — all on the current build:

- **Learned re-ranker** (now the default; Round 15 numbers below): top-1 lemma on top
  of frequency ranking — uniformly positive, including out-of-register classical
  (every AGLDT author).
- **Adaptive domain-table selection** (now the default): picks the best-fitting
  bundled table automatically. On AGLDT classical it recovers **+6.1** points
  (85.3 → 91.4) that a user who left the Koine default would lose; on the Apostolic
  Fathers it selects the AF table (+0.4).
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
  lowercase letter for 1 was absent (its capital form is present) and the table
  is off by default. (Round 15 fixed the case gap — α and ε now fall back to
  their capital entries; the table stays opt-in.)
- **False-friend analyses outrank name proposals**: an *unanalysed* token gets a
  proper-name proposal, but a capitalized genitive name that collides with a
  rare stemlib verb entry keeps the verb lemma — name-like entity keys therefore
  need a surface fallback (implemented in the Round 14 canonicalizer, not in the
  toolkit).

## Round 15 additions (2026-10-15): the learned + adaptive defaults (B-sprint)

Round 15 shipped the **B1 default flip**: the learned re-ranker and adaptive
frequency-table selection are now the Greek defaults — `Morpheus()` and
`scripts/benchmark.py` get both with no flags. Opt out with
`Morpheus(use_learned=False, adaptive_tables=False)` /
`--no-learned --no-adaptive-tables`; caller-supplied `frequencies=` are never
overridden. Validated on every local corpus against the old default (frequency
ranking with the fixed Koine table), on identical candidate sets:

| corpus (tokens) | old default | new default | gain |
| --- | ---: | ---: | ---: |
| SBLGNT / NT (137,554) | 94.56% | **94.67%** | +0.1 |
| Apostolic Fathers (63,227) | 90.14% | **90.21%** | +0.1 |
| Classical Greek, AGLDT (469,254) | 86.56% | **93.74%** | **+7.2** |
| PROIEL Greek NT — independent (132,366) | 91.66% | **92.19%** | +0.5 |
| LXX (623,685, exact) | 88.4% | **90.7%** | +2.3 |
| PapyGreek papyri (36,455, exact) | 81.2% | **85.7%** | +4.5 |
| — PapyGreek + `--numerals` (95.1% coverage) | 81.2% | **87.8%** | +6.6 |

- Adaptive selection picked the right register on every corpus (fit margins):
  SBLGNT → Koine (0.91 vs 0.89 classical), Apostolic Fathers → AF (0.89 vs 0.86),
  AGLDT → classical (0.95 vs 0.79), PROIEL → Koine (0.91 vs 0.90), LXX → LXX
  (0.93 vs 0.88), PapyGreek → papyri (0.72 vs 0.68).
- The NT-family corpora gain least (they were already served by the Koine default);
  the flip is worth **+7.2 on classical, +4.5 on papyri, +2.3 on the LXX** — the
  corpora a reader beyond the NT actually needs.
- The gate (`scripts/benchmark.py` + `benchmarks/expected_greek.json`) was
  re-baselined from the shipped-default run; the old frequency path stays available
  (`--no-learned --no-adaptive`, plus `--no-gate` for diagnostic runs).
- One measured interaction, kept for the record: on the Apostolic Fathers the learned
  path gives back a fraction of the table-selection gain (learned + AF table 90.21 vs
  frequency + AF table 90.45) — the model's features were trained against the default
  table, so a selected table helps its *fallback* order more than its scores. Net vs
  the old default is still positive.

Also in this round:

- **Confidence follows the score path.** The bundled softmax temperature (T=0.08) was
  fitted on frequency scores; the learned path now gets its own
  (`temperature_learned=1.0` — the learned scores turn out natively calibrated).
  Top-1 expected calibration error on the shipped path: **0.005** (SBLGNT) /
  **0.002** (AF), vs **0.142 / 0.139** for the calibrated frequency path (raw
  0.208 / 0.203) — the default path's confidence is ~30× tighter than pre-flip.
- **Lowercase letter-numerals fixed** (Round 14 gap): α and ε resolve via a case
  fallback to the table's capital entries. PapyGreek `--numerals` numeral misses drop
  853 → 38 of 1,454; coverage 92.9% → 95.1%.
- **Homograph re-ranking stays opt-in, now measured on the shipped default**: SBLGNT
  94.7 → 94.9, AF 90.2 → 90.7, PROIEL 92.2 → 93.1, but AGLDT **93.7 → 93.3** (the
  table is Koine/NT-trained; classical ὃ/τε/ἢ usage differs), so it does not meet
  the "never worse" bar for a default flip.
- **B8 head-to-head (measurement only, not shipped).** On identical ambiguous-token
  example sets (≥2 candidates, gold among them), bundled learned vs an MLP head over
  frozen `pranaydeeps/Ancient-Greek-BERT` context, trained on SBLGNT:

  | ambiguous tokens | freq | bundled learned | LM-MLP | combined |
  | --- | ---: | ---: | ---: | ---: |
  | SBLGNT test split (4,320) | 97.7% | 97.9% | **99.4%** | 99.4% |
  | Apostolic Fathers (21,589) | 96.9% | 97.3% | **98.0%** | 98.0% |
  | PROIEL NT, accent-insensitive (72,141) | 95.4% | **96.4%** | 92.3% | 92.7% |

  Corpus-level projection: SBLGNT test 94.0/94.1/**94.6**/94.6, AF
  90.1/90.3/**90.5**/90.5, PROIEL 91.7/**92.2**/89.9/90.2 (the AF and PROIEL
  projections reproduce the benchmark exactly, so the harness is comparable). The LM
  head has real headroom on accented text (+0.5pp corpus-level over the bundled
  learned on the SBLGNT test slice, +0.2 on AF) but **regresses on the shipped
  accent-insensitive pipeline**: PROIEL analyzed with `ignore_accents` is 59.4%
  multi-candidate (vs 37.8% with accents; 38.8% vs 22.1% distinct-lemma), i.e.
  dominated by accent-variant homographs the LM head was never trained on. The
  combined model ≈ LM (the learned-rank feature adds nothing). **Not shipped**
  (`torch` + ~440 MB GPL-3.0-derived weights); the actionable finding is that an LM
  layer must be trained on the shipped candidate distribution (including
  `ignore_accents` examples), not just on accented gold text.
- **B10 verified.** "Logion" (Cowen-Breen et al., *Machine-Learning Based Detection
  and Correction of Textual Errors in Greek Philology*, ALP 2023; `charliecb/Logion`;
  HF `cabrooks/LOGION-*`) is a scribal-error BERT, not a corpus: its 70M-word
  training corpus is request-only, and its models derive from a GPL-3.0 base with no
  licence card — not a clean corpus/LM candidate.

## Bottom line

- **Coverage**: ~94% of tokens analyzable at the fork's best → **~99% now** (and
  ~99.5%+ with the opt-in fallbacks); on true Unicode input the fork was 0%.
- **Top-1 lemma accuracy**: token-weighted across ~1.55M tokens, roughly
  **84.8% → 92.5%** — the top-1 lemma **error rate is about halved** (15.2% → 7.5%),
  with per-corpus gains of +4 to +13 points. Since Round 15 the shipped default
  (learned + adaptive) adds a further **+7.2** on classical, **+4.5** on papyri,
  **+2.3** on the LXX, and +0.1–0.5 on the NT-family corpora.

## Caveats

- **"Before" for top-1 is "raw Morpheus order",** measured on the current stemlib; the
  pure forked analyzer was a touch lower still (SBLGNT 86.7 at fork-time toolkit).
- **LXX and the LXX/AF/PG tables are corpus-trained**, so their agreement numbers
  measure domain consistency, not absolute accuracy. The two PROIEL corpora are
  independent gold and show the same magnitude of gain, which is the strongest
  evidence the ranking is real and not convention-fitted.
- **POS is the weak dimension** (~74–85%), because Morpheus collapses
  noun/adjective/pronoun/article into `N`; lemma accuracy is the headline.
- **PapyGreek numerals**: the opt-in `--numerals` table resolves 1,416/1,454 numeral
  tokens (the Round 14 lowercase α/ε gap is fixed); bare-letter numeral *false hits*
  remain deliberately out of scope.

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

The whole table (raw → adaptive-selected frequency ranking → learned, plus coarse POS,
with bootstrap CIs and a tolerance gate) is reproducible in one command — the shipped
defaults:

```bash
MORPHGNT_DIR=/path/to/morphgnt AF_CORPUS_DIR=/path/to/apostolic-fathers/data/morph \
AGLDT_DIR=/path/to/agldt/v2.1/Greek/texts PROIEL_DIR=/path/to/greek-nt.conll \
    .venv/bin/python scripts/benchmark.py --bootstrap 300
```

(`--no-learned --no-adaptive` reproduces the old frequency-only default; `--no-gate`
skips the threshold comparison for such diagnostic runs.)
