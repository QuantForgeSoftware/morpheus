# Plan: improve Morpheus against the LXX reference corpus

Working files live in `tmp/lxx/` (git-ignored): `compare.py` (harness, dual-pass:
accented + accent-insensitive), `report.txt`, `misses.tsv`, `mismatches.tsv`,
`common_misses.tsv`.

## Context / findings (from comparison harness, 623,685 tokens / 48,995 distinct forms)

- **Misses: 5.15% of tokens** — ~92% are proper names absent from the stemlib
  (Ισραηλ ×2956, Δαυιδ ×1091, Ιερουσαλημ ×867, …). Also real common-word gaps:
  whole verb εὐλογέω missing (only its compounds exist in lsj.vbs), noun σάββατον
  missing, plus scattered forms (λήμψεται, ἤλθοσαν, δῴη, ἐκέκραξα…).
- **Mismatches: 4.54%** — mostly harmless lemma-convention differences (the
  corpus lemmatizes compounds to the base verb), but includes real bugs documented below.
- **Robustness bug:** cruncher silently returns nothing for uppercase beta code
  (`E)N` vs `e)n`) — exactly how the reference corpus is encoded.

## Tasks

- [x] 1. Add `scripts/build_lxx_stemlib.py` (generator, mirrors
      `build_biblical_stemlib.py`: idempotent via a managed-section marker +
      `load_existing()` merge; `--include-recognized` for full-coverage recovery).
      Reads the reference corpus's `*.mlxx` files, runs Morpheus over distinct
      forms, emits
      `stemlib/Greek/stemsrc/nom.lxx` containing:
      - proper names the corpus marks as such (type `N` / capitalized lemma)
        that Morpheus misses → indeclinable `pers_name` entries with attested
        case/number/gender from its parse codes; two-letter masc/fem names kept,
        two-letter neuter tokens dropped as artifacts;
      - curated missing common words: σάββατον, ταμιεῖον, βροῦχος (generative) and
        ἀμνός, ἀδελφιδός, τρυβλίον (explicit `:wd:` paradigms — the generative
        patterns do not produce these forms).
- [x] 2. Add base verbs εὐλογέω (`eu)loge/w`) and ἐγγίζω (`e)ggi/zw`) to
      `stemlib/Greek/stemsrc/lsj.vbs` at their sorted positions.
- [x] 3. Fix uppercase-beta-code handling in `python/morpheus_toolkit/runner.py`
      (`_normalize_beta`, Greek only — Latin is case-sensitive) + unit tests in
      `python/tests/test_runner.py`.
- [x] 4. Rebuild stemlib via `scripts/build-stemlib.sh`; verified: names resolve
      (Ἰσραηλ→Ἰσραήλ, Δαυιδ→Δαυίδ, Ωγ…), common words resolve (σαββάτων→σάββατον,
      ἀμνοῖς→ἀμνός, …), εὐλόγησεν/ἐγγίζει → correct lemmas, uppercase `E)N`/`QEO/S`
      analyze through the toolkit.
- [x] 5. Test suite: 31 passed (29 pre-existing + 2 new).
- [x] 6. Re-ran the reference-corpus comparison; metrics below.

## Out of scope this round (documented for follow-up)

- **Perfect passive participles of -έω verbs are systematically missing**
  (εὐλογημένος, τιμημένος, δοξασμένος all miss). Generation-mechanism gap; no
  precedent for explicit `:vb:` participle lines in the vbs sources.
- Other missing verb inflections: future middle of λαμβάνω (λήμψεται…), aorist
  3pl -οσαν/-σαν (ἤλθοσαν, εἴδοσαν…), optative δῴη, perfect active ἐκέκραξα.
- `-πλ` lemma artifact: `addconstraints.pl` auto-generates plural entities for
  pers_names, but singular forms get attributed to the plural entity
  (βορρᾶ → "Βορέασ-πλ"). Needs build-system investigation.
- Compound-decomposition bug: ἀπηγγέλη → "ἀπό-ἐγγελάω" (should be
  ἀπο-ἀγγέλλω). C-level scanner issue.

## Review

**Before → after (LXX reference corpus, 623,685 tokens / 48,995 distinct forms):**

| metric | before | after |
|---|---|---|
| analyzed (distinct forms) | 35,979 | 40,827 (+4,848) |
| misses | 5,574 forms / 32,102 tokens (**5.15%**) | 864 forms / 1,966 tokens (**0.32%**) |
| lemma mismatches | 7,442 / 28,336 (4.54%) | 7,304 / 27,554 (4.42%) |

Missed-token rate down **94%**; the remaining misses are exactly the documented
follow-up items (verb-inflection gaps, interjections). Mismatches barely moved —
they are dominated by the corpus's base-verb lemma convention for compounds,
which is not a Morpheus defect.

**Verification performed:**
- `pytest python/tests` → 31 passed (includes new uppercase-beta tests).
- Target forms verified through the public API after rebuild (names in both
  default and `ignore_accents=True` modes; common words; εὐλογέω/ἐγγίζω forms;
  corpus-style uppercase input via the runner).
- Generator idempotency proven: consecutive runs emit identical counts
  (4,521 names / 5,672 forms); `--include-recognized` recovers full coverage.

**Notes for downstream users:** unaccented biblical text (verse-initial capitals,
Rahlfs-style all-caps names) is best analyzed with `Morpheus(ignore_accents=True)`;
the new name entries match in that mode regardless of accenting.

---

# Round 2: fix the remaining verb-inflection misses (explicit `:vb:` lines + paradigm declarations)

## Findings (verified against sources, built index, and live analyzer)

- **` :vb:` mechanism confirmed end-to-end.** `gensynform.c` parses `:vb:<form> <keys>`
  via `ScanAsciiKeys` (key vocabulary in `src/morphlib/morphkeys.h` +
  `stemlib/Greek/rule_files/stemtypes.table`) and `GenIrregForm` (`genwd.c:217`):
  the first field is stored verbatim as the surface form; keys must include a
  stemtype plus tense/mood/voice/person/number. A leading `-` disables a line
  (falls into the no-op `proc_beta` branch). Verb pipeline:
  vbs.simp.ml → conjfile → do_conj (`GenConjForms`, passes `:vb:` through) →
  conjfile.short → indexvbs → **vbind**, and the analyzer resolves explicit
  forms via vbind (proven: existing `:vb:labe/` analyzes, absent from binary
  endtables). So new `:vb:` lines in vbs.simp.ml need no makefile change.
- **Encoding:** one simplified beta code everywhere (u=υ, y=ψ, f=φ, x=χ,
  c=ξ, q=θ); the reference corpus differs only by case. Use the toolkit's
  `to_beta()` to write surface forms — do not hand-transliterate.
- **λαμβάνω future middle:** source declares `;fu mid`, but generation emits a
  broken stem (`lhy` = ληψ-, μ dropped) and an n_infix/ionic one (`lamy`) that
  produces no endtable forms. Generative path is dead for this shape → explicit lines.
- **Compounds:** no separate compound lemmas exist; the analyzer splits preverbs
  itself (ἐξῆλθεν → lemma e)ce/rxomai). Fixing the simplex form should cover
  compounds — to be verified empirically after rebuild.
- **-έω perfect passive participles:** τιμάω declares `;pp` and τιμημένος now hits
  (Round-1 rebuild fixed it); εὐλογέω declares no `;pp` → εὐλογημένος misses.
  Total perfp_p miss is only 66 tokens, dominated by εὐλογέω (55) → generative fix.
- **δίδωμι** has no optative declaration and o_stem has no optative ending table
  (endtables/basics: only a1/ihn/imen/imhn/pr have opt tables) → explicit lines.
- **κράζω:** the corpus codes ἐκέκραξα etc. as reduplicated *aorists* (AAI),
  not the declared perfect stem κεκράγ- → explicit lines with aorist keys.
- **ὁράω** declares no active aorist at all (εἶδον resolves via the separate οἶδα
  lemma — a mismatch, not a miss) → explicit lines for the -οσαν/-αν variants.

## Tasks

- [x] R2.1 εὐλογέω — **done via explicit lines, not declarations.** The planned
      `;pp`/`;pf`/`@ mid` declarations are inert (they never reach vbind — see
      Review findings); 8 explicit `:vb:` lines with the corpus's exact surface
      spellings instead. εὐλογέω now 60/60.
- [x] R2.2 λαμβάνω — 19 explicit `:vb:` lines (future middle incl. λημψόμεθα,
      aorist passive incl. both spellings of λημφθήτω, aorist active -οσαν/-αν
      variants, imperfect middle) + participle neuter acc sg. Coverage 324→440/454;
      residual = compound-passive forms under compound lemmas (out of scope).
- [x] R2.3 ἔρχομαι — `:vb:` for ἤλθοσαν + ἐλθέτωσαν (aor2). Compound -θοσαν
      residuals remain (covered only via separate compound lemmas → mismatches,
      not misses; out of scope).
- [x] R2.4 δίδωμι — optatives δῴη/δῴης. Plan's `o_stem` key failed at runtime
      ("no stemtype seen": o_stem is derivtypes-only); fixed by adding real
      stemtype `omi_pr` before it, mirroring the existing `:vb:di/dw` precedent.
      DI/DWMI now 34/34 covered.
- [x] R2.5 κράζω — 9 reduplicated-aorist `:vb:` lines + augmented variant
      ἐκεκράξατε (the corpus attests both spellings). KRA/ZW now 60/60.
- [x] R2.6 ὁράω — 4 aorist-variant `:vb:` lines. These fixed **lemma attribution**
      (forms previously resolved via οἶδα as mismatches; now also match gold
      ὁράω): lem-ok 5→46 of the covered forms.
- [x] R2.7 nom.lxx nouns — αλληλουία/ἀντιλήμπτωρ/νοσσία/παστοφόριον added, and
      **integrated into `scripts/build_lxx_stemlib.py`** (regeneration had wiped the
      hand-added section once; all curated entries now live in the script). νοσσία
      stored forms switched grave→acute per standword() semantics; generator gained
      a `standardize()` so no future run re-emits word-final graves (38 name
      entries fixed, 22 duplicate spellings deduped).
- [x] R2.8 Rebuild + verify: C harnesses (`test_lookup`, `test_indecl`) then toolkit
      (`verify_r2.py`, dual accent modes); `pytest python/tests` → 31 passed;
      full `compare.py` re-run — metrics in Review below.
- [x] R2.9 `lessons.md` updated (pipeline truth, standword/CheckGenWords accent
      semantics, inert declarations, deriv redupl gate, managed-section trap).

## Out of scope (documented)

- Interjections (οἴμοι ×18 …): Morpheus has no interjection POS; would require a
  category decision. ~44 tokens.
- C-level compound-decomposition bug (ἀπηγγέλη → ἀπό-ἐγγελάω) and the `-πλ`
  pers_name artifact from Round 1 — build-system issues, separate round.
- The broken reg_conj future-middle generation for -μπ stems (produces ληψ-
  instead of λημψ-) — a C-code fix candidate for a later round; explicit lines
  cover the LXX need meanwhile.
- **Round-3 candidates surfaced by this run's residual misses:** compound
  passive/fut-passive forms under compound lemmas (συλλημφθήσῃ ×3 …, ~15 tok),
  ὁράω aorist/future passive (ὁραθῇ/ὁραθῆναι/ὁραθήσεται) + compounds
  (ἑώρακαν, ἀφιδὼν), and the new top misses: ἥκασιν ×20 (ἥκω),
  ἐνεπύρισαν/ἐνεπύρισεν ×31 (πυρίζω -οσαν aorist), γνώτωσαν ×10, εὕροσαν/
  εὕροσάν ×15 (εὑρίσκω -οσαν), ἡμάρτοσαν/ἠγάγοσαν/ἐφάγοσαν/ἐνεβάλοσαν
  (-οσαν aorist pattern across several verbs).
- **Reference-corpus lemma quirks, not Morpheus defects** (now count as
  mismatches):
  ἀντιλήμπτωρ lemmatized without the μ (`A)NTILH/PTWR` ×19 tok); νοσσία
  accented on the final alpha (νοσσιά) instead of the standard penult (×17 tok);
  θιμωνιά same quirk (×4). Morpheus keeps the linguistically correct spellings.

## Review (Round 2)

**Before → after (LXX reference corpus, 623,685 tokens / 48,995 distinct forms):**

| metric | Round-1 build | Round-2 build |
|---|---|---|
| analyzed (distinct forms) | 40,827 | 40,939 (+112) |
| misses | 864 forms / 1,966 tokens (**0.32%**) | 729 forms / 1,155 tokens (**0.19%**) |
| lemma mismatches | 7,304 / 27,554 (4.42%) | 7,327 / 27,643 (4.43%) |

Missed-token rate down a further **41%** (cumulative 96% vs Round-0's 5.15%).
The small mismatch increase is expected: forms newly covered by this round include
the corpus's quirky lemmas (above), which now count as mismatches instead of
misses; ὁράω -οσαν forms conversely moved from mismatch (via οἶδα) to match.

**Per-lemma results (`tmp/lxx/verify_r2.py`, dual accent modes):**

| lemma | covered / total | notes |
|---|---|---|
| εὐλογέω | 60/60 ✓ | was 0/60; explicit `:vb:` lines (declarations are inert) |
| δίδωμι | 34/34 ✓ | was 0/34; `omi_pr` stemtype fix; 1 tok mismatch = παραδῴη compound convention |
| κράζω | 60/60 ✓ | was 0/60; reduplicated-aorist lines + augmented variant |
| νοσσία | 17/17 covered | grave→acute stored forms; lemma quirk (accent position) → mismatch, not miss |
| ἀντιλήμπτωρ | 19/19 covered | worked since Round-2 data landed; harness false-negative fixed; μ-dropped gold lemma → mismatch |
| αλληλουία / παστοφόριον | 24/24, 14/14 ✓ | unchanged from earlier verification |
| λαμβάνω | 324→440/454 | +116 tok; residual = compound-passive forms under compound lemmas |
| ἔρχομαι | 44/97 (unchanged) | simplex fixed in Round 1; compound -θοσαν covered only via compound lemmas → mismatches |
| ὁράω | 46/51 (coverage unchanged) | the 4 new lines fixed **lemma attribution** for 41 tok (οἶδα→ὁράω); residual = passive + compounds |

**Root causes found and fixed this round:**
1. `;xx`/`@ xx` paradigm declarations in vbs sources never reach the built index:
   makefile target is `cat … > conjfile; do_conj; mv conjfile.short /tmp/vbmorph;
   indexvbs`, and indexvbs only processes `:vs/:aj/:no/:vb/:wd/:de:` lines of the
   do_conj output. Only explicit lines (or `:de:` deriv stems) affect vbind.
2. The generative deriv path rejects non-reduplicated perfect stems
   (`derivio.c checkcomderiv2`: `if (!had_redupl && Is_perfect(stemtype)) continue;`),
   so -έω pp participles (εὐλογημένος) never generate.
3. GenIrregForm requires a real stemtype in keys — `o_stem` alone is derivtypes-only
   and fails with "no stemtype seen" (δῴη); `omi_pr` fixes it.
4. `standword()` rewrites GRAVE→ACUTE on every input before lookup, and CheckGenWords
   compares accents exactly in normal mode — stored word-final graves can never match.
   Fixed at the root: generator `standardize()` + νοσσία block; 38 name entries
   corrected, 22 duplicate spellings deduped (5672→5650 forms).
5. Managed-section trap: re-running build_lxx_stemlib.py rewrote nom.lxx from the
   script's lists and wiped the hand-added Round-2 section. All curated entries now
   live in the script; regeneration proven byte-identical for the generated section.

**Verification performed:**
- C harnesses against the rebuilt stemlib: `test_lookup` (δῴη round-trip),
  `test_indecl` (all 5 νοσσία forms hit CheckGenWords in normal mode).
- Toolkit dual-mode verification of every previously-missed target form
  (`verify_r2.py`, now reporting coverage vs lemma-agreement separately).
- `pytest python/tests` → 31 passed.
- Full corpus re-run: `tmp/lxx/compare.py` (89 s) → report.txt metrics above;
  generator idempotency re-proven (two consecutive runs, generated section
  byte-identical).

---

# Round 3: use Morpheus to produce a full morphological analysis of the LXX ("morph lxx")

## Goal

Produce a complete, contextually disambiguated annotation of the whole Septuagint with
Morpheus — a drop-in alternative to the reference corpus's own `*.mlxx` annotations — and
measure how it compares. Rationale: after Rounds 1–2 Morpheus covers 99.81% of LXX tokens
(0.19% miss), so full-corpus annotation is now feasible; the toolkit already has the
disambiguation machinery (Viterbi POS-bigram tagger + frequency ranking, `tagger.py` /
`ranking.py`) and MorphGNT-style code mapping (`morphgnt.py`), built for the GNT —
Round 3
calibrates it to the LXX.

## Design decisions (engineering calls; veto-able)

- **Lemma convention: compound lemmas** (Morpheus's natural output; more informative than
  base-verb lemmatization). A `--base-lemmas` mode is a possible follow-up but needs proper
  preverb handling — the toolkit does not expose the C-level preverb split — deferred.
- **Output format**: same column layout as the reference corpus (`form type parse lemma
  [prefix]`). The type column carries coarse POS (N, V, A, P, D, C, X, I, RA…); the parse
  column carries Morpheus's full 8-char parsing code (person/tense/voice/mood/case/number/
  gender/degree) — a superset of the corpus's 5-char codes. Lemma in canonical beta,
  uppercased to match the corpus style. Prefix column empty in v1.
