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

A third approach **does** measure positive on exactly the ambiguity plain frequency
can't resolve — function-word homographs whose reading depends on the neighbours
(ὃ → ὁ/ὅς, τε → σύ/τε, ἢ → εἰμί/ἠμί/ἤ/ἦ). `--homographs` (API:
`use_homograph_context=True`) re-ranks a token's candidates by P(gold lemma | form,
prev POS, next POS) from the bundled table `data/homograph_contexts.json` (644
forms; trained on SBLGNT + Apostolic Fathers + PapyGreek, all CC BY-SA — rebuild
with `scripts/build_homograph_contexts.py`). Context is the neighbours' own ranked
top-1 POS and resets at verse/sentence boundaries, so there is no train/test
mismatch. Measured on the shipped default (flag off → on): SBLGNT 94.7→**94.9%**,
Apostolic Fathers 90.2→**90.7%**, PROIEL Greek NT 92.2→**93.1%** — the gain transfers
to unseen text. On classical AGLDT it is 93.7→**93.3%** (the table is Koine/NT-trained;
classical usage of these function words differs), which is why it stays opt-in. Off by
default; with it off, behavior is byte-identical. Most of Morpheus's ambiguous forms
are in fact unambiguous in the gold (only 42/644 table forms have a split), so the
effect is small but real and positive on every corpus measured.

### Learned re-ranking

Learned re-ranking is **on by default for Greek** (`--no-learned`; API
`Morpheus(use_learned=False)`); with it off no model is loaded and behavior is unchanged.
It re-orders a token's candidates with a
small bundled model (`data/learned_reranker.json`) instead of plain frequency. It is a
per-token averaged perceptron trained on pooled commit-safe gold — SBLGNT + Apostolic
Fathers + **AGLDT v2.1 Greek** (CC BY-SA 3.0 US) — 385,758 analyzable tokens. Features:
lemma frequency and its *rank*, fine POS, stem type, **morphological feature values**
(person/number/tense/voice/case/gender/…), and POS interactions with the neighbouring
tokens' frequency-ranked POS. Most of what frequency ranking already gets right is
preserved (frequency is a feature); the model adds the signals frequency alone cannot
see. Rebuild with `scripts/build_learned_model.py` (add `--agldt-dir …`; `--agldt-limit N`
subsamples AGLDT to balance the pool against the Koine corpora).

Top-1 lemma, frequency ranking → learned (flag off → on):

| corpus | tokens | freq | learned |
| --- | ---: | ---: | ---: |
| SBLGNT (MorphGNT) | 137,554 | 94.6% | **94.7%** |
| Apostolic Fathers (all) | 63,222 | 90.1% | **90.3%** |
| PROIEL greek-nt (**independent**) | 132,366 | 91.7% | **92.2%** |
| AGLDT v2.1 Greek (classical, adaptive table) | 469,254 | 92.8% | **93.7%** |

Pooling the classical treebank into training is what makes the model strong on classical
text (+3.0pp over the Koine-only model, +1.0pp over frequency ranking with the classical
table) at the cost of a
~0.3pp Koine drift (within build noise; the larger, unbalanced pool cost ~0.7pp, hence
the `--agldt-limit` balance). It cannot resolve feature-level homographs inside one lemma
(e.g. εἰμί imperfect 3sg vs 1sg, which need lemma-level context).

### Adaptive domain tables

Adaptive table selection is **on by default for Greek** (`--no-adaptive-tables`; API
`Morpheus(adaptive_tables=False)`); caller-supplied `frequencies=` are never overridden.
It removes the need to hand-pick
the frequency table: it scores every bundled table against the input's candidate lemmas
(by their normalized rank inside each table) and uses the best fit. Verified selections:
SBLGNT→Koine, Apostolic Fathers→AF, AGLDT classical→classical, PROIEL Greek NT→Koine,
LXX→LXX, PapyGreek papyri→papyri. The
payoff of getting the register right is large:

| corpus | Koine table (fixed) | adaptive |
| --- | ---: | ---: |
| AGLDT v2.1 Greek (classical) | 86.6% | **92.8%** |
| Apostolic Fathers | 90.1% | **90.5%** |
| SBLGNT | 94.6% | 94.6% |

On classical text, automatic selection recovers **+6.2pp** over the Koine default (and
matches passing the classical table by hand). Inputs under 40 tokens keep the default
table.

### Confidence calibration

Reported `confidence` is a softmax over the ranker's scores, which are *ordering*
scores, not probabilities — so the raw softmax is badly scaled. A temperature per
score path (bundled `data/calibration.json`, fitted by NLL grid search on SBLGNT with
`scripts/calibrate.py`; `--learned` fits the learned path) now scales it:

