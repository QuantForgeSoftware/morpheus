# Active plan — Round 8: new corpora (items 1–3 approved)

Round 7 (Apostolic Fathers) is complete and committed (`d760a3e`, `259df21`,
`23b33d3`, `b3707de`); its full record lives in [completed.md](completed.md).
User approved items **1–3** ("Do round 8"); item 4 (classical AGLDT) was
explicitly optional and is **not** being done. Working files go in
`tmp/<corpus>/` (git-ignored).

## Context: where Morpheus stands, and what "improve" can still mean

The Greek biblical side is near saturation: LXX 99.81% coverage (Round 2), NT
~95% top-1 after the name additions, AF 99.35% / 96.6–97.4% lemma (Round 7).
Remaining levers found in corpus research (2026-10-11):

**Key caveat — most Perseus "morph texts" are circular.** Celano's OGA/OLA
treebanks (45M Greek / 17M Latin words; the data behind morph.perseus.org) were
auto-annotated *with Morpheus* (LemmatizedAncientGreekXML). They cannot serve as
independent gold for improving Morpheus — at best a scale benchmark or POS-bigram
source. The valuable resources are the **manually curated treebanks** and a few
independent lemmatized corpora:

| corpus | size | annotation | license / access | improves |
|---|---:|---|---|---|
| **PapyGreek Treebanks** (Helsinki; Zenodo `10.5281/zenodo.5074307`) | 44K tokens, documentary papyri ca. 300 BCE–700 CE (Zenon archive letters, petitions) | semi-manual + reviewed, dependency-morphosyntax; TEI XML | CC BY-SA 4.0, free | **new Koine domain** — first test of Morpheus on papyrological Greek; safe stemlib additions from human-reviewed gold |
| **PROIEL greek-nt** (Tischendorf 1869) | 140,763 tokens | fully manual morphosyntax + info structure; PROIEL XML **and CoNLL-X** | CC-BY-**NC**-SA 3.0, GitHub (`syntacticus/syntacticus-treebank-data`) | independent second NT gold — validates how much of our SBLGNT-based NT numbers are robust vs convention-fitted (some sections unannotated: HEB 13, catholics) |
| **PROIEL latin-nt** (Jerome's Vulgate) + caes-gal/cic-att/per-aeth/pal-agr | ~113K tokens total | manual; CoNLL-X available | CC-BY-**NC**-SA 3.0, GitHub | first benchmark of the **Latin analyzer** (this checkout ships a full Latin stemlib — ~286K source lines — that has never been measured) |
| **AGLDT / Perseids v2.1** (`PerseusDL/treebank_data`) | Greek ~190K words (Homer, Hesiod, Aeschylus, Sophocles, Thucydides 1, Aesop); Latin: Caesar, Cicero, Ovid, Petronius, Vergil… | manual by 200+ annotators; free on GitHub | open | classical register — expands/validates both languages beyond the biblical domain |
| **Index Thomisticus** (Busa) | 11M lemmatized words, medieval Latin | classic lemma+POS per word; plain text at corpus.thomisticum.org (+ treebank subset) | free | large-scale Latin frequency table source |
| OGA/OLA/GLAUx (Celano 2024) | 45M / 17M words | **auto, Morpheus-derived** → circular | open | not gold; scale benchmark only |
| TLG | huge | subscription; abridged untagged | paid | skip unless user has access |
| Hebrew (OSHB/SBLHBT) | — | — | free | N/A — this checkout has no Hebrew component |

No large freely available *patristic* tagged corpus exists (the AF repo remains
the main one); PapyGreek is the closest new-domain gold in the user's register.

## Round 8 plan (checkable)

1. **PapyGreek round** — ✅ complete, see review below.
2. **Latin benchmark round** — ✅ complete, see review below.
3. **PROIEL Greek NT cross-validation** — ✅ complete, see review below.

## Review (Round 8, item 2: Latin benchmark + AGLDT frequency table) ✅

**First-ever measurement of the Latin analyzer.** Evaluator:
`tmp/latin/eval_latin.py` (`MorpheusRunner(language="latin")`; PROIEL UPOS mapped to
lenient Morpheus classes; Morpheus's `#N` homonym markers stripped on both sides).
Gold: PROIEL CoNLL-X (CC BY-NC-SA 4.0 → measurement/docs only, nothing committed).

| corpus | tokens | coverage | top-1 raw | top-1 ranked (AGLDT) | POS raw→ranked |
|---|---:|---:|---:|---:|---|
| latin-nt (Vulgate) | 110,774 | **98.4%** | 81.1% | **90.5%** (+9.4pp) | 78.3→81.9 |
| caes-gal | 27,397 | 96.9% | 74.3% | **85.1%** (+10.8pp) | 74.4→78.0 |
| cic-att | 45,580 | 97.1% | 78.0% | **86.5%** (+8.5pp) | 72.9→75.1 |
| per-aeth | 17,554 | 94.7% | 74.8% | **83.8%** (+9.0pp) | 73.8→78.2 |
| pal-agr | 11,979 | 97.5% | 75.5% | **85.2%** (+9.7pp) | 71.7→74.3 |

**Table source — license resolution.** Index Thomisticus Treebank is CC BY-**NC**-SA
3.0 (the Digital Classicist wiki footer's "CC BY" is wrong; the project site states
NC-SA), and corpusthomisticum.org offers no clear bulk-download license → rejected.
**AGLDT v2.1 (`PerseusDL/treebank_data`) is CC BY-SA 3.0 US — commit-safe**, and its
Latin files carry manual lemma annotations (`<word form=… lemma=… postag=…/>`,
Perseus-style trailing homonym digits). Built from all 11 Latin treebanks (Caesar,
Cicero, Propertius, Sallust, Vergil Aen. 6, Ovid, Phaedrus, Augustus *Res Gestae*,
Suetonius, Tacitus, Jerome's Apocalypse): **6,052 lemmas / 55,409 tokens** → bundled
as `python/morpheus_toolkit/data/lemma_frequencies_latin.json` (attribution in the
file; editorial artifacts like `-que`/`heu!` filtered).

**What holds up.** The four classical corpora share *no* text with the table, yet
top-1 rises +8.5 to +10.8pp — ranking generalizes across Latin registers exactly as
the Greek tables did (item 3's +12pp transfer). The Vulgate row is only partially
circular: the table contains Jerome's complete Apocalypse and PROIEL latin-nt shares
**2.85%** of its tokens with it in 10-word sequences — negligible, and even so the
non-circular AGLDT table (90.5) beats a *fully* circular PROIEL-derived one measured
earlier this round (88.3).

**The `#` homonym-marker fix.** Morpheus's Latin stemlib disambiguates irregulars
with `#N` (`sum#1`, `edo#1`, `quis#2`) and the parser kept them in lemma variants,
so frequency lookups for the most common words in Latin (est→sum) silently missed.
`normalize_lemma()` now strips trailing `#`/digit runs (Greek lemmas contain neither
— zero occurrences in all bundled tables; A/B re-run of the AF evaluation with and
without the change is **byte-identical**). Re-running the circular PROIEL table under
the new normalization: 88.3 → **91.5** — the fix alone is worth ~+3pp on the Vulgate.

**Decisions.**
- Table carries plain frequencies only, no joint lemma×POS counts: Morpheus's Latin
  analyzer cannot separate adjectives from nouns (both surface as `N` unless a special
  stem type fires), while AGLDT tags them separately — joint counts would systematically
  demote correct readings. (A future joint table should be derived from Morpheus's own
  output on a large corpus, self-consistent by construction.)
- Not auto-loaded: `Morpheus(language="latin")` still ranks with the Koine default
  unless frequencies are passed — same pattern as the LXX/AF tables. Wiring it in is an
  open question for the user (see below).
- No stemlib changes from this item; coverage gaps (94.7–98.4%) are a separate, larger
  effort (the Latin stemlib predates these corpora's rare forms) — candidate Round 9.

## Review (Round 8, item 3: PROIEL Greek NT cross-validation) ✅

**Dataset**: `syntacticus/syntacticus-treebank-data` (cloned to `tmp/proiel/`,
git-ignored) → `proiel/greek-nt.conll`: Tischendorf 1869, fully manual
annotation, **132,366 word tokens** (the CoNLL-X export omits the unannotated
HEB 13 + Catholic epistles; XML has 140,773). License CC BY-NC-SA 4.0 →
measurement/docs only; nothing PROIEL-derived is committed.

Evaluator: `tmp/proiel/eval_proiel_nt.py` (CoNLL-X reader; gold = col 3 lemma,
col 4 UPOS with a lenient class map; SBLGNT-style `#1` homonym suffixes and
`οὕτω(ς)` optional-parens normalized before comparison).

| metric | value |
|---|---:|
| coverage | **99.6%** (492 misses) |
| top-1 lemma, raw Morpheus order | 78.0 / 79.3 exact/acc-insens |
| top-1 lemma, ranked with NT tables | **90.7 / 91.7** |
| POS coarse | 81.6% (n=130,209) |

**What holds up**: the SBLGNT-trained frequency table transfers **+12pp** to a
text it never saw — ranking is robust, not convention-fitted. The gap vs our
SBLGNT numbers (~95%) decomposes as:
- **Lemma-convention differences (~3,100 tokens ≈ 2.4pp)**: PROIEL heads the
  pronoun families at the plural (ὑμεῖς/ἡμεῖς) where SBLGNT/Morpheus use the
  singular (σύ/ἐγώ); PROIEL lemmatizes εἶπεν to λέγω where Morpheus keeps the
  reduplicated aorist εἶπον as its own lemma. Convention-adjusted top-1
  acc-insens ≈ **94%**.
- **True residual errors (~7.9pp before adjustment)**: dominated by known
  homographs — ὡς→ὅς ×455, εἰ→εἰμί ×329, ἢ→εἰμί ×326, τε→σύ ×213,
  ὃ/ἃ→ὁ ×~280 — the same Round-6 residual profile (not patched there for
  overfitting reasons; confirmed here to be stable across independent gold).
- **Misses (492)**: 148 are names, mostly edition spelling/case conventions —
  PROIEL lowercases σατανᾶς as a common noun while the stemlib entry is
  uppercase-only (Σατανᾶς resolves fine); PROIEL spells Elijah Ἡλίας (iota)
  where SBLGNT has Ἠλίας (eta, which resolves). The rest are loanwords/dialectal
  one-offs (ῥαββεί ×15, ὡσαννὰ, …).

**Decision**: no stemlib changes from this item — the findings are convention
differences between two human-annotated editions of the same text, and adding
PROIEL's spellings would change NT behavior (out of scope per user direction)
and commit NC-SA-derived content. Numbers documented here only.

## Review (Round 8, item 1: PapyGreek) ✅

**Dataset**: Zenodo `10.5281/zenodo.5074307` → `tmp/papygreek/ezhenrik-papygreek-treebanks-b87127c/`
(394 documentary + 1 literary ALDT v1.5 XML; **42,313 Greek tokens**; CC BY-SA 4.0).
ALDT dual layers: input = `form_orig` (editorial markers stripped), gold =
`lemma_reg`/`postag_reg`. POSTAG is 9 chars — pos person number tense mood voice
**GENDER CASE** degree (gender before case, opposite of MorphGNT; lowercase).

**Evaluator**: `tmp/papygreek/eval_pg.py` (+ `missdump.py`) — coverage, top-1
before/after ranking (raw order via `runner.analyze_beta(ignore_accents=True)`,
not the pre-ranked API), coarse POS, miss profile. The marker inventory was
expanded after a full corpus audit: beyond ∼∽∤⋰⋱⸢⸣❨❩`<>[]{}()` + U+0324 and
`|num:N|`/`|g:…|` spans, the corpus also uses 〚〛 (×310), `?` (×81), ⊢⊣ (×50),
⸌⸍ (×37), ⎴⎵/⦑⦒ (×22), …, -, ⸜⸝, ⧼. The apostrophes ʼ ’ are real elision marks
(kept); combining diacritics ͂ ͅ are Greek letters (kept).

**Baseline → after stemlib additions** (36,455 word tokens; numerals tracked
separately — Morpheus has no numeral support and alphabetic numerals collide
with real words; documented limitation, not added to the stemlib):

| metric | baseline | after round-8 additions |
|---|---:|---:|
| coverage | 89.4% (old marker set) / 89.9% (fixed) | **92.9%** |
| misses | 3,871 (marked 1,878; numerals 863/1,454) | 2,600 (marked 1,417; numerals 853/1,454) |
| top-1 lemma, NT tables | 78.3 / 80.0 exact/acc-insens | **81.2 / 83.3** |
| top-1 lemma, PG tables | 80.5 / 81.8 | **83.7 / 85.1** |
| POS coarse | ~80–82% | 81.1 (NT) / 81.7 (PG) |

Remaining misses are dominated by irreducible damage: 1,417 marked forms whose
editorial reconstruction is partial, plus the 853 numeral tokens.

**Stemlib additions** (all additive; verified against the rebuilt indexes):
- `stemsrc/nom.papyri` — generated by new `scripts/build_papyri_stemlib.py`
  (mirrors Round 2's builder: missed nominal tokens with capitalized gold lemma,
  count ≥ 2 threshold since papyri carry more scribal noise; dictionary-form
  recognition check; idempotent managed-section merge). **179 names / 407 forms**
  — Egyptian deity/month/personal names (Θωθ, Ἰσις, Ἀμμώνους, Παῦνι, Ἐπείφ,
  Θερμουθᾶς, Τῦβι…), plus a curated section: papyrus dative-plural pronoun
  spellings ὑμεῖν→σύ / ἡμεῖν→ἐγώ and the Egyptian loanword κίκιος→κίκι.
  EXCLUDE: Ἀχιλλᾶς, Ἰωνᾶ (declined forms of known names used as lemmas —
  Morpheus already parses both correctly).
- `stemsrc/vbs.papyri` — hand-curated explicit `:vb:` entries for dialectal verb
  forms the generative paradigms don't produce: reduplicated aorists of
  λαμβάνω (ἰλήφασι ×15, ἔλαβα/ἐλαβα, εἴληφαν — standard Attic!, αἴλαβα),
  -εισκ-/-οσκ- presents and -ιν infinitives of γιγνώσκω, -ιν/-εριν infinitive
  variants of χαίρω. **15 forms / ~75 tokens.** Makefile's vbind rule now lists
  the file (and gained explicit prerequisites — fixes the stale-target trap).
- `stemsrc/nom.elided` — added ἐγ→ἐκ (×16 in papyri) alongside Round 7's 13.

**Bundled table**: `python/morpheus_toolkit/data/lemma_frequencies_pg.json`
(3,913 lemmas; punctuation/junk filtered; source label "PapyGreek Treebanks
v1.01 (CC-BY-SA 4.0)" — bundling is license-fine, SBLGNT precedent). The PG
table beats the NT tables by +2.5pp exact top-1 on papyri (83.7 vs 81.2) —
domain tables matter for disambiguation, not just coverage.

**Verification**:
- Every new form resolves with its gold lemma (`analyze_beta`, both modes);
  accented forms also hit in default mode; unaccented variants only under `-n`
  (CheckGenWords accent-exact gate — expected).
- Index key diff vs Round 7: nomind +362 keys / vbind +13, **zero collisions**
  with pre-existing keys → purely additive.
- AF guard: main-config snapshot (`ev2_af.txt`) re-runs **byte-identical**; the
  `--joint` config shows a ±0.5pp POS shift that reproduces on a *pristine*
  Round-7-source rebuild too — endtable regeneration noise (see lessons), not
  caused by these additions. `ev2_af_full.txt` snapshot refreshed to match.
- LXX guard: full driver re-run over all 64 books / 623,685 tokens with the
  Round-7 convention flags → **one token differs** (elided μετ' now correctly
  P/META/ instead of a junky N reading — an improvement from endtable drift).
- pytest 33/33.

## Decisions / open questions for the user

All three approved items are complete. Open questions:

1. **Push morpheus origin/master** — now 7 commits ahead of `75fface`
   (`d760a3e`, `259df21`, `23b33d3`, `b3707de`, `35e2074`, `a2b7a77` + this round's)?
2. **Push the AF repo's `morpheus-analysis` branch** (`2b51d98`)?
3. **Auto-load the Latin table?** `Morpheus(language="latin")` currently ranks with
   the Koine default unless frequencies are passed (same pattern as LXX/AF tables).
   Wiring in `lemma_frequencies_latin.json` would make out-of-the-box Latin ranking
   work (+9pp top-1) — a behavior change, so left to your call.
4. **License comfort with CC-BY-NC-SA (PROIEL)** for anything that would be committed
   (items 2–3 keep PROIEL-derived tables out of the repo regardless; only AGLDT,
   CC BY-SA 3.0 US, is bundled).
5. **Migrate the Round 8 record to completed.md** and stop, or start a new round?
   Candidate Round-9 items: Latin coverage pass (94.7–98.4% → close the gaps),
   classical Greek AGLDT benchmark (item 4, never approved), joint lemma×POS table
   for Latin derived from Morpheus's own output.
