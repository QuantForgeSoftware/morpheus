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