- **frequency scores** (`--no-learned`): T=0.08, top-1 expected calibration error
  **0.208 → 0.142** on SBLGNT and **0.203 → 0.139** on the Apostolic Fathers;
- **learned scores** (the default path): the learned model's scores turn out natively
  calibrated — T=1.0, ECE **0.005** (SBLGNT) / **0.002** (AF), ~30× tighter than the
  calibrated frequency path.

Pass `temperature=1.0` to opt out; the value stays in `[0, 1]`.

### Convention profiles

`--profile morphgnt` (API `Morpheus(profile="morphgnt")`) selects a named output
convention from a registry (`morpheus_toolkit/profiles.py`). In practice Morpheus's
Unicode output already matches the MorphGNT/LXX dictionary-form convention — articles
are lemmatized under nominative `ὁ`/`RA`, personal pronouns under `ἐγώ`/`σύ`,
demonstratives under `οὗτος`/`ἐκεῖνος` — so the bundled article transform is
**idempotent**: it is a guard, and the registry is the extension point for
corpus-specific conventions. (The LXX `--base-lemmas` preverb-stripping is not a static
profile — it needs an analyzer-backed verb-resolution guard — and stays in
`build_morph_lxx.py`.)

### Performance and packaging

`Morpheus(jobs=N)` / CLI `--jobs N` splits analysis across N concurrent `cruncher`
subprocesses (alignment preserved because chunks are contiguous). On the Apostolic
Fathers this measures **3.06×** at `jobs=4` with byte-identical analyses.
`scripts/package.sh` builds a wheel into `dist/` locally, using only the build backend
(no external hosting). A design for a Unicode-native C input path — to remove the beta
round-trip entirely — is in [`../docs/unicode-native-input.md`](../docs/unicode-native-input.md).

## Recovery pre-pass (spelling variants and names)

Documentary and post-classical texts spell words in ways the stemlib does not know:
itacism (ὑγειαίνῃς for ὑγιαίνω), gemination, sandhi (μὲγ for μέν), dropped iota
subscripts, or an oblique form of a name the stemlib simply lacks (Δωρίωνος). The
recovery pre-pass (`--no-recovery`; API `Morpheus(recovery=False)`) fires **only on
tokens the stemlib could not analyze at all** and proposes candidates from two
rule-generated sources:

- **spelling variants** (`recovery.spelling_variants`) — bounded, closest-first
  orthographic normalization: vowel classes ι/ει/η/υ/οι/υι/ου, ε/αι, ο/ω;
  consonant classes τ/δ/θ, κ/γ/χ, π/β/φ; geminate simplification and doubling;
  documentary ο/οι, ει/ε, ζ/σ and μψ/ψ; the final -ν/-ς toggle including sandhi
  spellings (μὲγ → μέν); and dropped iota subscripts restored on single η
  positions — the accent-insensitive cruncher mode does not ignore the subscript,
  so ῃ forms match only when it is present. Every variant the stemlib analyzes is
  attached as a candidate with `proposed=True` and `recovered_from` naming the
  variant.
- **name candidates** (`recovery.name_candidates`) — case-ending → nominative rules
  for name-like surfaces (Δωρίωνος → Δωρίων, Ἀχιλλᾶτος → Ἀχιλλᾶς, Χοινώθμεως →
  Χοινωθμις). When the stemlib confirms a reading whose lemma matches the candidate
  (accents ignored), that reading is used; otherwise the rule-generated nominative
  is proposed directly as a synthetic `stemtype="proper"` analysis, re-accented
  from the active frequency table and capitalized to match the surface.

The pre-pass never touches tokens that already have candidates — their analyses are
byte-identical with it off or on — and proposals go through the regular ranking, so a
proposal can only win when ranking justifies it. Measured on PapyGreek (all 36,455
word tokens; learned + adaptive defaults with the papyri table, `--numerals`; recovery
off → on):

| metric | off | on |
| --- | ---: | ---: |
| coverage | 95.1% | **99.2%** |
| top-1 ranked (exact / accent-insensitive) | 85.9 / 87.3% | **87.9 / 89.3%** |
| top-1 learned | 87.9 / 89.4% | **89.7 / 91.2%** |
| unanalyzed tokens | 1,781 | **296** |

The remaining misses are dominated by editorially marked or truncated forms (189),
numerals outside the bundled table (31), and rare technical vocabulary with no stemlib
entry. The 1,265 recovered forms split 390 spelling-only / 376 name-only / 499 from
both (exact top-1 hits among recovered tokens: 588 spelling, 134 name). Coarse POS
agreement reads 80.1% → 79.7% because the newly covered tokens enter
that metric's denominator and agree at ~70% — a completeness effect, not a regression
(coverage and top-1 can only rise: a miss has no candidates to lose). On clean literary
corpora the pre-pass fires on the few remaining misses and measures neutral-or-positive:
the LXX (623,685 tokens) reaches 100.0% coverage (99.81% before) with top-1 unchanged,
and on the gate corpora (SBLGNT, AF, AGLDT, PROIEL) every coverage/top-1 metric is
up-or-equal — AF's analysis rate rises 98.4% → 99.4%, which is also what moves its
coarse POS down slightly (the same completeness effect).