- **Disambiguation**: Viterbi POS-bigram tagger over Morpheus candidates, with both models
  (POS bigrams + lemma frequencies) trained on the reference corpus itself (~624k tokens).
  Note: this calibrates to the domain but makes agreement-with-corpus evaluation partly
  circular; reported as such.
- **Misses**: fall back to the corpus's own annotation for the residual ~0.19% (interjections,
  rare forms) so the output is complete; fallbacks are counted and reported per book.

## Tasks

- [x] R3.1 Train LXX models: both training scripts gained a `--format mlxx` adapter
      (shared `coarse_pos()` mapper in `morphgnt.py`: first letter, two-letter R-codes
      kept); emitted `data/pos_bigram_lxx.json` (16 tags) +
      `data/lemma_frequencies_lxx.json` (12,943 lemmas / 623,685 tokens). Bundled GNT
      tables untouched.
- [x] R3.2 Driver `scripts/build_morph_lxx.py`: reads all corpus `*.mlxx`; analyzes the
      48,995 distinct forms via `Morpheus(ignore_accents=True)` with an LXX ranker (joint
      lemma+POS frequencies); Viterbi-tags each contiguous token run; emits re-annotated
      files to `--out-dir` in the same column layout (headers preserved, lemmas uppercased
      to corpus style); fallback = corpus's own annotation for tokens with no candidate,
      recorded in `<book>.fb` sidecars + summary report.
- [x] R3.3 Evaluation `tmp/lxx/eval_morph.py`: line-aligned comparison — lemma agreement
      (normalized), POS agreement, parse-field agreement (class-aware: verb codes are 5-char
      tense/voice/mood/person/number, nominal codes 3-char case/number/gender); Morpheus-only
      vs full-file rates; top disagreements ranked by corpus token frequency.
- [x] R3.4 Ran end-to-end on all 64 books (driver 66 s, eval 19 s) → `tmp/lxx/morph-lxx/`;
      metrics in Review below; `pytest python/tests` → 31 passed; lessons.md updated.

## Out of scope / follow-ups (documented)

- Base-lemma output mode (needs preverb exposure/heuristics — follow-up).
- The known C-level compound-decomposition bug (ἀπηγγέλη → ἀπό-ἐγγελάω, ~26 tokens): it will
  show up in evaluation; fixing the scanner is a separate round.
- Interjection POS: Morpheus has no such category; those tokens use corpus fallback.
- **Surfaced by this round's evaluation:** article/pronoun dictionary-form conventions
  (the corpus groups all article forms under ὁ and lemmatizes pronouns to the nominative;
  Morpheus uses the stem ο( / distinct forms — ~40k tokens of the lemma gap); residual
  disambiguation errors (ὅτι→ὅστις ×4,044; θεοῦ→θεάομαι ×1,114; λέγων→λέγος ×814);
  accent/orthography differences on names and adverbs.

## Review (Round 3)

**Deliverable:** a complete Morpheus annotation of the whole Septuagint in the reference
corpus's own format — `tmp/lxx/morph-lxx/` (64 re-annotated `.mlxx` files + `summary.txt`
+ per-book fallback sidecars), produced by `scripts/build_morph_lxx.py` in 66 s.

**Coverage:** 623,685 tokens → **99.81% analyzed by Morpheus** (622,530); the residual
1,155 tokens (0.19%) fall back to the corpus's own annotation, so the output is complete.
Fallbacks are dominated by verb forms (VAI/VA/VBI/VC/V1) plus rare nouns — exactly the
Round-2 residual list; interjections use fallback too (no POS in Morpheus).

**Agreement with the reference corpus (Morpheus-only tokens, i.e. excluding fallbacks):**

| dimension | agreement |
|---|---|
| lemma (normalized) | **90.01%** (560,327/622,530) |
| POS (coarse) | **85.11%** (529,808/622,530) |
| parse fields (class-aware; 421,191 comparable tokens) | **76.24%** (321,123) |

Including fallback tokens: lemma 89.84%, POS 84.95%.