## The Septuagint (LXX)

Morpheus's Greek stemlibs carry a generated `nom.lxx` with ~4,500 proper names and
curated common words taken from a reference morphological analysis of the LXX, plus
explicit verb entries for inflections the generative paradigms miss. Against that
corpus (623,685 tokens) Morpheus now analyzes **100%** — 99.81% from the stemlib, and
the residual interjections and rare forms are resolved by the recovery pre-pass (on by
default). The stemlib entries are regenerated with
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

## Latin

The Latin analyzer (`language="latin"`, CLI `--language latin`) was benchmarked for
the first time in Round 8 against the PROIEL treebanks (CC BY-NC-SA — measurement
docs only, nothing PROIEL-derived is committed):

| corpus | tokens | coverage | top-1 raw | top-1 ranked | POS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vulgate NT (latin-nt) | 110,774 | 98.4% | 81.1% | **90.5%** | 78.3→81.9 |
| Caesar Gallic War | 27,397 | 96.9% | 74.3% | **85.1%** | 74.4→78.0 |
| Cicero Atticus letters | 45,580 | 97.1% | 78.0% | **86.5%** | 72.9→75.1 |
| Persius Satires | 17,554 | 94.7% | 74.8% | **83.8%** | 73.8→78.2 |
| Palatine Agricultural Poems | 11,979 | 97.5% | 75.5% | **85.2%** | 71.7→74.3 |

A bundled table `data/lemma_frequencies_latin.json` (6,052 lemmas / 55,409 tokens)
derives from the AGLDT v2.1 Latin treebanks — Caesar, Cicero, Propertius, Sallust,
Vergil, Ovid, Phaedrus, Augustus's *Res Gestae*, Suetonius, Tacitus and Jerome's
Apocalypse (PerseusDL/treebank_data, CC BY-SA 3.0 US). It lifts top-1 by +8.5 to
+10.8 points on all five corpora; the four classical ones share no text with the
table, so the gain is cross-corpus generalization, not memorization.

```bash
scripts/build_lemma_frequencies.py --format agldt \
    --corpus-dir /path/to/treebank_data/v2.1/Latin/texts \
    --out python/morpheus_toolkit/data/lemma_frequencies_latin.json
```

As with the LXX/AF tables, it is **not** auto-loaded by `Morpheus(language="latin")`;
pass it explicitly (`frequencies=...`) or use a script that does. The table carries
plain frequencies only — Morpheus's Latin analyzer cannot separate adjectives from
nouns (both surface as `N`), so joint lemma×POS counts would demote correct readings.
Latin lemmas in the stemlib carry `#N` homonym markers (`sum#1`);
`normalize_lemma()` strips them, which alone is worth ~3 points on the Vulgate.

## Classical Greek

Benchmarked in Round 9 against AGLDT v2.1 Greek (PerseusDL/treebank_data,
CC BY-SA 3.0 US): **469,254 word tokens** — Homer (~200K), Sophocles, Aeschylus,
Athenaeus, Herodotus, Polybius, Diodorus, Thucydides, Plutarch, Hesiod, Lysias,
Plato, Aesop, Homeric Hymns, Apollodorus.

| corpus | tokens | coverage | top-1 raw | top-1 ranked | POS |
| --- | ---: | ---: | ---: | ---: | ---: |
| **All** | 469,254 | **99.8%** | 79.9% | **91.4%** | 85.1% |
| Homer (epic) | 200,091 | 100.0% | 78.5% | 91.2% | 88.1% |
| Sophocles (tragic) | 40,851 | 99.8% | 75.8% | 88.9% | 83.7% |
| Thucydides / Herodotus (Attic/Ionic prose) | 51,127 | ~100% | ~82% | ~92% | ~77% |
| Diodorus Siculus | 23,037 | 99.9% | 86.2% | **95.4%** | 84.6% |

Two findings:
- The only systematic gap was **elision-mark encoding**: classical editions mark
  elision with a word-final combining comma above (U+0313, δ̓ = δέ), which the beta
  converter rejected — 34K tokens, mostly in Homer. `to_beta()` now maps a
  *word-final* U+0313 to the ASCII apostrophe Morpheus already recognizes; coverage
  went from 92.8% to **99.8%** with no stemlib changes (every elided form resolves
  through existing entries). Mid-word combining marks are untouched, and all
  committed gold corpora contain zero word-final U+0313.
- The residual misses (708 tokens, 0.15%) are editorial fragments and one-off rare
  names — no stemlib additions were made for them.

A bundled table `data/lemma_frequencies_grc.json` (21,889 lemmas / 476,401 tokens)
derives from the same treebanks; rebuild with:

```bash
scripts/build_lemma_frequencies.py --format agldt \
    --corpus-dir /path/to/treebank_data/v2.1/Greek/texts \
    --out python/morpheus_toolkit/data/lemma_frequencies_grc.json
```

As with the other domain tables it is not auto-loaded; pass it explicitly.
Cross-checked against PROIEL Herodotus (CC BY-NC-SA, measurement only): coverage
99.8%, ranked top-1 90.2% exact — the classical table beats the Koine one by +4pp
on that independent text.

**Training use.** The same AGLDT gold is pooled into the learned re-ranker (see Learned
re-ranking) and used to build a classical POS bigram model
(`scripts/build_pos_model.py --format agldt` → `data/pos_bigram_grc.json`). The classical
bigrams are the better choice for classical text *if* the Viterbi tagger is used (Homer
POS 87.3% vs 84.8% with the Koine bigrams), but the tagger still trails plain
frequency-ranked POS (85.2% on AGLDT) — the long-standing finding that the bigram
tagger doesn't pay off stands. (The `AGDT2`, `v2.0`/`v1.6`/`v1`, and `IGDS` trees in the
same repository are redundant or negligible; only `v2.1` is used.)

## Papyrus numerals

Papyri write numbers as bare Greek letters (β = 2, κθ = 90, λϛ = 36 …), and the
stemlib has no entries for them — in the PapyGreek treebank they are the single
largest miss family (853 of its 1,454 numeral tokens). `--numerals` (API:
`Morpheus(numerals=True)`) gives unanalyzed tokens a synthetic analysis from the
bundled table `data/papyrus_numerals.json` (50 forms; built from the PapyGreek
Treebanks' numeral gold, CC BY-SA — rebuild with
`scripts/build_papyrus_numerals.py`).

The flag fires **only on tokens Morpheus cannot analyze** and never overrides an
existing analysis: short betas like `ke`/`ka` also match real words under
accent-insensitive matching (and are real particles elsewhere), so overriding would
corrupt them. Synthetic analyses carry POS N and `proposed=True`. On PapyGreek the
flag lifts coverage 92.9% → **95.1%** and ranked top-1 lemma 83.7% → **85.9%**; a
handful of single-letter abbreviations (τ for ἀντί) get labeled as numerals — filter
on `proposed` if that matters. Off by default; with it off behavior is unchanged.

## Known limitations

- **POS granularity.** Morpheus tags nouns, adjectives, pronouns, articles and
  prepositions all as `N`; the stem type recovers most of them, but noun vs
  adjective remains ambiguous. POS agreement is therefore lower than lemma
  agreement.
- **Contextual ranking is experimental.** The hand-written context rules in
  `ranking.py` *hurt* accuracy and the POS-bigram Viterbi tagger in `tagger.py`
  merely matches frequency ranking; both are off by default. The exception is the
  homograph-context re-ranker (`--homographs`, see Ranking), which measured a small
  positive gain on every corpus tested — opt-in, Greek only. The learned
  re-ranker (see Ranking) is on by default for Greek (together with adaptive tables)
  and cannot separate feature-level readings inside one lemma.
- **Papyrus letter-numerals are misses** (β = 2, κθ = 90 …): the stemlib has no
  entries for bare-letter numerals. Enable `--numerals` to give unanalyzed ones a
  synthetic analysis from the bundled PapyGreek-derived table (see Papyrus numerals).
- **Coverage.** A small fraction of NT tokens gets no analysis, historically dominated
  by **biblical proper names** (Δαυίδ, Φαρές, Ἀμιναδάβ, …) absent from `stemlib`;
  coverage improved slightly after the LXX additions (`nom.lxx`) since many biblical
  names are shared. The recovery pre-pass (on by default; see Recovery pre-pass)
  resolves some of the remaining misses to stemlib-analyzed variants and
  rule-generated name nominatives. Enable
  `unknown_as_proper=True` (CLI: `--unknown-as-proper`) to give unanalyzed tokens a
  synthetic proper-noun analysis (lemma = surface, POS `N`/`NP`, flagged
  `proposed=True`). This brings the analysis rate to **100%** on both the SBLGNT and
  the Apostolic Fathers. ~6% of tokens are analyzed but with a different lemma than
  the gold corpus.

## Tests

```bash
cd python && ../.venv/bin/pytest -q
```