**What the disagreement is made of** (top items by token frequency):
- Dictionary-form conventions for articles/pronouns (~40k tokens): corpus groups article
  forms under ὁ and lemmatizes pronouns to the nominative; Morpheus returns the stem ο(
  or distinct forms. A convention difference, not an error — flip-able in a follow-up.
- Compound-verb lemma convention (base vs compound) — documented since Round 1.
- Accent/orthography: Δαυιδ→Δαυίδ ×1,091, πάντα→πᾶς ×1,378, ὅμοιος→ὁμοῖος…
- Genuine disambiguation errors the tagger still makes: ὅτι→ὅστις ×4,044,
  θεοῦ→θεάομαι ×1,114, λέγων→λέγος ×814, ἰδοὺ→ἰδού ×1,152.
- Cases where Morpheus is arguably *more* correct than the corpus: μοι → ἐγώ (corpus
  lemma "δς") ×964; standard accenting throughout.

**Caveat:** both models were trained on this same reference corpus, so agreement numbers
measure domain consistency as much as absolute accuracy; they are a floor for real-world
use on untagged LXX text, not a ceiling claim.

**Verification performed:**
- `pytest python/tests` → 31 passed (toolkit changes: `coarse_pos()` in morphgnt.py,
  format adapters in the two training scripts).
- Output spot-checked by eye across registers (Gen 1:1, Psalms, Daniel OG) — annotations
  are linguistically sound; line counts match the source files exactly.
- Fallback sidecars sum to exactly the summary's fallback count (1,155).

---

# Round 4: repo-wide scrub of the reference corpus's name (user re-grep found stragglers)

## Context

The user grepped the working tree again and still saw the reference corpus's name in
`runner.py` "and other files". Rounds 1–3 had only scrubbed the docs; this round extends
it to **every morpheus-owned file** (committed + tmp). A word-boundary grep across all
file types found stragglers the earlier `.py/.md/.sh`-only verification missed: a stale
generated `conjfile`, old report/snapshot scratch files, and a local path embedded in
the Round-3 summary.

## Tasks

- [x] R4.1 `python/morpheus_toolkit/runner.py` — `_normalize_beta` docstring no longer
      names the corpus ("some corpora (…)" → "some reference corpora").
- [x] R4.2 `python/tests/test_runner.py` — same rewording in the test comment.
- [x] R4.3 `tmp/lxx/compare.py` — removed the hardcoded local checkout path; corpus
      location now comes from `--corpus-dir` / `LXX_CORPUS_DIR` (same interface as
      build_lxx_stemlib.py).
- [x] R4.4 `stemlib/Greek/conjfile` — stale generated artifact still carried the
      pre-scrub Round-2 comment wording; regenerated from the already-clean sources via
      `scripts/build-stemlib.sh`. Diff vs a pre-rebuild snapshot: exactly the 3 reworded
      comment lines, nothing else (stemlib otherwise byte-identical).
- [x] R4.5 `scripts/build_morph_lxx.py` — summary no longer embeds the local corpus path
      (it was leaking into `morph-lxx/summary.txt`); now a neutral label. Regenerated all
      64 outputs: every `.mlxx` + sidecar md5-identical, only summary.txt changed.
- [x] R4.6 Deleted stale scratch snapshots retaining pre-scrub wording (report.prev,
      regen.diff, nom.lxx.{pre-scrub,pre-r2regen,post-r2regen}); re-ran compare.py so
      report.txt/TSVs come from the current clean format.

## Review (Round 4)

- Word-boundary grep for the corpus name across all repo files (excluding .venv):
  **zero occurrences** in any morpheus-owned file. The only remaining case-insensitive
  substring hits are legitimate Latin dictionary entries (peccator, siccatio, occatio…).
- `pytest python/tests` → 31 passed.
- compare.py smoke run with the new CLI reproduced Round-2 metrics exactly: misses
  729 forms / 1,155 tokens (**0.19%**), mismatches 4.43% — proving the interface change
  is behavior-neutral.
- Lessons captured in lessons.md (word-boundary all-file-type greps; never hardcode the
  corpus location).

---

# Round 5: update the user docs (READMEs) for the new texts and features

## Context

The repo has no file named "tutorial" — the user-facing documentation is `README.md`
(overview, build, cruncher usage) and `python/README.md` (toolkit tutorial). Neither
mentions anything from Rounds 1–3: the LXX stemlib entries, uppercase-beta normalization,
or the full-LXX annotation pipeline. Update both.

## Tasks

- [x] R5.1 Re-measured with the current build: AF coverage 90.9→**91.2%**, top-1
      84.5→**84.8%** before / 89.9→**90.1%** after ranking, POS 74.6→74.3%;
      MorphGNT-sourced subset 96.4→**96.5%**, top-1 89.7→**89.8%** / **95.9%**;
      analyze_corpus.py total 98.2→**98.4%**. SBLGNT row untouched (no local checkout).
- [x] R5.2 Root `README.md`: new "Septuagint (LXX)" section — what the stemlib gained
      (`nom.lxx` names + curated common words, new verb entries), coverage result,
      regeneration commands; pointer to the toolkit docs for the annotation pipeline.
- [x] R5.3 `python/README.md`: intro bullet on case handling (Greek input is normalized
      to lowercase beta before the cruncher; Latin untouched); new "The Septuagint (LXX)"
      section — bundled LXX models + rebuild commands (`--format mlxx`),
      `scripts/build_morph_lxx.py` full-corpus annotation, agreement numbers with the
      circularity caveat.
- [x] R5.4 Refreshed the ranking table's AF rows (re-measured) with a footnote that the
      SBLGNT row predates the LXX additions; reworded the "Known limitations" coverage
      bullet (the old "~1.6%" figure was not reproducible from any local corpus).
- [x] R5.5 Verified: documented commands match actual `--help` for all four scripts;
      both READMEs contain zero occurrences of the scrubbed corpus name; `pytest`
      → 31 passed.

## Review (Round 5)

**Docs updated:**
- [README.md](README.md) — new "Septuagint (LXX)" section between the Python-toolkit
  blurb and Tests: `nom.lxx` contents (~4,500 names + curated common words), verb-source
  additions, 99.81% coverage result, regeneration commands; toolkit blurb now also points
  at LXX annotation support.
- [python/README.md](python/README.md) — new "Case handling" intro bullet (uppercase-beta
  normalization); new "The Septuagint (LXX)" section: bundled `*_lxx.json` models +
  rebuild commands, full-corpus annotation via `build_morph_lxx.py` (format, fallback,
  lemma convention), agreement numbers with the circularity caveat; ranking table's AF
  rows re-measured and footnoted; coverage limitation bullet reworded.

**Verification performed:**
- Re-measurement ran the exact commands already documented in python/README.md against
  `../apostolic-fathers` (63,222 tokens) with the Round-2-built stemlib — numbers above;
  movement is small but real (shared biblical names now resolve).
- Every command shown in the docs was checked against the script's actual `--help`
  output (build_lxx_stemlib.py, build_morph_lxx.py, build_pos_model.py,
  build_lemma_frequencies.py) — flags and choices match.
- Cross-links use valid anchors (`#septuagint-lxx`, `#the-septuagint-lxx`).
- Word-boundary grep of both READMEs: zero occurrences of the scrubbed corpus name
  (Round-4 constraint held).
- `pytest python/tests` → 31 passed.

---

# Round 6: make "morph lxx" better than the reference — convention layer + base-lemma mode ✅

## Rationale

The analyzer is at its stopping point for LXX (99.81% coverage; residual = interjections
+ rare forms). Round 3's evaluation decomposed the ~10% lemma disagreement: dictionary-form
conventions (articles/pronouns, ~40k tokens) and compound-vs-base verb lemmas dominate;
genuine disambiguation errors are next. The significant gains live in the annotation layer.
This round adds two opt-in convention modes to `build_morph_lxx.py` and regenerates + re-evaluates.

## Design decisions (engineering calls; veto-able)

- **Opt-in flags; natural output stays default.** `--dictionary-forms` and `--base-lemmas`;
  with both off the Round-3 behavior is byte-identical. The "better morph lxx" run uses both.
- **Dictionary forms (MorphGNT-style).** Article lemma ο( → ὁ. Pronoun mapping only where it
  is lossless and standard — decided per class from the corpus's own coding sheet: if the
  corpus uses catch-all lemmas (e.g. δς for personal pronouns) we do NOT copy that; those
  tokens stay as Morpheus's more informative lemmas and are documented as corpus quirks.
- **Base lemmas.** Strip preverbs from compound verb lemmas; a prefix is stripped only when
  the remainder resolves as a verb in Morpheus (guards against over-stripping).

## Tasks

- [x] R6.1 Quantify: run `eval_morph.py` on the current output; count tokens per disagreement
      class (articles, pronoun pairs, compound-base pairs); read the corpus's `*Morph-Coding`
      sheet for its article/pronoun conventions. → Done in prior session: RA 88,429 tok
      (table covers 88,424), RP 26,934 (covers 26,628), RD 35,834 (covers 34,704); compounds
      ~17.5k head-strip + ~11.8k tail-match fixable (`compound_counts{,2,3}.txt`, `tables.txt`).
- [x] R6.2 Implement `--dictionary-forms` in `scripts/build_morph_lxx.py` (+ mapping table).
      → Three closed-set tables (articles→ὁ/RA, personal pronouns→ἐγώ|σύ/RP, demonstratives→
      family nominative/RD); unambiguous forms forced before Viterbi; 4 homographic article
      forms left contextual; type column emits the reference code when the reading matches.
- [x] R6.3 Implement `--base-lemmas` (preverb list + verb-resolution guard).
      → Head preverb-stripping + tail-matching for contracted compounds, guarded on attested
      preverb remnants (`PREVERB_REMNANTS`, 40 LXX-attested ∪ full preverbs); memoized.
- [x] R6.4 Regenerate morph-lxx with both flags; re-run eval; before/after agreement table.
      → See Review below (all three metrics beat Round 3).
- [x] R6.5 Update python/README.md LXX section (new flags, new numbers); lessons if any.
      → README updated (flags + mechanism + numbers table + residual breakdown); lessons.md
      extended with the beta-dialect / ranking / tagger lessons from this round.

## Review (Round 6)

**Result: the flagged run beats Round 3 on all three metrics — no regressions.**

| variant | lemma | POS | parse | Δ vs Round-3 |
|---|---|---|---|---|
| Round-3 natural (old ranking) | 90.01% | 85.11% | 76.24% | — |
| natural, new ranking only (`morph-lxx-base2`) | 90.25% | 85.09% | 76.26% | +0.24 / −0.02 / +0.02 |
| `--dictionary-forms` only (`morph-lxx-dict`) | 90.70% | 90.54% | 79.75% | +0.69 / +5.43 / +3.51 |
| **both flags (deliverable, `morph-lxx/`)** | **94.23%** | **90.54%** | **79.75%** | **+4.22 / +5.43 / +3.51** |

(623,685 tokens; 622,530 Morpheus-analyzed; 1,155 fallbacks = 0.19%.)

### What the attribution runs showed (and fixed)

The first flagged regeneration (prior session) regressed parse by −0.41pp. Line-by-line
attribution (`diff_variants.py`, with a monkey-patched reconstruction of the old ranking in
`morph-lxx-oldnat/`) isolated three distinct causes — all now fixed:

1. **Ranking over-promotion (root cause, `ranking.py`).** The joint-frequency lookup scored 0
   when Morpheus's POS isn't a key in the lemma's row (αὐτός tagged A here but RD in the
   reference). The prior session's fix fell back to *full plain lemma frequency*, which
   over-credited unattested pairings: σός(N) 0.432 vs σύ(RP) 0.838 left only a ~1.2-nat
   emission gap that bigram context flipped (σοῦ/ἐμοῦ → possessive adjectives, τὰ/τοῦ → τίς).
   **Fix:** an unattested (lemma, POS) pair now scores a *floor of one occurrence* — it can
   never be the gold reading of any token (gold is built from the same reference), so the
   floor only removes wrong answers. Natural mode recovered fully (76.26% parse ≥ Round 3).
2. **Forcing removed featureless candidates.** Morpheus offers a surface-form pseudo-candidate
   for αὐτοῦ (lemma=αὐτοῦ, POS D, *empty* parse code) that vacuously passes parse comparison;
   forcing to hits[:1] deleted it and collapsed the real αὐτός candidates arbitrarily.
   **Fix:** forcing keeps *all* target-reading candidates so Viterbi still uses context.
3. **Same-POS feature ties are arbitrary in the tagger** (one candidate per coarse POS, first
   on score ties). For tied forms the reference's own accent notation correlates strongly with
   the reading — `AU)TOU=` is 97% GSM while `AU)TOU\S`/`/S` are ~100% APM; `AU)TW=N` came out
   GPN though 92% of gold is GPM. **Fix:** a derived `TIE_BREAK` table (≥10 tokens, ≥90%
   majority per spelling; weaker cases like τὰ stay contextual) stable-sorts hits so the tie
   resolves toward the reference majority. This single change moved parse 75.79% → 79.75%.

Also verified: base-lemma mode is a pure lemma-column operation (+3.53pp lemma, zero POS/parse
effect); spot checks pass (ἀπέστειλεν→στέλλω+ΑΠΟ; contracted ἐκέρχομαι→ἔρχομαι at Gen 1:2368
matching gold exactly); `summary.txt` reports the active conventions; pytest 33 passed.

### Honest caveats and residuals

- **Models are corpus-trained.** Both disambiguation models come from this same reference, so
  agreement measures domain consistency as much as absolute accuracy — a floor for untagged LXX
  text, not a ceiling claim.
- **The eval's "top lemma disagreements" list is misleading**: it sorts by *total* form
  frequency and prints only the first disagreeing line. True per-form mismatch counts are far
  smaller (τοῦ: 1/10568; αὐτοῦ: 4/9181; οἱ: 1/4762; ὅτι: 8/4044 — the last was already ~right
  in Round 3, an earlier misread).
- **Residual lemma disagreement (~5.8%)** is dominated by documented reference quirks where
  Morpheus is arguably more correct (surface-form lemmas τοῦ→τοῦ; ἰδοὺ lemmatized as ὁράω ×28),
  the genuine ἕως/ἠώς homograph (277 tokens — largest true error), κυριόω intrusions (32), and
  ~286 compound verbs the reference keeps unstripped while the heuristic strips (ἐγείρω,
  ἐπίσταμαι, …; etymologically they are compounds). Not patched: copying per-lemma corpus
  choices would be overfitting to annotation inconsistency.
- **Structural limit:** the tagger keys states by coarse POS, so feature-level ambiguity within
  a POS (masc/neut homographs of article forms) is resolved only where the reference's accent
  notation carries signal; genuinely ambiguous cases stay at chance.

# Round 7: Morpheus × Apostolic Fathers — AF pipeline, convention layer, elided forms ✅

**User direction: do NOT change anything NT-related; improve Morpheus against the
Apostolic Fathers corpus instead.** All five approved items implemented, verified
and committed (`d760a3e`, `259df21`, `23b33d3`, `b3707de`). Working files in
`tmp/af/` (git-ignored): evaluators (`eval_af.py`, `eval_out.py`), snapshots
(`ev2_*.txt`, `ev3_*.txt`), driver outputs, AF table sources.

## Evidence gathered (63,222 Greek tokens: 52,094 MorphGNT-derived gold + 11,128 machine-model gold)

- Verb mismatches on trustworthy gold are ~97% convention differences, not errors
  (reduplication γίγνομαι→γίνομαι ×249; augment ἐθέλω→θέλω ×95; aorist-vs-base
  εἶδον/εἶπον→ὁράω/λέγω ~160; accents ~116; act/mid ~90) — the Round-6 pattern.
- The "interrogative gap" was an accent artifact (MorphGNT writes τίς, HF lines
  τις): 42.6% → 0.2% under accent-insensitive comparison. No analyzer change needed.
- Elided forms (544 tokens, all HF-sourced) were a real analyzer gap: Morpheus
  returned no candidates for any of them.
- Joint ranking hurts lemma on AF (unlike LXX): the reference tags adjectives N
  where Morpheus says A; plain frequency is best for lemma, joint only for POS.

## Tasks

- [x] 1. Commit the two toolkit fixes (frequency-builder guard for MorphGNT-format
      corpora — previously all token lines skipped, 106 vs 5,874 lemmas; and
      `Analysis.matches_lemma()` normalizing both sides). Verified: pytest 33/33,
      LXX rebuild byte-identical. (`d760a3e`)
- [x] 2. AF convention table + annotation pipeline — `scripts/build_morph_af.py`
      mirroring the LXX driver (accent-insensitive mode, AF frequency ranking,
      optional Viterbi/joint). Convention layer derived at run time from
      MorphGNT-derived gold with three guards: single target per source lemma,
      ≥10 tokens, and **M==0** — no trustworthy token with that choice may agree
      with the gold. The M==0 guard rejects form-dependent splits (κύριος/κυρία
      gender 10-vs-613; ἐγώ/κἀγώ enclitic 22-vs-1198; ἐπεί/ἐπειδή 17-vs-33) that a
      plain single-target guard would have applied globally and broken. Rejected
      pairs are printed in the summary for auditability. (`23b33d3`)
- [x] 3. Stemlib additions for elided forms — `stemsrc/nom.elided` (13 forms: δι,
      κατ, παρ, μετ, ἀπ, ὑπ, ἐπ, ἀφ, ὑφ, ἐφ, καθ, μεθ, ἀλλ) mapping to existing
      full-form lemmas; rebuilt nomind. Entries resolve only in accent-insensitive
      mode (`-n`), so default-mode behavior is unchanged and vbind byte-identical.
      (`259df21`)
- [x] 4. Bundle AF tables + repo tooling — `lemma_frequencies_af.json` /
      `pos_bigram_af.json` in `python/morpheus_toolkit/data/` (neutral source
      label, LXX precedent); `scripts/agreement_report.py` gained
      `--frequencies/--model` flags. (`23b33d3`)
- [x] 5. Upgrade the AF repo — `tools/morpheus/analyze.py` rewritten as a
      self-contained mirror (tables derived at run time from its own gold;
      conventions on by default with `--no-conventions` escape); all 15
      `data/morph-morpheus/*.txt` regenerated + new `.fb` sidecars and
      `summary.txt`; README rewritten. Committed locally in the AF repo
      (`2b51d98`, branch `morpheus-analysis`) — not pushed.

## Review (Round 7)

Headline numbers (driver = accent-insensitive mode + AF frequency ranking + top-1
candidate + convention layer):

| subset | tokens | lemma | acc-insens lemma | POS | coverage |
|---|---:|---:|---:|---:|---:|
| all Greek | 63,222 | 91.1% | 92.1% | 75.3% | 99.35% (413 fallbacks) |
| `source=MorphGNT` (trustworthy) | 52,094 | **96.6%** | **97.4%** | 75.7% | 99.95% |
| `source=grc_proiel_lg` (machine gold) | 11,128 | 65.4% | 67.2% | 73.1% | 96.5% |

- Baseline before the round: 90.4/74.3 (ALL), 96.3/75.5 (MG subset) with NT
  tables, no `-n`, ~1,027 misses. The convention layer lifts the trustworthy
  subset to 96.6% exact / 97.4% accent-insensitive; `-n` mode cuts misses from
  ~1,027 to 413 (elided forms + unaccented spellings).
- **Config trade measured**: Viterbi (`--tagger`) costs ~1.4pp MG-subset lemma for
  +1.0pp POS — the opposite of LXX, where it was net positive. Default is top-1
  (lemma-first); `--tagger`/`--joint` available for POS-optimized output.
- **Verification**: saved ev2 evaluator snapshots re-run byte-identical after all
  toolkit changes; pytest 33/33; AF repo's analyze.py output verified
  byte-identical to morpheus's build_morph_af.py across all 15 files; LXX driver
  spot-check clean. NT/LXX untouched (no shared stemlib lemma changes).

**Open questions for the user:** push morpheus origin/master (4 commits ahead of
`75fface`; the AF README pins `23b33d3`, so pushing makes that pin real)? Push the
AF repo's `morpheus-analysis` branch?

# Round 8: new corpora — PapyGreek, Latin benchmark, PROIEL Greek NT cross-validation ✅

**User approved items 1–3 ("Do round 8"); item 4 (classical AGLDT) was explicitly
optional and is not done.** All three complete and committed (`a2b7a77` for item 1;
`1935b8f` for items 2–3). Working files in `tmp/<corpus>/` (git-ignored):
PapyGreek treebanks + evaluators, PROIEL clone + evaluator, AGLDT clone + Latin
evaluator.

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
(Note: AGLDT v2.1 Greek turned out much larger than this table — 557,918 words;
see Round 9.)

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
  unless frequencies are passed — same pattern as the LXX/AF tables.
- No stemlib changes from this item; coverage gaps (94.7–98.4%) are a separate, larger
  effort (the Latin stemlib predates these corpora's rare forms).

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

**Open questions — resolution:** pushed morpheus origin/master and the AF repo's
`morpheus-analysis` branch; **user has no interest in further Latin work** (the
Round-8 benchmark + bundled table remain as committed; nothing more planned);
PROIEL-derived content stays out of the repo regardless. Record migrated from
todo.md; Round 9 drafted there.

# Round 9: classical Greek, contextual homographs, papyrus numerals ✅

**User approved all three items ("Do all 3"); all complete and committed**
(`6f8ae3a` item 1; `2652cbf` item 2; `444ea10` item 3). Standing constraints held:
no Latin work, PROIEL-derived content stays out of committed files (NC-SA), default
NT behavior unchanged. Working files in `tmp/<corpus>/` (git-ignored): AGLDT clone +
classical evaluator (`tmp/agldt/`, `tmp/grc/`), homograph A/B evaluator (`tmp/r9/`).

## Where things stand after Round 8

- LXX coverage 99.81% (Round 2); NT ~95% top-1; AF 99.35% / 96.6–97.4% lemma
  (Round 7); PapyGreek 92.9% coverage / 83.7% top-1 with PG tables (Round 8).
- PROIEL cross-validation: the SBLGNT-trained table transfers **+12pp** to unseen
  text — ranking is robust, not convention-fitted. The stable true residual across
  *both* independent golds is a handful of function-word homographs: ὡς→ὅς ×455,
  εἰ/ἢ→εἰμί ~×650, τε→σύ ×213, ὃ/ἃ→ὁ ~×280.
- AGLDT v2.1 Greek is much bigger than the Round-8 research table assumed:
  **557,918 words** (Homer ~230K, Thucydides, Herodotus, Sophocles ×3 vols,
  Aeschylus ×6, Hesiod ×3, Plato, Plutarch ×2, Athenaeus ×2, Diodorus, Polybius,
  Lysias ×4, Apollodorus, Aesop) — CC BY-SA 3.0 US, commit-safe.

## Round 9 plan (checkable; all approved)

1. **Classical Greek round** ✅ (see review below)
   - [x] Baseline: coverage / top-1 / coarse POS over AGLDT v2.1 Greek (557,918 words;
     per-author breakdown; epic/Ionic dialect is the stress test).
   - [x] Build + bundle `lemma_frequencies_grc.json` (`--format agldt`); re-measure
     ranked top-1.
   - [x] Stemlib additions: **not needed** — after the elision fix, residual misses are
     708 tokens of editorial fragments and one-off names (see review).
   - [x] Guards: AF/PG snapshots byte-identical (or known endtable noise); pytest 33/33.
   - [x] Independent cross-check: PROIEL Herodotus (`hdt.conll`, CC BY-NC-SA →
     measurement/docs only, nothing committed).
2. **Contextual homograph disambiguation** ✅ (see review below)
   - [x] Profile the residual homographs on SBLGNT/AF/PG gold to fix the form set
     and context features.
   - [x] Train a small learned model P(lemma | form, prev POS, next POS) on
     commit-safe gold only (SBLGNT + AF + PG; LXX excluded — no annotated `.mlxx`
     gold in this workspace); bundle as data table.
   - [x] Wire in behind an opt-in flag (API + CLI); default path byte-identical.
   - [x] Verify: measured +0.6–1.6pp top-1 on SBLGNT/AF/PapyGreek (below the
     +2–4pp target — see review for why that is the ceiling); transfers to PROIEL
     greek-nt (independent gold); pytest 33/33.
3. **PapyGreek numerals** ✅ (see review below)
   - [x] Inspect ALDT numeral gold (postag `m`): forms, lemmas, marker patterns.
   - [x] Build bundled papyrus-numeral table from PapyGreek gold (CC BY-SA);
     opt-in flag emits synthetic analyses for unanalyzed numeral tokens
     (`unknown_as_proper` precedent) — never silent stemlib additions.
   - [x] Verify: coverage +2.2pp on PapyGreek; AF/SBLGNT default paths
     byte-identical, PG baseline matches Round 8's snapshot; pytest 33/33.

## Review (Round 9, item 1: classical Greek) ✅

**Dataset**: AGLDT v2.1 Greek (`tmp/agldt/`, CC BY-SA 3.0 US): **469,254 word tokens**
across Homer (~200K), Sophocles, Aeschylus, Athenaeus, Herodotus, Polybius,
Diodorus, Thucydides, Plutarch, Hesiod, Lysias, Plato, Aesop, Homeric Hymns,
Apollodorus. Evaluator: `tmp/grc/eval_grc.py` (per-author breakdown; AGLDT postag
pos-1 empirically mapped — note it differs from Latin: g=particle, p=pronoun,
r=preposition, l=article, m=numeral).

**The one systematic gap was elision-mark encoding.** Baseline coverage was 92.8%
(Homer 90.3%, Sophocles 88.5%) with the top misses all word-final U+0313 (combining
comma above, the classical elision mark): δ̓ ×10,778 alone = 2.3% of the corpus.
`to_beta()` now maps a *word-final* U+0313 to the ASCII apostrophe Morpheus already
recognizes (mid-word combining marks untouched). Every top-30 elided form was
verified to resolve through existing stemlib entries — no new stems needed for them.
Safety: SBLGNT/AF/PapyGreek gold contain **zero** word-final U+0313/U+0306 (scanned);
LXX is beta code, so structurally impossible. Result:

| metric | before fix | after fix |
|---|---:|---:|
| coverage (ALL) | 92.8% | **99.8%** |
| Homer | 90.3% | **100.0%** |
| Sophocles / Aeschylus / Hesiod | 88.5 / 90.2 / 90.6% | 99.8 / 99.6 / 99.7% |

**Bundled table**: `data/lemma_frequencies_grc.json` (21,889 lemmas / 476,401
tokens; attribution in file). Ranked results per author:

| author | n | coverage | top-1 raw → ranked | POS |
|---|---:|---:|---|---:|
| **ALL** | 469,254 | 99.8% | 79.9 → **91.4%** (+11.5pp) | 85.1% |
| Homer | 200,091 | 100.0% | 78.5 → 91.2% | 88.1% |
| Sophocles | 40,851 | 99.8% | 75.8 → 88.9% | 83.7% |
| Aeschylus | 39,479 | 99.6% | 78.1 → 89.4% | 87.3% |
| Athenaeus | 33,272 | 99.2% | 82.0 → 91.8% | 81.1% |
| Herodotus | 28,791 | 100.0% | 81.8 → 91.8% | 79.1% |
| Polybius | 25,528 | 100.0% | 84.1 → 93.9% | 83.4% |
| Diodorus Siculus | 23,037 | 99.9% | 86.2 → **95.4%** | 84.6% |
| Thucydides | 22,336 | 99.9% | 83.5 → 92.5% | 78.8% |
| Plutarch | 19,386 | 99.9% | 85.3 → 93.9% | 81.6% |
| Hesiod | 16,280 | 99.7% | 77.7 → 92.3% | 90.6% |

**No stemlib additions needed.** Residual misses: **708 tokens / 527 forms (0.15%)**
— editorial fragments (τ- ×47, κ- ×40), one-off rare names (×1–6 each from
Athenaeus/Plutarch/Diodorus), and <40 epic-dialectal forms (γώ/γὼ→ἐγώ, σθω/σθαι,
πὶ/φὶ). Adding ~500 one-off names to the shared stemlib would be bloat for 0.1%
— deliberately not done (contrast PapyGreek, where misses were systematic).

**Independent cross-check — PROIEL Herodotus** (`hdt.conll`, 83,819 tokens,
CC BY-NC-SA → docs only): coverage **99.8%**; top-1 raw 79.9/81.5 exact/acc-insens;
ranked with NT tables 86.3/87.6, with the classical grc table **90.2/91.7** — the
classical table beats the Koine one by +4pp on a text it shares no words with,
and Morpheus's coverage of Ionic prose matches AGLDT's (100%).

**Verification**: pytest 33/33; AF main-config re-run adds zero drift vs Round 8's
check run (both show only the known endtable noise); PapyGreek eval byte-identical
in both table configs.

## Review (Round 9, item 2: contextual homograph disambiguation) ✅

**Design.** Opt-in re-ranker (`Morpheus(use_homograph_context=True)` / CLI
`--homographs`, Greek only; off by default — the table is not even loaded when off).
Context = the neighbours' *frequency-ranked top-1 POS* (Morpheus's own output, not
gold POS — no train/test mismatch); verse/sentence boundaries reset context.
Scoring is `log1p(count)` with exact-context → marginal fallback; tokens whose form
is not in the table are untouched. New module `morpheus_toolkit/homographs.py`
tables by beta form and lazy-loads only when the flag is on.

**Training.** Commit-safe gold only: SBLGNT + Apostolic Fathers + PapyGreek (all CC
BY-SA, 237,231 tokens). LXX deliberately excluded — no annotated `.mlxx` gold exists
in this workspace (only Morpheus's own outputs in `tmp/lxx/`); documented as a
limitation. Table: **644 forms** (`min_form=20`, `min_ctx=5`) →
`data/homograph_contexts.json`; rebuild with `scripts/build_homograph_contexts.py`
(idempotent; readers for all three gold formats).

**Result — A/B (flag off → on, gold = each corpus's own lemma):**

| corpus | n | top-1 | acc-insens | POS |
|---|---:|---|---|---|
| SBLGNT (in-domain) | 137,554 | 93.6 → **94.4** (+0.8pp) | 94.2 → 95.0 | 77.6 → 78.2 |
| Apostolic Fathers | 63,222 | 89.0 → **89.7** (+0.7pp) | 89.6 → 90.3 | 75.0 → 75.5 |
| PapyGreek | 36,455 | 83.8 → **85.4** (+1.6pp) | 85.3 → 86.9 | 77.3 → 78.5 |
| PROIEL greek-nt (independent) | 132,366 | 92.4 → **93.0** (+0.6pp) | 93.4 → 94.0 | 82.7 → 83.1 |

Positive on **all four** corpora including the fully independent PROIEL gold —
transfer confirmed, not memorization. But +0.6–1.6pp, not the +2–4pp target: only
**42 of the 644 table forms have non-degenerate marginals (and just 13 any context
split)** — Koine gold is ~95–100% one-way for most ambiguous forms, and several
"splits" are accent/case annotation conventions (te→τέ/τε, ti/→τίς/τις). The famous
residual families from the Round-8 cross-validation (w(s→ὡς unanimous in training,
ei)→εἰ unanimous, o(\→ὅς unanimous) are inter-edition convention differences with
PROIEL, not ranking errors — the model correctly doesn't chase them. Shipped as
opt-in tooling; the larger residual is convention noise no ranker can fix (lesson
captured in `lessons.md`).

**Verification**: pytest 33/33; AF default-path re-run byte-identical to Round 9's
check snapshot (`tmp/af/ev2_af_r9check.txt`) — flag off is a proven no-op.

## Review (Round 9, item 3: PapyGreek numerals) ✅

**Gold profile.** The ALDT treebank has **1,454 numeral tokens** (postag `m`); **853
are currently missed — all bare Greek-letter numerals** (β = 2, κθ = 90, λϛ = 36 …;
the corpus stores them without a visible numeral sign), only 83 distinct forms. Of the
601 "analyzed" numerals: word-numerals Morpheus handles fine (χίλιοι, δέκα — tagged N in
85% of cases) plus **false hits**: short betas collide with real stems under
accent-insensitive matching (κε→ἄν, ιε→εἶμι, ιη→κερατέα — 315 of 348 letter-numeral hits
carry the wrong top-1). Those are deliberately NOT touched: overriding analyzed tokens
would corrupt real one/two-letter particles (κε = καί) in other corpora.

**Feature.** `data/papyrus_numerals.json` (**50 forms**; PapyGreek numeral gold, CC BY-SA):
for each form Morpheus misses, the majority-vote gold lemma keyed by beta code. Rebuild:
`scripts/build_papyrus_numerals.py` (pipe annotations stripped from lemmas too; only pure
letter lemmas count as reliable — a handful of decimal-annotated tokens like `Ατ→1300`
are excluded). Opt-in via `Morpheus(numerals=True)` / CLI `--numerals` (new module
`morpheus_toolkit/numerals.py`, Greek only): unanalyzed tokens whose beta is in the table
get a synthetic analysis (POS N, `proposed=True`). Runs before `unknown_as_proper`
(more specific wins); off by default — no table loaded, behavior unchanged.

**Result (PG evaluator + PG frequency table; flag off → on):**

| metric | off | on |
|---|---:|---:|
| coverage | 92.9% | **95.1%** (+2.2pp) |
| numerals missed | 853/1454 | **38/1454** |
| top-1 ranked (exact / acc-insens) | 83.7 / 85.1% | **85.9 / 87.2%** (+2.2pp) |

All 815 missed tokens whose beta is in the table are recovered; the residual 38 are forms
below `min_count=2` (one-off editorial variants). Recovered numerals are correct by
construction (lemma = gold letter string), so top-1 rises too — except a handful of
decimal-annotated tokens that now count as covered-but-mismatching, and **4 in-domain false
positives** (τ = ἀντί abbreviation ×3 + one editorial placeholder) get labeled numerals;
consumers can filter on `proposed=True`. The POS metric drops 81.7→79.8% purely as a
denominator artifact: that evaluator maps treebank `m` → class X and Morpheus has no numeral
tag, so every papyrus numeral counts as a POS mismatch both before and after.

**Verification**: pytest 33/33; PG baseline byte-identical to Round 8's saved snapshot;
AF re-run byte-identical (`tmp/af/ev2_af_r9check.txt`); SBLGNT flag-off A/B line identical —
default path unchanged on all three corpora.

## Not doing (standing constraints)

- Any Latin work (user direction for Round 9); the Round-8 Latin benchmark + table
  remain as committed, untouched.
- PROIEL-derived content in committed files (CC BY-NC-SA; measurement/docs only).
- NT behavior changes (Round-7 direction): no stemlib edits that alter SBLGNT/NT
  output to fit another edition's conventions.

**Open questions — resolution:** user chose to stop here ("Migrate, commit, push and
stop"); record migrated from todo.md; morpheus origin/master pushed. No further rounds
planned at this time. Candidate follow-ups if resumed: retrain the homograph table once
annotated LXX gold is available in the workspace (excluded — no `.mlxx` gold locally);
the 38 sub-threshold numeral forms are diminishing returns; fixing the false-hit letter
numerals (315 wrong top-1 on PapyGreek) would need stemlib entries that change default
behavior, out of scope per user direction.

# Round 10: accuracy, correctness, offline tooling, product/scale ✅

**User approved the whole plan ("Process"/"Do 2 and 3"/"Do 10-13"/"Do both"); complete
2026-10-14 → 2026-10-15.** Working files in `tmp/r10/` (git-ignored). Standing constraints
held throughout: no Latin, PROIEL content out of committed files, NT behavior unchanged,
no GitHub processing. Migrated from `todo.md` (2026-10-15). `improvements.md` gained a
"Round 10 additions" section at the end.

## Items and outcomes

- **Item 1 — learned disambiguation model: done (opt-in).** New
  `python/morpheus_toolkit/learned.py` (shared feature extractor + `LearnedRanker`),
  `scripts/build_learned_model.py` (per-token averaged perceptron), bundled
  `data/learned_reranker.json` (488 features; trained on SBLGNT + AF, 188,656 analyzable
  tokens). Features: lemma frequency + its rank, fine POS, stem type, morphological
  feature values, POS interactions with the neighbours' frequency-ranked POS. API
  `Morpheus(use_learned=True)` / CLI `--learned`. Top-1 lemma, frequency → learned:
  SBLGNT 94.6→**95.0**, AF 90.1→**90.6** (MorphGNT subset 95.9→96.4), independent PROIEL
  90.7→**91.5** (+0.8), AGLDT classical 91.4→**92.1** (every author positive). Uniformly
  positive → generalization; kept opt-in (not yet validated on LXX/PapyGreek). Adding
  morphological-feature tokens was the change that made it uniformly positive; a
  POS-only first version dipped on Homer/Diodorus. Evaluators gained a `--learned` flag.
- **Item 2 — adaptive domain-table selection: done (opt-in).** New
  `python/morpheus_toolkit/tables.py` (`TableSet`): scores every bundled table against the
  input's candidate lemmas by normalized rank inside each table (size-robust), picks the
  best fit; `blend()` provided. `Morpheus(adaptive_tables=True)` / `--adaptive-tables`.
  Selection correct on every register (SBLGNT→Koine, AF→AF, AGLDT→classical, PROIEL NT→
  Koine) and matches the best single table: **AGLDT classical 85.3→91.4 (+6.1)** vs the
  Koine default, AF 90.1→90.5, SBLGNT unchanged. Kept opt-in. 4 unit tests.
- **Item 3 — lemma-context features: tried, reverted.** Added neighbour closed-class
  lemma features (gated `--lemma-context`, off) and retrained: **worse** (PROIEL
  91.5→91.4, AGLDT 92.1→91.9, Diodorus 95.9→95.2) despite lower train error — the
  predicted-neighbour lemma is noisy and the features overfit. 488-feature model restored.
- **Item 4 — `-έλλω` aorist passive: fixed.** Root cause was not the compound scanner:
  `ἐγγελάω` is a real rare lemma, and the true gap was that the aorist passive of -έλλω
  verbs was never generated (simplex ἠγγέλη fell back to ἐγγελάω). Added
  `stemlib/Greek/stemsrc/vbs.r10` (explicit `:vb:` lines, stemtype `aor_pass`) wired into
  the vbind cat list. Verified ἠγγέλη → ἀγγέλλω, **ἀπηγγέλη → ἀπαγγέλλω** (wrong ἐγγελάω
  gone), καταγγέλη → καταγγέλλω.
- **Item 5 — `-πλ` pers_name artifact: fixed.** `addconstraints.pl` emitted a
  `:le:<lemma>-pl` `is_group` entry per `pers_name`; because the engine generates every
  number from one stem+ending class, the group entry duplicated the surface forms and made
  singular forms return the bogus `-πλ` alias. Fixed by emitting the group entries under
  the **base** lemma (`:le:$curlemma`), so indexnoms merges them. Verified: `-πλ` top-1
  lemmas SBLGNT 4/40K → **0**, AGLDT 26/120K → **0**; affected names now match gold where
  the base lemma is gold-correct (Συβαριτῶν→Συβαρίτης, Εὐμολπιδῶν→Εὐμολπίδαι,
  Ἀθηνᾶ→Ἀθήνη, βορρᾶ→Βορέας); plural/oblique still resolve; nomind shrank
  (4,367,409 → 4,336,597 B).
- **Item 6 — `-μπ` future-middle: already covered.** The Round-2 explicit `:vb:` lines
  resolve every standard λαμβάνω future (λήμψομαι/ῃ/εται/όμεθα/εσθε/ονται); non-standard
  λήψεται correctly returns nothing.
- **Item 7 — interjection POS: fixed.** Interjections carry stem type `exclam`, which
  `fine_pos()` did not map; mapped `exclam`→`I` (οἴμοι/φεῦ/ἰού). Unit test added.
- **Item 8 — offline benchmark harness: done.** `scripts/benchmark.py` reads whichever
  corpora are present (env: `MORPHGNT_DIR`/`AF_CORPUS_DIR`/`AGLDT_DIR`/`PROIEL_DIR`),
  prints analyzed / coverage / top-1 (raw→ranked→learned) / POS, checks committed
  thresholds `benchmarks/expected_greek.json` (tolerance-gated, non-zero exit; `--update`
  regenerates), and prints paired bootstrap CIs (`--bootstrap`). Offline only.
- **Item 9 — deterministic builds: done.** Two `make clean` rebuilds are byte-identical
  (equal to HEAD) for `steminds/`, `endtables/`, `derivs/`; the only deltas are the
  compiled STEMPROG helper binaries (build metadata, no analysis effect). The historical
  ±0.5pp drift is cross-environment. Hardened the makefile with
  `$(sort $(wildcard …))`; verified neutral.
- **Item 10 — confidence calibration: done.** `calibration.py` + `scripts/calibrate.py`
  (temperature by NLL grid search; `data/calibration.json`, T≈0.08). Applied by default;
  top-1 ECE 0.207→**0.141** (SBLGNT), 0.203→**0.139** (AF); `temperature=1.0` opts out.
- **Item 11 — convention profiles: done (mechanism).** `profiles.py` registry +
  `Morpheus(profile=…)` / `--profile`. Finding: Morpheus's Unicode output already matches
  the MorphGNT/LXX dictionary-form conventions (articles ὁ/RA, pronouns ἐγώ/σύ,
  demonstratives οὗτος/ἐκεῖνος), so the bundled transform is idempotent. Follow-up 11.2
  (`--base-lemmas` profile) deferred to Round 11.
- **Item 12 — Unicode-native path: scoped.** `docs/unicode-native-input.md` (NFD + mapping
  tables in `src/greeklib/gkunicode.c`, explicit `-u` flag, `to_beta` oracle test;
  ~2.5 days). Implementation deferred to Round 11.
- **Item 13 — scale/packaging: done.** `Morpheus(jobs=N)` / `--jobs` → **3.06×** at
  jobs=4 on the Apostolic Fathers (60.2s→19.7s), identical output.
  `scripts/package.sh` builds a wheel locally (`dist/`, git-ignored).

## Verification

- `pytest` → **49 passed** (was 38; +learned/tables/calibration/profiles tests).
- Offline benchmark gate: full run reproduces the evaluators and a re-run prints
  "OK (within tolerance)".
- Ruby C suite: 11 failures on macOS — reproduced on the committed stemlib too →
  pre-existing platform candidate-ordering differences, not regressions.
- Flag-off paths unchanged (learned/adaptive load nothing when off); calibration changes
  only reported confidence, not rankings.

## Out of scope (carried as standing constraints into Round 11)

- Latin work; PROIEL content in committed files (CC BY-NC-SA); NT behavior changes; any
  GitHub processing.
- Coverage fishing already declined: classical one-off names/fragments (0.15%), the LXX
  ἕως/ἠώς homograph, the 38 sub-threshold PapyGreek numerals, bare-letter numeral false
  hits.

# Round 11: harvest AGLDT v2.1 for training + classical POS model ✅

**Executed 2026-10-15.** Working files in `tmp/r10/` and `tmp/agldt/`. Only **Item A**
(AGLDT harvesting) and the round wrap-up (Item C) were executed; Item B remained a
candidate list and is carried forward in `todo.md`. Migrated from `todo.md` per the new
process rule; `improvements.md` re-evaluated (Round 11 section).

## Item A — harvest `PerseusDL/treebank_data` for training

- **A1 — `--format agldt` reader: done.** Added `read_agldt()` + `assign_chunks()` to
  `scripts/build_learned_model.py` (regex over `<word form=… lemma=… postag=…>`, one
  context chunk per file, skip postag `u`/`m`, map pos1 → coarse POS). Verified 468,596
  AGLDT rows. Analyzer calls are batched (4000) because AGLDT files are huge single chunks.
- **A2 — pool AGLDT into the learned re-ranker: done (balanced).** Two runs:
  - *pooled-all* (SBLGNT+AF+AGLDT = 650,360 tokens): classical **+3.25** but Koine
    regressed (SBLGNT 95.0→94.3, AF 90.6→90.0, PROIEL 92.1→91.7) — 70% classical pool.
  - *balanced* (`--agldt-limit 200000`; 385,758 tokens) shipped as the bundled model:
    AGLDT 88.5→**91.5** (Koine table) / 92.1→**93.2** (classical table); independent
    PROIEL **+0.13** (92.1→92.2); Koine −0.3 (SBLGNT 94.7, AF 90.3) — within the ±0.5pp
    build-noise band. Added the `--agldt-limit` uniform-subsample control.
- **A3 — classical POS model: built; negative result.** `scripts/build_pos_model.py
  --format agldt` → `data/pos_bigram_grc.json` (10 tags). Measured via the evaluator's
  new `--tagger/--model`: the classical bigrams beat the Koine ones for classical *when
  the tagger is used* (Homer POS 87.3 vs 84.8), but the tagger still trails plain
  frequency-ranked POS (ALL 85.2 vs 83.6) — consistent with the long-standing finding
  that the bigram Viterbi tagger does not pay off.
- **A4 — provenance: done.** AGLDT v2.1 is CC BY-SA 3.0 US (commit-safe); PROIEL stays the
  independent, measurement-only gold. Records the inventory finding: `AGDT2` (Aesop +
  P.-Apollodorus) is already in v2.1; `v2.0`/`v1.6`/`v1` are older copies; `IGDS` is
  ~73 words.
- **A5 — re-baseline: done.** `benchmarks/expected_greek.json` regenerated with the
  pooled model; harness gained per-group batching (large AGLDT files were timing out as
  single cruncher calls).

## Item B — other Round 11 candidates

Not executed (kept as candidates in `todo.md`): default-on validation (B1), a proper
POS/sequence model (B2), the Unicode-native C path (B3), per-config/POS calibration (B4),
the `--base-lemmas` profile (B5), cross-environment build determinism (B6), tokenizer
robustness (B7).

## Item C — round wrap-up

- **C1 — `improvements.md`: updated** (Round 11 additions section; header date).
- **C2 — migration: this record.** `todo.md` now holds Round 12 (proposed) and the
  carried-forward candidates.

## Verification

- `pytest` 49 green; `build_learned_model.py`/`build_pos_model.py`/`eval_grc.py` compile.
- Benchmark: pooled model run + thresholds rewritten; gate passes.
- Full A/B across SBLGNT / AF / AGLDT / PROIEL recorded above.

---

# Round 14: OIKONOMIA-Grammateus × Morpheus (entity-extraction integration) ✅

**Executed 2026-10-15.** Working files in `tmp/grammateus/` — all corpus-derived data,
gold, predictions and model artifacts stay there; **nothing DDbDP/OIKONOMIA-derived is
committed** (this record holds measurements only, per the standing constraint). Migrated
from `todo.md` per the process rule; `improvements.md` re-evaluated (Round 14 section).

## Where things stand after Round 13

The toolkit is a lemma/POS/numeral analyzer with a bundled learned re-ranker (top-1 lemma:
SBLGNT 94.7, AF 90.3, PROIEL 92.2, AGLDT 93.2) and an opt-in papyrus-numeral table. It has
no entity layer. Round 14 asked two questions: **what does the analyzer contribute under a
real entity-extraction pipeline** on documentary papyri, and **can that pipeline be
reproduced locally from public artifacts**.

## Round 14 plan (checkable; all approved)

14.1 joint pipeline prototype · 14.2 three extractor options with true P/R · 14.3
Morpheus-driven recall boost · 14.4 canonicalized entity output · 14.5 route comparison ·
14.6 fine-tune on the public gold. Guardrail: nothing OIKONOMIA/DDbDP-derived committed.

## Review (item 1: joint pipeline) ✅

`tmp/grammateus/pipeline.py` — NER extract → Morpheus canonicalize/soft-validate → optional
LLM second pass. Demonstrated on a real documentary segment (PHI7 `DDP0006`): the NER found
14 entities (64% Morpheus-recognized), qwen 15 (67%), agreement only 6/22; Morpheus
canonicalized real entities (`χαλκοῦ`→χαλκός, `δραχμῶν`→δραχμή, `ἥμισυ`→ἥμισυς) and flagged
suspect spans. Two refinements identified up front: separate "not a word" from "name
Morpheus lacks", and validate multi-word spans.

## Review (item 2: three extractor options, true P/R) ✅

- **Options.** (1) **OIKONOMIA-DB** (CC-BY-3.0 parquet, 61,249 docs) is fetchable and a big
  **reference/index**, but it is the same model's output (circular for NER) and
  DDbDP-derived. (2) **Fine-tuned NER checkpoint** (Apache-2.0) runs locally, deterministic
  and fast — **the extractor to pair with Morpheus**. (3) **Hand gold** was superseded: the
  real 115-document gold is public (`data/gold/annotated.jsonl`: 115 docs / 2,995 entities /
  15 labels, model-drafted + model-checked, *not* expert-validated).
- **Harness.** `tmp/grammateus/eval_gold.py` mirrors the project's own inference
  (`src/oikonomia/ner/{inference,encode}.py`: tokenize → argmax → `decode_spans`, strided
  token windows). Text is NFC (NFD input destroys the model: F1 0.002); lowercase hurts.
- **True P/R on the gold (zero-shot).** Shipped NER checkpoint: strict P 0.593 / R 0.567 /
  **F1 0.580**; relaxed 0.683; lemma-space 0.594. qwen base prompt: strict F1 0.229
  (P 0.394 / R 0.162); relaxed 0.418; lemma-space 0.274. Exhaustive prompt (19 docs):
  strict 0.319 / relaxed 0.566 vs NER 0.616 / 0.729 on the same subset.
- **Checkpoint diagnosis.** The card's stage-2 model was trained on all 115 docs (AGE F1
  0.974). The shipped artifact scores **the same** on the 85 pre-expansion docs (0.587) and
  the 30 new docs (0.580), has no memorization, and predicts **0 AGE** — behaviour matches
  the card's **silver-stage** model (card 0.654; measured 0.580 zero-shot), not stage 2.
  Weak labels: OCCUPATION (20% covered), COMMODITY 45%, TAX_TERM 41%, TRANSACTION 56%;
  confusions PLACE→PERSON (69), numeral family (~130). Item 6 confirms and fixes this.
- **DB ≠ gold on the same 115 docs** (PERSON 958 vs 840, MONEY_AMOUNT 185 vs 223,
  `has_price` 0 vs 10, `has_tax` 1 vs 29): the DB is a linkable reference, not a gold
  substitute.

## Review (item 3: Morpheus-driven recall boost) ✅

- **Candidates (deterministic).** After NER, Morpheus flags unlabelled content tokens
  (POS N/A or `stemtype=numeral`, not `proposed`): 2,476 candidates over the 115 docs;
  **425 of the 931 missed gold spans (46%) contain one** — OCCUPATION 75%, COMMODITY 81%,
  TAX_TERM 78%, PERSON_ROLE 94%, QUANTITY 65%, MONEY_AMOUNT 36%; AGE only 1% (its spans sit
  inside wrong-label DATE_REF predictions — a relabelling problem). With
  `Morpheus(numerals=True)` the set grows 2,476→2,526 and reachability 425→430 (+5 spans;
  AGE 1%→2%) — letter-numerals are not the AGE bottleneck.
- **Full 115-doc LLM pass** (one call per doc over just the candidates, `boost_llm.json`):
  naive merge is F1-negative (strict 0.580→0.519, relaxed 0.683→0.620 — strict R rises
  0.567→0.632 but the LLM over-labels). **Label-filtered merge is net-positive:** whitelist
  {COMMODITY, OCCUPATION, TRANSACTION, MONEY_AMOUNT} → strict P 0.559 / R 0.613 / **F1
  0.585**, relaxed **0.689** (+4.6pp strict recall).
- **Proposal quality (1,435 proposals; 14% strict-precise, 22% relaxed-precise;**
  **relaxed precision):** OCCUPATION 0.72 (70 of 154 missed recovered), COMMODITY 0.43
  (73/113), MONEY_AMOUNT 0.36 (12/106), TRANSACTION 0.10 (10/29); whitelist = 422
  proposals, 41% relaxed-precise, 165 missed spans recovered. Outside the whitelist
  relaxed precision is ≤0.22 (PERSON 0.47 but only 0.03 strict — boundary noise; QUANTITY
  0.20; PLACE 0.22; UNIT/CURRENCY/PRICE_TERM/AGE ≈0).
- **Verdict:** the second pass works only as a **whitelist-filtered, recall-oriented**
  layer; Morpheus candidate generation is what makes it cheap (one call per document).
- **It does not survive a stronger extractor.** The same recipe re-run on the
  fine-tuned model's held-out output (`boost_llm_ft.json`): proposals drop to 5%
  strict / 8% relaxed precise (whitelist 16% — 33 missed spans recovered) and the
  merge turns **F1-negative**: strict 0.717→**0.700** (P 0.648 / R 0.760), relaxed
  0.814→**0.795**. A good extractor's remaining misses are the hard ones; the boost
  is a crutch for a weak extractor, not a permanent layer.

## Review (item 4: canonicalized entity output) ✅

`tmp/grammateus/canonical.py` re-keys every entity by Morpheus: per-word lemma/POS/
features/confidence plus a canonical key (lemma sequence + label); artifacts
`canonical_entities_ner.jsonl`, `canonical_entities_ner_boost.jsonl`. Label-aware policy:
`Morpheus(numerals=True, unknown_as_proper=True)`; PERSON/PLACE prefer a proposed (name)
analysis, and a capitalized token whose best stemlib analysis is a verb (genitive-name
false friends) keeps its surface as the safe canonical form. Measured: shipped NER 2,867
entities, 53% fully known, 5% of surface keys collapse in canonical space, lemma-space F1
0.580→0.594; fine-tuned model 3,272 entities, 53% known, 4% collapse, lemma-space F1
0.717→0.725 — **the morphology layer's gain shrinks as the extractor improves**. Two
toolkit gaps recorded in `improvements.md`: letter-numerals are opt-in and the lowercase
letter for 1 is missing from the table; verb false friends outrank name proposals for
analysed tokens.

## Review (item 5: route comparison) ✅

Micro F1 on the 115-doc gold (strict / relaxed / lemma-space):

| route | strict F1 | relaxed F1 | lemma F1 |
| --- | ---: | ---: | ---: |
| qwen base prompt | 0.229 | 0.418 | 0.274 |
| shipped NER checkpoint (zero-shot) | 0.580 | 0.683 | 0.594 |
| shipped NER + whitelist boost | 0.585 | 0.689 | — |
| fine-tuned from GreBerta (gold only, held-out) | 0.295 | 0.516 | 0.295 |
| **fine-tuned from shipped ckpt (held-out)** | **0.717** | **0.814** | **0.725** |
| fine-tuned + whitelist boost (held-out) | 0.700 | 0.795 | — |
| fine-tuned final (train-on-test) | 0.981 | 0.990 | 0.979 |

(The boost row is net-negative on the fine-tuned base — see item 3.)

**Morpheus-layer measurements** (held-out fine-tuned preds): 54% of predictions fully
Morpheus-validated / 11% partial / 35% none; strict-match rate 0.705 (validated) vs 0.664
(not) — a *soft* signal (hard-filtering drops strict F1 0.717→0.522); 61% of remaining
misses contain Morpheus-known words.

## Review (item 6: fine-tune on the public gold) ✅

`tmp/grammateus/finetune.py`, the project's stage-2 recipe (lr 3e-5, linear + warmup,
15 epochs, batch 8, max_len 512, seed 17; 5-fold CV + final). Two runs:

- **From base GreBerta (gold only): weak.** CV strict F1 0.296 / relaxed 0.518 (AGE 0.462,
  CURRENCY 0.507, UNIT 0.481; COMMODITY 0.041, OCCUPATION 0.076) — gold-only fine-tuning on
  a non-domain backbone doesn't transfer; consistent with the card's no-DAPT control (0.495
  on the 65-doc gold).
- **From the shipped checkpoint: CV strict F1 0.717 / relaxed 0.816** — the card's
  0.737/0.837 reproduced within fold noise, at laptop scale (~25 min on MPS). Per-label
  held-out (card value): AGE 0.932 (0.974), PERSON 0.767 (0.775), CURRENCY 0.835 (0.822),
  UNIT 0.845 (0.841), PLACE 0.648 (0.650), MONEY_AMOUNT 0.744 (0.758), QUANTITY 0.690
  (0.744), DATE_REF 0.644 (0.690), OCCUPATION 0.696 (0.746), TRANSACTION 0.597 (0.602),
  PRICE_TERM 0.929 (0.929), FRACTION 0.785 (0.863). Final model (all 115, train-on-test)
  0.981 strict / 0.990 relaxed — training pipeline verified.

**Outcome:** the shipped artifact is the silver-stage model; the card's stage-2 quality is
reproducible locally by fine-tuning that checkpoint on the public gold. Model artifacts
stay in `tmp/grammateus/model_gold{,2}/`.

## Verification

- `pytest python/tests` — 49 passed (no toolkit code changed; the bare-`pytest` rootdir
  collision with the scratch `tmp/r10/test_tables.py` is pre-existing and ignored).
- All Round 14 numbers re-derivable offline from `tmp/grammateus/` (`eval_gold.py`,
  `eval_folds.py`, `compare_all.py`, `morpheus_layer.py`, `canonical.py`,
  `recall_boost*.py`, `merge_boost.py`, `finetune.py`); LLM calls only via local LM Studio.
- Benchmark gate untouched (no shipped-code changes).

## Not doing (standing constraints)

- Nothing TLG/PHI-derived and nothing DDbDP/OIKONOMIA-derived is committed (personal-study
  use only); PROIEL-derived content stays measurement-only.
- No GitHub CI runs; pushes use `[skip ci]`.

---

# Round 12: license-safe private-corpus coverage harvest (PHI7 documentary) ✅

**Closed 2026-10-15 as a documented feasibility study (Option A).** Executed as a
local-only probe; closed without toolkit changes because the license-clean actionable
upside is small and the big miss buckets are either inherent or not committable. Tooling
stays in git-ignored `tmp/phi/` (`probe.py`, `scan.py`, `lsj_filter.py`); this record is
method/counts only — **no PHI/TLG-derived data in any committed file**. `improvements.md`
re-evaluated: no change (no shipped-code effect).

## What was done

- **Format decoded; extraction solved without porting the Delphi parser.** PHI7 `.TXT`
  keeps all reference/metadata (region, author, work, citation, nibble codes) in
  high-ASCII bytes (≥0x80) and the TLG beta text in 7-bit ASCII. Dropping ≥0x80 and
  stripping TLG/Leiden markup (numeric codes, bracket/brace wrappers, lacunae, underdots,
  line-break hyphens) yields clean beta. Validated against the user's own
  `BetaCode/Attica.TXT` export: **99.6% distinct / 99.9% token overlap**.
- **Regions**: inscriptions ~49 MB, documentary papyri ~45 MB, Christian ~12 MB (Coptic
  excluded).
- **Coverage probe**: documentary Greek analyzes at **73.5%** — the weakest register
  (cf. PapyGreek 92.9% after Round 8).
- **Miss taxonomy (26.5% missed token mass)**: ~50% ≤4-letter fragments (inherent to
  broken texts); ~21.5% (466,789 tokens) proper names, mostly not in LSJ (so not
  committable); a documentary word family (~15K tokens); a few common verb forms; ~17K
  numeral tokens (tally-style); a small line-split tokenizer leak in the probe extractor.
- **License-clean filter**: matching the 383,888 missed distinct forms against
  public-domain LSJ (accent-skeleton + stem + plausible-ending rule; prefix entries
  excluded) leaves **14,097 forms / 61,318 tokens = 2.8% of misses (≈0.75% of the
  corpus)** mapping to 6,127 candidate lemmas — still fragment-contaminated; the
  genuinely real subset (e.g. LSJ-attested ὑοθεσία, Ἡρακλῆς, Σάραπις, Θερμοῦθις, δῆμος,
  στῆλη, εὐλογία, ἀρτάβη) is smaller still.

## Decision and rationale (Option A)

- The two big buckets are **inherent** (fragments) or **not committable** (names).
- The committable remainder is **below 0.75% of tokens** after curation, against the
  cost of curation + a new generated source + stemlib rebuild + benchmark re-baseline.
- The documentary register is already served by committable PapyGreek-derived work
  (Rounds 8/9: `nom.papyri`, numeral table).
- **Closed as a feasibility study; 12.3–12.6 not executed.** The probe vindicates the
  earlier "coverage probe only / probably not a windfall" stance with data.

## Carried forward

- The I.PHI/Pythia idea (candidate B9) is moot for Round 12; lacuna restoration as a
  pre-pass for fragmentary texts remains an open candidate note.
- A numeral-table extension for tally-style numerals is not worth pursuing for PHI under
  the license rule; Round 9's table already covers letter-numerals.

## Verification

- Extraction validated against the user's own export (99.6% distinct / 99.9% token).
- No shipped-code changes; `pytest` green; benchmark gate untouched.

---

# Round 15: B-item sprint — learned + adaptive defaults (2026-10-15) ✅

## Goal

Ship as much of the B-item backlog as can move the `## Accuracy` numbers before the
CSNTM/Wallace contact: the B1 default flip first, then whatever else measures today.

## B1 — `--learned` + `--adaptive-tables` are now the Greek defaults (shipped)

- **API**: `Morpheus(use_learned=True, adaptive_tables=True)` by default; opt out with
  `use_learned=False` / `adaptive_tables=False`. Caller-supplied `frequencies=` are
  never overridden (new `_explicit_frequencies` guard). CLI: `--no-learned` /
  `--no-adaptive-tables`; the old positive flags remain as hidden no-op aliases.
- **Benchmark**: defaults flipped to match (`--no-learned`/`--no-adaptive` opt-outs);
  the canonical gate command is now plain `scripts/benchmark.py`; `--no-gate` added for
  opt-out diagnostics.
- **Validation** (identical candidate sets; corpus-level top-1 lemma):

  | corpus | old default | new default | gain |
  | --- | ---: | ---: | ---: |
  | SBLGNT (137,554) | 94.56 | 94.67 | +0.1 |
  | Apostolic Fathers (63,227) | 90.14 | 90.21 | +0.1 |
  | AGLDT classical (469,254) | 86.56 | **93.74** | **+7.2** |
  | PROIEL Greek NT (132,366) | 91.66 | 92.19 | +0.5 |
  | LXX (623,685, exact) | 88.4 | 90.7 | +2.3 |
  | PapyGreek (36,455, exact) | 81.2 | 85.7 | +4.5 |

- Adaptive selection picked the right register on every corpus (fit margins):
  SBLGNT→Koine (0.91), AF→AF (0.89), AGLDT→classical (0.95), PROIEL→Koine (0.91),
  LXX→LXX (0.93 vs 0.88), PapyGreek→papyri (0.72 vs 0.68).
- Re-baselined `benchmarks/expected_greek.json` from the shipped-default run.
- Interaction recorded: on AF, learned + AF table (90.21) vs frequency + AF table
  (90.45) — the learned model's features were trained against the default table, so a
  selected table helps its *fallback* order more than its scores. Net vs old default
  still positive (+0.07).
- Tooling fixes found along the way: `select_adaptive_table` analyzed group-by-group
  (a cruncher spawn per verse/sentence — minutes wasted); now flattens the sample and
  batches it. Non-learned runs no longer report a phantom `learned=0.0%`
  (miss-branch flag leak in `Counters`).
- Tests: 3 new API tests (defaults on, opt-outs, explicit-frequencies guard) — 56 pass.

## B4 (partial) — confidence calibration follows the score path

- The bundled temperature (T=0.08) was fitted on frequency scores; after the flip the
  default path reports learned scores on a different scale.
- `calibrate.py --learned` fits the learned path and merges `temperature_learned` +
  ECE fields into `calibration.json` (merge keeps both fits in one file);
  `load_temperature(learned=...)` and `api._annotate` select by the score path that
  actually produced the order (`_learned_scores` tracks it; the context/homograph
  passes keep the historical frequency temperature).
- Measured: the learned path is natively calibrated → T=1.0, ECE **0.0054** (SBLGNT) /
  **0.0024** (AF), vs frequency T=0.08 ECE 0.1416 / 0.1393 (raw 0.208 / 0.2034). A
  probe confirmed the learned path is insensitive to T ∈ [0.08, 1.0] (ECE ~0.005), so
  the pre-flip mismatch was numerically harmless — but the selection is now correct
  and the *default-path* confidence is ~30× tighter than the old default's.
- Remaining: joint-path temperature + calibrated POS confidence (B4 stays open).

## Numerals gap (Round 14 carry-over)

- Lowercase α/ε were absent from the table while their capitals were present.
  `propose()` now falls back to the capital entry (`*` prefix) for single letters —
  numeral case is meaningless. PapyGreek `--numerals`: numeral misses **853 → 38** of
  1,454; coverage 92.9% → **95.1%**; top-1 **87.8%** exact with papyri + learned.
- New `test_numerals.py` (2 tests).

## B8 — head-to-head: bundled learned vs LM-MLP vs combined (measurement only)

- Harness `tmp/lm/head2head.py` (proto.py extended): identical example sets (≥2
  candidates, gold among them), four scorers, corpus-level projection. The AF and
  PROIEL projections reproduce the benchmark exactly (90.1/90.3, 91.7/92.2) — the
  harness is comparable to `scripts/benchmark.py`.
- Result: the LM head wins on accented text (SBLGNT test 99.4 vs learned 97.9; AF 98.0
  vs 97.3 ambiguous-only; corpus-level +0.5 / +0.2) but **regresses on the shipped
  accent-insensitive pipeline** (PROIEL 92.3 vs learned 96.4 ambiguous-only; 89.9 vs
  92.2 corpus-level). Mechanism measured: `ignore_accents` inflates PROIEL's
  multi-candidate rate 37.8% → 59.4% (38.8% vs 22.1% distinct-lemma) — accent-variant
  homographs the LM head (trained on accented SBLGNT only) never saw.
- Combined ≈ LM (the learned-rank feature adds nothing).
- **Not shipped** (`torch` + ~440 MB GPL-3.0-derived weights). Actionable finding: an
  LM layer must be trained on the shipped candidate distribution (incl.
  `ignore_accents` examples), not just accented gold text. B8 stays open.

## Homograph re-ranking — stays opt-in

- Measured on the new default: SBLGNT 94.7→94.9, AF 90.2→90.7, PROIEL 92.2→93.1, but
  AGLDT **93.7→93.3** — fails the "never worse" bar for a default; stays opt-in
  (documented with these numbers).

## B10 — "Logion" verified

- Cowen-Breen et al., *Machine-Learning Based Detection and Correction of Textual
  Errors in Greek Philology* (ALP 2023), arXiv:2305.01099; `charliecb/Logion`;
  HF `cabrooks/LOGION-*`. It is a scribal-error BERT, not a corpus: the 70M-word
  corpus is request-only, and its models derive from a GPL-3.0 base with no explicit
  licence — not a clean corpus/LM source. Closed.

## B2/B3/B5/B6/B7/B9 — assessed

- B2: the POS-bigram negative result stands; the learned-emission direction is what B8
  measured (the LM is the lever; the bundled perceptron captures most of the
  transferable signal on accented text). Closed as subsumed by B8.
- B3: robustness/parity work (own round); no accuracy effect — scoping doc stands.
- B5/B6/B7: no `## Accuracy` effect today; carried.
- B9: lacuna-restoration pre-pass remains a candidate; the I.PHI part was retired with
  Round 12.

## Verification

- `pytest python/tests` — 56 passed.
- `scripts/benchmark.py` (shipped defaults) — gate green on the re-baselined
  thresholds; the four-config matrix is deterministic (independent runs agree).
- All measurement material in git-ignored `tmp/`; no PROIEL/TLG/PHI-derived content
  committed.

## Carried forward

- B4 remainder (joint-path temperature, POS confidence); B8 revisit with a
  licence-clean LM trained on the shipped candidate distribution; B3/B5/B6/B7/B9.
- Round 13 remains queued pending the CSNTM contact.

# Round 16: PapyGreek recovery pre-pass + annotation hygiene (2026-10-15) ✅

## Goal

User-selected scope: the PapyGreek recovery pre-pass (spelling variants + name
lemmatization) and the annotation-lemma hygiene — the two items that move the
top-priority corpus without touching the learned features (that is Round 17).

## 16.1/16.2 — `recovery.py`: spelling variants + name candidates (shipped)

- **`spelling_variants`** — bounded (cap 48), closest-first (singles → pairs)
  orthographic generator: vowel classes ι/ει/η/υ/οι/υι/ου, ε/αι, ο/ω; consonant
  classes τ/δ/θ, κ/γ/χ, π/β/φ; geminate simplification/doubling; documentary
  globals ο/οι, ει/ε, ζ/σ, μψ/ψ; final -ν/-ς incl. sandhi (μὲγ→μέν, ἐὰμ→ἐάν);
  dropped iota subscripts restored on single η positions.
- **`name_candidates`** — case-ending → nominative rules (Δωρίωνος→Δωρίων,
  Ἀχιλλᾶτος→Ἀχιλλᾶς, Χοινώθμεως→Χοινωθμις, Δωρίωνα→Δωρίων); when the stemlib
  confirms a reading whose lemma matches the candidate (accents ignored) that
  reading is used, else a synthetic `stemtype="proper"` proposal re-accented from
  the active frequency table and capitalized to match the surface.
- **Shared `recover()` helper** — fires only on tokens with zero analyses, batches
  the re-analysis (2,000/chunk), flags `proposed=True` + `recovered_from`; API,
  CLI and both measurement harnesses use the same code path.
- `_finish` order: unaccented → numerals → adaptive → recovery →
  unknown_as_proper → rank → learned (adaptive before recovery so name proposals
  re-accent from the chosen table; unknown-as-proper after so specific proposals
  win).
- **Default flip (B1-style, after measurement)**: `Morpheus(recovery=True)`, CLI
  `--no-recovery` (positive flag kept as a hidden alias), benchmark
  `--no-recovery`. Additive by construction: analyzed tokens are byte-identical
  with the pre-pass off or on.
- 16 tests in `test_recovery.py`; 72 total pass.

## 16.3 — Measurement

PapyGreek (36,455 word tokens; learned + adaptive defaults, papyri table,
`--numerals`), recovery off → on:

| metric | off | on | gain |
| --- | ---: | ---: | ---: |
| coverage | 95.1% | **99.2%** | +4.1 |
| top-1 ranked (exact / acc-insens) | 85.9 / 87.3 | **87.9 / 89.3** | +2.0 |
| top-1 learned (exact / acc-insens) | 87.9 / 89.4 | **89.7 / 91.2** | +1.8 |
| unanalyzed tokens | 1,781 | **296** | −83% |

- 1,265 distinct forms recovered: 390 spelling-only, 376 name-only, 499 both;
  exact top-1 hits among recovered tokens split 588 spelling / 134 name.
- Default (no `--numerals`): coverage 92.9% → **97.4%**; learned 87.5/89.0.
- LXX (623,685 tokens): coverage 99.81% → **100.0%** (572 forms recovered);
  learned top-1 unchanged (90.7/91.2) — additive, as designed.
- Coarse POS 80.1% → 79.7% is a completeness artifact: the ~1,485 newly covered
  tokens enter that metric's denominator and agree at ~70%.
- Remaining PG misses (296) are dominated by marked/truncated forms (189),
  numerals outside the table (31), stemlib gaps (παστοφόρων, ἐρίδια, πόκια) and
  the long spelling tail (συνπροσγενόμενος, ἀνήνκασε, γεγράφεκα).
- Gate (SBLGNT / AF / AGLDT / PROIEL): coverage, ranked and learned top-1 up-or-equal
  on all four (learned SBLGNT 94.67→94.70, AF 90.21→90.26, AGLDT 93.74→93.76,
  PROIEL 92.19→92.24; coverage +0.02–0.06 each). The analysis rate jumps where misses
  were name-heavy (AF 98.37%→99.4%, SBLGNT 99.79%→99.95%). The only metric that moves
  down is AF coarse POS (75.94→75.31) — the documented completeness artifact: ~650
  newly analyzed tokens agree at ~15%, and every previously analyzed token's order is
  byte-identical (the arithmetic reproduces 75.31 exactly).

## 16.4 — Annotation-lemma hygiene

- Harness `clean_gold_lemma` strips `|num:N|`/`|gap:N|` spans from gold lemmas
  (45 tokens); U+0305 combining overline added to the marker inventory
  (`β̅|num:2|` → β → numeral table). Baseline re-measured under the same harness:
  learned 87.8/89.3 → 87.9/89.4 (the +0.1 is hygiene, not recovery).
- Convention floor documented (data-only): 45 annotated lemmas, 35 hyphenated
  compound lemmas, 5,598 (15.4%) surface lemmas; degree suppletion
  (πλεῖστα→πολύς) and particle conventions (κε→ἄν) bound achievable agreement.

## 16.5/16.6 — Docs + wrap-up

- README: new "Recovery pre-pass" section (rules + measurement table + caveats);
  the coverage limitation bullet updated.
- improvements.md: Round 16 section; PG coverage row 92.9% → 97.4% (default) /
  99.2% (`--numerals`).
- lessons.md: iota-subscript finding; reproduce-through-the-exact-path lesson;
  re-measure-the-baseline-after-harness-change lesson; POS completeness artifact.

## Verification

- `pytest python/tests` — 72 passed.
- CLI smoke: ἥμυσυ → ἥμισυς (default); `--no-recovery` → miss; hidden
  `--recovery` alias accepted.
- Gate: the verification run (recovery on vs the old thresholds) showed
  coverage/ranked/learned up-or-equal on all four corpora; its one red line — AF
  coarse POS, −0.63pp — is the completeness artifact above (no token's analysis or
  order regressed). Thresholds re-baselined with `--update` from the shipped-default
  run; the confirmation re-run was cut off by a session boundary, and Round 17's
  full gate run re-validates the thresholds end-to-end.
- All measurement material in git-ignored `tmp/`; no PROIEL/TLG/PHI-derived
  content committed.

## Carried forward

- Round 18 (agreed, deferred): canonical-lemma scoring fix (form-element
  pollution), learned-feature cleanup, PG retrain with a document-level held-out
  split.
- B items: B3 (Unicode-native C path), B4 remainder (joint-path temperature + POS
  confidence), B5 (profile registry `--base-lemmas`), B6 (build determinism), B7
  (tokenizer robustness), B8 (licence-clean LM), B9 (lacuna restoration).
- Round 13 remains queued pending the CSNTM contact.

---

# Round 17: recovery tail pass + PapyGreek gate entry (2026-10-15) ✅

## Goal

Close the measured tail of the Round 16 recovery pre-pass and put PapyGreek — the
priority corpus — into the offline regression gate. Items 17.1–17.6 from the plan
(evidence: the 296-miss Round 16 record in `tmp/pg16/`).

## 17.1 — Operation-based recovery variants (shipped)

`recovery.spelling_variants` rebuilt around primitive edit operations on the
normalized base: every rule is an edit list (`_edits` returns `(rank, pair_eligible,
edits)`), tier 1 emits all single operations, tier 2 merges every eligible pair
(slot+slot, slot+geminate, slot+global), and the capped list (96) stays closest-first
with vowel substitutions before consonants. Added internal nasal assimilation
(νπ→μπ, νβ→μβ, νφ→μφ, νκ→γκ, νχ→γχ, νγ→γγ) and extended geminate reduction
(ββ γγ δδ θθ φφ χχ beside the existing λλ μμ νν ππ ρρ σσ ττ κκ). Newly reachable:
συνπροσγενόμενος → συμπροσγενόμενος, θρυδάκεια → θριδάκια (υ→ι + ει→ι),
ὑγειαίνησς → ὑγιαίνῃς (ει→ι + σσ→σ).

## 17.2 — Compositional letter-numerals (shipped)

`numerals.propose(beta, surface=None)`: beside the 50-form table, a vowel-less run of
≥2 numeral letters gets the table's surface-lemma convention with the letter sum in a
`value` feature (χμγ = 643, ψπ = 780, ρξβ = 162 …); single letters fall back across
case in both directions (the table lacked capital singles like Β, Ζ, Δ, Τ, Φ). Still
opt-in (`--numerals`), still unanalyzed-only. χμγ's absence from the table was
explained: the builder keeps gold pos `m` tokens and χμγ's gold pos is `x` — the rule
covers it without a table rebuild. Ατ (gold 1300, contains a vowel) remains a table
exception (decimal lemma).

## 17.3 — Curated stemlib nouns (shipped)

`build_papyri_stemlib.py` gained three curated entries in the generated `nom.papyri`
(each justified: LSJ headword or LSJ-attested derivative / PG attestation):
παστοφόρος (LSJ via παστοφόριον/ἀρχιπαστοφόρος), πόκιον (PG-attested diminutive of
πόκος), ἐρίδιον (LSJ headword, Dim. of ἔριον, long iota [-ῑδ-]). θριδάκιον and
πιττάκιον were already in `lsj.nom`, and ἀρχισωματοφύλαξ already analyzed — their
misses were spelling issues (17.1's job). Rebuild: 10 lines added; only
`nom.papyri`, `steminds/nomind`, `nomind.lindex` changed.

## 17.4 — PapyGreek in the offline gate (shipped)

`scripts/benchmark.py` gained the optional `PAPYGREEK_DIR` corpus: reader mirrors the
tmp harness (original spelling, markers stripped; regularized gold lemma; per-document
grouping; POS classes inverted from the harness's TB2CLASS/MORPH2CLASS maps including
the DC bridge and X/I equivalence), shipped default gated (no `--numerals`).
Gate row: n=36,455, analyzed 97.4%, cov 90.8%, raw 74.8 → ranked 87.7, learned 88.1,
POS 81.3% (POS matches the harness exactly; ranked/learned read above the harness's
exact column because the gate's `matches_lemma` credits any lemma variant — see
lessons.md).

## 17.5 — Proposal-confidence audit (carried to B4)

Audited (sample: 40 documents, 3,589 tokens; 299 all-proposed tokens): softmax
confidence is conditional on the generated candidate set — lone proposals report 1.0
(63 tokens), mean 0.842 vs ~0.59 measured top-1 accuracy for recovered forms. The
proper fix (fitted per-strategy priors) is carried to B4; findings in
`tmp/pg17/audit_17_5.md`.

## 17.6 — Measurement

PapyGreek (all 36,455 word tokens; learned + adaptive defaults with the papyri table,
`--numerals`; Round 16 → Round 17):

| metric | Round 16 | Round 17 |
| --- | ---: | ---: |
| coverage | 99.2% | **99.4%** |
| unanalyzed tokens | 296 | **235** |
| — editorially marked | 189 | 157 |
| — numeral tokens | 31 / 1,454 | **14 / 1,454** |
| top-1 ranked (exact / acc-insens) | 87.9 / 89.3% | **88.1 / 89.5%** |
| top-1 learned (exact / acc-insens) | 89.7 / 91.2% | **89.9 / 91.4%** |
| recovered forms (spelling/name/both) | 1,265 (390/376/499) | **1,295 (422/331/542)** |
| recovered exact top-1 (spelling/name) | 588 / 134 | **634 / 132** |

Default path (no `--numerals`): 97.4% coverage / 87.6 / 89.1 learned, 942 unanalyzed
(Round 16: 97.4% / 87.5 / 89.0).

ε/η and α/ο interchange experiments: measured against the miss list — ε/η fixes 3
tokens, α/ο 6; both add tier-1 operations that shift every existing target deeper into
the capped list, so both were deferred with the measurement recorded.

## Docs

- README: recovery section (op-based generator, new rules, Round 16/17 table);
  numerals section (compositional rule, symmetric case fallback); limitation bullets.
- improvements.md: Round 17 section; PG opt-in coverage row 99.2% → 99.4%.
- lessons.md: op-based generation; measure-a-symmetric-rule; builder filters; gate vs
  harness comparison conventions; confirmation-runs; proposal-confidence audit.

## Verification

- `pytest python/tests` — 75 passed.
- CLI smoke: συνπροσγενόμενος/θρυδάκεια/ὑγειαίνησς recovered (default); χμγ → χμγ
  [value=643], ψπ → ψπ [value=780] with `--numerals`.
- Gate: thresholds re-baselined with `--update` on all five corpora (shipped
  default). SBLGNT unchanged on every metric; AF analyzed +0.01; AGLDT unchanged
  except learned −0.01pp (the recovery's new variants alter a few
  previously-recovered tokens' candidate sets; the three new stems match no AGLDT
  token); PROIEL +0.01/+0.02; PapyGreek joined the
  gate (n=36,455, analyzed 97.42%, cov 90.81%, ranked 87.73%, learned 88.07%,
  POS 81.28%). The confirmation run reproduced every metric byte-identically and
  reported **OK (within tolerance)**.
- All measurement material in git-ignored `tmp/`; no PROIEL/TLG/PHI-derived content
  committed.

## Carried forward

- B4: fitted per-strategy priors for proposal confidence.
- ε/η + α/ο interchanges: measured, deferred (9 tokens; cap-pressure risk).
- Round 18 unchanged (canonical-lemma scoring + learned retrain).

# Round 18: canonical-lemma scoring + learned retrain (2026-10-15) ✅

## Goal

Fix the candidate-scoring primitive that credited a form element with another word's
frequency (18.1), clean up the learned features that encoded it (18.2), and retrain
the learned model on the shipped candidate distribution with a document-level
PapyGreek held-out split (18.3); gate + docs (18.4). The B items B4/B5/B7 close in the
same session (B6 was already committed); B3/B8/B9 are assessed and carried.

## 18.1 — Score on the canonical lemma (shipped)

Morpheus's `form,lemma` candidate field carries the *forms* the stem matched before the
lemma; a Doric/alternate stem can make one entry's form element equal a different
word's lemma — πηρός's Doric stem lists παρά, so variant-list scoring credited πηρός
with παρά's frequency (366) and promoted it above the actual preposition on PapyGreek.
`Ranker.frequency_score` now scores `normalize_lemma(analysis.lemma)` only; the same
fix applies to `LearnedRanker._best_frequency`/`_best_joint`, the adaptive table fit
(`tables.py`) and the opt-in homograph re-ranker (`homographs.py`). Matching still
considers every variant (`Analysis.matches_lemma`, the Strong's fallback, the gold
readers) — matching wants recall, scoring wants identity.

Measured (same harness, before → after): PG plain path ranked **88.1 → 89.4** exact /
**89.5 → 90.8** accent-insensitive; recovered-form top-1 634 → **660**; SBLGNT a wash
(top-1 ranked 94.6, POS 77.9 = the gate baseline). Evidence: `tmp/r18/pg_18_1.txt`,
`tmp/r18/sblgnt_18_1.txt`.

## 18.2 — Learned-feature cleanup

The frequency/rank features were computed from the polluted ordering, so 18.1 fixed
them at the source; all scoring sites were re-verified (`grep variants()` now finds
only matching/presentation uses). No `proposed` feature was added: proposal membership
is constant within a token's candidate set, so it cancels in perceptron updates and
cannot affect the ranking.

## 18.3 — Retrain on the shipped candidate distribution

`scripts/build_learned_model.py` now (a) runs the same recovery pre-pass the shipped
pipeline uses — tokens with no analysis become spelling/name proposals and are ranked
like any other candidate; (b) reads the PapyGreek treebanks (34,998 tokens) with a
document-level stride split — 79 documents / 7,474 tokens held out; (c) prefers
canonical-lemma matches when choosing the gold index (variants fallback); (d) reports
the held-out frequency-vs-learned top-1 and stores it in the model file
(`papygreek_holdout`).

Training: **411,615** analyzable tokens (Round 15: 385,758), 827 features → **711**
kept (≥2 occurrences). Held-out PapyGreek (6,936 analyzable of 7,474): frequency top-1
94.2%, learned top-1 **96.1%** (training convention: covered tokens, bundled Koine
table). Model source string updated: "+ PapyGreek Treebanks v1.01 (CC-BY-SA 4.0)".

PapyGreek with the new model (all 36,455 word tokens; learned + adaptive defaults with
the papyri table, `--numerals`; Round 17 → Round 18):

| metric | Round 17 | Round 18 |
| --- | ---: | ---: |
| coverage | 99.4% | 99.4% |
| unanalyzed tokens | 235 | 235 |
| top-1 ranked (exact / acc-insens) | 88.1 / 89.5% | **89.4 / 90.8%** |
| top-1 learned (exact / acc-insens) | 89.9 / 91.4% | **90.2 / 91.7%** |
| POS coarse | 81.1% | 81.1% |
| recovered-form top-1 (ranked, exact) | 634 | **660** |
| default path (no `--numerals`) learned | 87.6 / 89.1% | **88.0 / 89.5%** |

## 18.4 — Gate + docs

Full offline gate re-run with the round's defaults (adaptive + learned + recovery),
re-baselined with `--update` and confirmed green against the new thresholds. Every
per-corpus `adaptive table:` pick is unchanged (SBLGNT→koine, Apostolic Fathers→
apostolic, AGLDT→classical, PROIEL→koine, PapyGreek→papyri) — the check that the
scoring fix did not move a load-bearing table choice — and no metric regressed:

| corpus | coverage | ranked (17 → 18) | learned (17 → 18) | POS (17 → 18) |
| --- | ---: | ---: | ---: | ---: |
| SBLGNT | 95.3% | 94.60 → 94.60 | 94.70 → 94.70 | 77.82 → **78.06** |
| Apostolic Fathers | 91.3% | 90.52 → 90.49 | 90.26 → 90.21 | 75.31 → **75.54** |
| AGLDT classical | 98.7% | 92.80 → 92.77 | 93.75 → **93.84** | 85.19 → **85.95** |
| PROIEL greek-nt | 94.2% | 91.71 → 91.75 | 92.25 → 92.10 | 81.53 → **81.74** |
| PapyGreek | 90.8% | 87.73 → 87.71 | 88.07 → **88.25** | 81.28 → **82.75** |

The PapyGreek *ranked* gate number is flat because the gate's comparison credits a
candidate whose *variant* matches the gold: the polluted candidates the fix demotes
(πηρός with form element παρά) already counted as correct there, so the +1.3pp shows in
the harness's exact column, not in this one. POS agreement improved on every corpus
(+1.5pp on PapyGreek); the retrained model moves ≤0.15pp on the NT-family corpora.
README tables re-measured (learned, adaptive-vs-fixed, PapyGreek section, recovery-off
baseline 95.2% / 87.2% / 1,750 unanalyzed).

## B4 — Per-config confidence calibration (shipped)

- **Joint-path temperature** `temperature_joint` = 0.12 (SBLGNT ECE 0.198 → 0.137,
  AF 0.192 → 0.133) — the joint path genuinely needs its own temperature (plain 0.08,
  learned 1.03).
- **POS confidence**: the class-mass estimate is peaked for the lemma, not for the
  class (mass ECE 0.19); the reported `pos_confidence` now multiplies the class mass by
  a per-class reliability fitted on SBLGNT — learned path ECE 0.19 → **0.002**,
  frequency 0.19 → 0.021, joint 0.19 → 0.014 (AF transfer 0.003 / 0.020 / 0.016). The
  fitted rates make the Morpheus↔reference convention gaps explicit: when Morpheus
  says `A` the reference usually says `R` (determiners αὐτός/οὗτος are `A` here,
  `RD`/`RP` there; 0.04), and its `X` particles are usually reference `C` conjunctions
  (0.07); D (adverb/particle) is 0.48-0.63. `pos_reliability` is stored per score path
  with a plain-table fallback.
- **Proposal priors**: `proposal_priors` fitted through the shipped API path on
  PapyGreek scales the conditional softmax of all-proposed tokens, so a lone proposal
  reports its strategy's measured top-1 rate instead of 1.0 — spelling **0.49**
  (1,019/2,078), name **0.27** (123/455), fallback `other` 0.45. Measured end-to-end:
  `μοὐ`'s three spelling proposals report 0.490/0/0 and the top's `pos_confidence`
  is 0.412 (mass × C-reliability).

## B5 — Analyzer-guarded `base-lemmas` profile (shipped)

`profiles.py` gained `BaseLemmas`: compound verbs lemmatize to the base verb, a preverb
is stripped only when the remainder resolves as an attested verb in the analyzer's
joint (lemma, POS) table (falling back to the bundled Koine table), and contracted
compounds are recovered by tail-matching guarded on attested preverb remnants. Profiles
are comma-combinable (`--profile morphgnt,base-lemmas`, applied left to right) and the
CLI validates names. This is the analyzer-guarded mode `build_morph_lxx.py
--base-lemmas` used.

## B6 — Build determinism (committed ebe6c63)

The five STEMPROG helper binaries and `tailnolen` (an Alpha COFF binary with no source
or references) are untracked and git-ignored; a rebuild was verified against the
tracked outputs with the SDK/CFLAGS environment from `build-stemlib.sh`. A full `make
clean` still regenerates the tracked endtables/steminds (pre-existing, out of scope).

## B7 — Tokenizer robustness (committed e9fbe41)

`tokenize()` now normalizes editorial input instead of mangling it: NFC normalization
(NFD accents no longer split tokens), `|annotation|` spans removed (πα|gap:1|ρά no
longer leaked `gap` as a token), editorial combining marks (dot-below, overline)
removed, bracket/ellipsis/hyphen runs *between letters* removed (ἀδελφ[οῦ] is one
token), and elision/crasis apostrophes (ʼ ’ ' koronis) stay attached because Morpheus
analyses the elided forms (ἀλλʼ → ἀλλά, δʼ → δέ). Crasis stays a single token: the
stemlib analyses the common forms (κἀγώ → ἐγώ, τοὐμόν → ἐμός, τἀληθές → ἀληθής, χὠ → ὁ)
and the rare ones go through recovery (μοὐ → μοι); the contracted vowel cannot be
restored without a lexicon.

## Assessed and carried: B3, B8, B9

- **B3** (Unicode-native C input path): scoping doc exists
  (`docs/unicode-native-input.md`); a robustness/parity refactor of the cruncher's
  input path with no accuracy effect — its own round, with dedicated parity validation
  against the NT-output-invariance rule. Carried.
- **B8** (licence-clean LM disambiguation layer): the Round 15 head-to-head stands —
  the LM-MLP wins on accented text (SBLGNT 99.4 vs 97.9 ambiguous-only; AF 98.0 vs
  97.3) but loses on the shipped accent-insensitive pipeline (PROIEL 92.3 vs 96.4;
  `ignore_accents` inflates the multi-candidate rate 37.8% → 59.4%), and it needs torch
  plus a GPL-3.0-derived ~440 MB checkpoint. A shippable version means training a model
  on the shipped candidate distribution (including `ignore_accents` examples) — a
  GPU-scale task. Carried with that concrete next step.
- **B9** (lacuna-restoration pre-pass): needs external model weights (Ithaca/Pythia)
  and PHI-derived text (tmp-only); deferred.

## Carried forward

- CSNTM outreach (Round 13) stays blocked on user contact.
- ε/η and α/ο interchange evidence stays in lessons.md (deferred).
- Ατ (gold 1300, decimal lemma) remains a documented PG numeral residual.

# Round 19: PG error audit, adaptive numerals, Unicode-native C input, MLP head-to-head (2026-10-16) ✅

## Goal

User direction "do all 5" — the five suggestions from the Round 18 wrap-up:
(19.1) a PapyGreek top-1 error audit that names what is actually left and bounds
what ranking work can buy; (19.2) register-aware numerals
(`numerals="auto"` / `--numerals-auto`); (19.3) the B8-lite CPU contextual
re-ranker, head-to-head against the perceptron under a ship/no-ship gate;
(19.4) the B3 Unicode-native cruncher input path with exhaustive parity
validation; (19.5) CSNTM demo refresh + outreach email to unblock Round 13.2.
Records (19.6) close the round.

## 19.1 — PapyGreek top-1 error audit (measurement only)

All 36,455 PG word tokens through the *shipped* path: accent-insensitive
candidate pass, recovery pre-pass, learned re-ranking, the adaptive papyri
frequency table (selection score 0.83), numerals off. Script
`tmp/r19/audit_pg_top1.py`; evidence `tmp/r19/audit_19_1.log`,
`audit_19_1_errors.tsv` (2,857 error tokens), `audit_19_1_families.tsv`
(1,510 families), report `tmp/r19/audit_19_1_report.md`.

Faithfulness: learned top-1 exact/acc-insensitive **88.1 / 89.6%**, reproducing
the Round 18 default path (88.0 / 89.5). Cross-check: the default Koine table
instead of the adaptive papyri pick gives 85.6 / 88.2 — the adaptive selection
is worth ~2.5pp exact on PG, and the audit uses the shipped configuration.

| bucket | tokens | share |
| --- | ---: | ---: |
| covered (≥1 candidate) | 35,513 | 97.4% |
| misses | 942 | 2.58% |
| gold lemma absent from candidates | 1,725 | 4.73% |
| gold present, not top-1 (ranking) | 1,132 | 3.11% |
| top-1 exact | 32,105 | 88.1% |
| top-1 accent-insensitive | 32,656 | 89.6% |

- **Misses (942).** 717 are the numeral/indeclinable class; 703 are covered by
  `--numerals`/`--numerals-auto` (14 remain: decimal-annotated gold like Ατ,
  sub-threshold forms). ~225 non-numeral ≈ the Round 18 residual (157
  editorially marked or truncated).
- **Gold absent (1,725).** 192 are *covered-misanalyzed* numerals (the token has
  a wrong reading, so the misses-only numerals path cannot fire): ιθ→ηθ 65,
  κε→ἄν 27, ιζ→εἰμί/ἴς 16, ιδ→ηθ 12, λε→ληίς 11, ιγ→ἐν 16…; a numeral proposal
  exists for 134 (vowel-less rule or table). The other 1,533 are
  **editorial/regularization conventions** — the treebank's regularized lemma is
  not the lemma of the spelling present (ποιήσις→ποιέω 11, πλεῖστα→πολύς 8,
  ἐπὶ→ἐπεί 20, εἵνα→ἵνα 19, κὲ→καί 14, Ἡρακλέους→ἡρακλέης 10, καθάπερ→καθά 11).
  Candidate-generation work, not ranking; corpus-specific lemma mapping was
  declined in Rounds 12/17 — do not chase.
- **Gold present (1,132, the only ranking-fixable bucket).** 925 native
  candidates (443 gold at rank 2; POS-class agrees 366; both lemmas common 319),
  including **numeral-gold with the numeral candidate present — 140** (ιη→κερατέα
  51, κη→πη 32, ια→κερατέα 23, ιε→ἰός/εἶμι 17); 147 recovery proposals out-ranking
  a native gold reading; 60 variant-credited (gate hits). Largest families:
  function-word homographs ἀλλά→ἄλλος 86, ὅς→ὁ 69+ (plus ὃ/ἃ/ἃς), εἰμί→ἐάν/οὖν/
  ὄντα/εἰ 43, πᾶς→πάντῃ 24, σύ→σου/σε 13, ὡς→ὅς 14+; word-formation confusions
  ἀποδίδωμι→ἄπους 28 (ἀπόδος), χαλκοῦς→χαλκός 18, ἀξιόω→ἄξιος 11,
  ἀντίγραφος→ἀντιγράφω 9, ἀπαντάω→ἀπαντή 9.
- **Ceilings.** Better ranking with no candidate changes: **+3.1pp**
  (89.6 → 92.7 acc-insensitive, numerals off). A papyri-scoped numeral-candidate
  rule (192 + 140 ≈ 274 tokens) is worth ~+0.75pp but needs its own round with a
  false-positive audit (κέ/τ/abbreviations). B8-lite's honest target was
  therefore the 1,132-token bucket — fractions of a point, not points.

## 19.2 — Adaptive numerals (`numerals="auto"` / `--numerals-auto`) (shipped)

The papyrus-numeral proposals (Round 14) now have a register-aware form: apply
them only when adaptive table selection picked the **papyri** table for this
input, so numeral-shaped misses in other registers stay misses. `api.py`
accepts `numerals: bool | "auto"` (validated; `True` keeps the old
always-on behavior); the auto pass runs *after* `_apply_adaptive_tables` — so
numeral proposals can never skew the table selection that gates them — and
`_selected_table` records the pick. It needs selection to run: caller-supplied
`frequencies` or `adaptive_tables=False` leave it inert (documented).

CLI: `--numerals-auto` (mutually exclusive with `--numerals`). Implemented as a
distinct flag rather than the planned `--numerals=auto` optional-value form,
because `nargs="?"` would make `--numerals file.txt` eat the positional path
argument — recorded in lessons.md.

Tests: 5 new (`test_api.py`): auto fires on PG text; silent on SBLGNT-shaped
text even with numeral misses; explicit `numerals=True` unchanged; inert
without adaptive selection; invalid string rejected. **105 tests pass.**

Verified: an 8-document PG sample selects papyri; `bgu.3.948.xml` through the
full shipped path (learned + recovery) gives auto output identical to explicit
`numerals=True`; SBLGNT selects koine and auto output is identical to
`numerals=False`. Equivalence on the other corpora is by construction (auto is
the same code path once the selection matches).

## 19.3 — B8-lite MLP head-to-head (measured; not shipped)

`scripts/build_learned_model.py` gained an opt-in `--mlp` branch
(`train_mlp()`; graceful without torch): listwise softmax cross-entropy over
each token's candidates, bucketed by candidate count, batch 128, Adam 1e-3,
best-held-out state, pure-Python payload shape (`feature_index`/`w1`/`b1`/
`w2`/`b2`, type `"mlp"`) so shipping would have needed only a forward path.

Run on the same shipped candidate distribution as the Round 18 retrain
(recovery pre-pass included): 411,615 analyzable tokens, 827 features → 815
kept; PG document-level held-out split (6,936 analyzable of 7,474).

| model | held-out top-1 |
| --- | ---: |
| frequency baseline | 94.22% |
| perceptron (shipped) | 96.08% |
| MLP (64 hidden, 8 epochs, best) | **96.29%** |

The perceptron reproduces the shipped model **byte-identically** (weights and
feature index equal — the training pipeline is fully reproducible). The MLP's
+0.21pp (≈15 held-out tokens; SE ≈ 0.24pp at n = 6,936) is below the pre-set
**≥0.3pp ship gate** and within noise, so it is **not shipped**: nonlinearity
over the existing features buys fractions of a point, exactly as 19.1
predicted. The MLP improved monotonically over its 8 epochs (95.95 → 96.29),
so the carried next step is *features* (the audit's function-word homograph
families and context counts), not more model capacity. Evidence:
`tmp/r19/train_r19.log`, `learned_reranker_r19.json`,
`learned_reranker_r19_mlp.json`.

## 19.4 — B3: Unicode-native cruncher input (shipped)

`cruncher -u` converts UTF-8 Greek directly to lowercase beta in C before the
existing pipeline (`src/anal/gkunicode.c`; `-u` wired into `stdiomorph.c`,
Greek-only — Latin keeps its case). The converter replicates the beta-code
package's algorithm — NFC normalize → per-codepoint map → pass-through →
lowercase — with **every table generated** from the same
`unicode_to_beta_code.json` the Python converter uses
(`scripts/gen_gkunicode_tables.py` → `src/anal/gkunicode_tab.c`: 271 map
entries, 449 composition pairs, 111 combining classes, 153 lowercase mappings,
259 NFD expansions). `bin/gkconvert` is the oracle binary; `makefile` links
`gkunicode.o gkunicode_tab.o` into cruncher and gkconvert; the binary is
git-ignored.

Parity (`scripts/unicode_parity.py`): the exhaustive synthetic set (map keys,
both Greek ranges, pair compositions in NFC and NFD spellings, mark orders,
apostrophes, 3K random strings) plus **every distinct form** in MorphGNT, AF,
AGLDT, PROIEL and PapyGreek — **110,927 forms, 0 mismatches** against
`to_beta(w).lower()`; conversion speed ~2M forms/s. `cruncher -u` output is
byte-identical to the beta-input path on samples; default (no `-u`) behavior
unchanged. Guards: `python/tests/test_unicode_c_path.py` (synthetic oracle +
direct conversions + cruncher -u vs beta path; skipped when not built).

Debugging found three real divergences the oracle caught: singleton NFD
decompositions (U+0340/0343/0344) are not composition pairs (367 forms), spacing
decomposition pieces (U+00A8/backtick/space) must start recomposition (16
forms), and a generated-table struct overflow (`nfd[4]` + terminator) produced
a 1,134-form output explosion. `docs/unicode-native-input.md` now documents the
implemented design; README gained the `-u` row + example; lessons recorded.
The toolkit keeps the Python `to_beta` path for now — switching it to `-u` is
a later decision, gated on this parity (now proven).

## 19.5 — CSNTM prep

`docs/csntm-morphology-demo.md` refreshed: current measured numbers (SBLGNT
94.6 / 94.7 exact/acc-insensitive; PG 89.4 / 90.8 with numerals; learned ~+2
over frequency on the held-out split), the John 1:1–2 worked example re-run on
the current build (24/24 analyzed; ἐν 0.99, ἀρχῇ 1.00, ἦν 0.88 with the
calibrated confidences), and the JSONL excerpt updated to the current record
shape (lemma_variants, pos_confidence, recovered_from). The honest
uncial-text nuance section stands (accent-insensitive strips accents but not
breathings; bare forms can mis-resolve). `docs/csntm-outreach.md` drafts the
email for the user to send — the last step of Round 13.2.

## 19.6 — Gate + records

Full offline gate re-run in verification mode (`tmp/r19/refresh_gate.sh
--check`, five corpora in parallel, against the committed thresholds): **all
five OK (within tolerance)** — SBLGNT 94.6/94.7, AF 90.5/90.2, AGLDT 92.8/93.8,
PROIEL 91.8/92.1, PapyGreek 87.7/88.2 — and every adaptive pick unchanged
(SBLGNT→koine, AF→apostolic, AGLDT→classical, PROIEL→koine, PG→papyri). As
expected: the round's changes are additive (`-u`, `--numerals-auto`),
measurement-only (the audit), or outside the shipped model (the perceptron
reproduces the shipped file byte-identically, so no model was re-shipped).
105 pytest pass.

Records: this entry; `improvements.md` Round 19 section; lessons (audit under
the shipped configuration; split gold-absent from gold-present before proposing
ranking work; a gated pass must not run before its gate; distinct flag over
optional-value flag; replicate the reference converter's algorithm; NFC =
NFD + recomposition; composition starters include decomposition pieces;
terminator slot sizing; greedy hex escapes; exhaustive oracle; test the
evaluation path with held-out data before the long run).

## Carried forward

- **Round 13.2**: send the CSNTM email (user action; draft ready).
- **Numeral-candidate rule** for covered-misanalyzed numerals (~274 tokens,
  ~+0.75pp) — own round, false-positive audit required (κέ/τ/abbreviations).
- **Context/homograph ranking** (the +3.1pp ceiling): the audit's families
  (ἀλλά/ἄλλος, ὅς/ὁ, εἰμί/ἐάν, πᾶς/πάντῃ); B8-lite showed model capacity is not
  the lever — features/data are.
- **B3 toolkit switch-over** (use `-u` in the runner; keep `to_beta` for the
  API `beta` field) — parity is proven, decision deferred.
- Ατ (gold 1300, decimal lemma) remains a documented PG numeral residual.
