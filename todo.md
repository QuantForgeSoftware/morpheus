# Active plan

**Round 18** (canonical-lemma scoring fix + learned-feature cleanup + PG retrain with a
document-level held-out split) is agreed and deferred. **Round 13** (CSNTM /
NT-manuscript outreach) is queued pending the CSNTM contact; the remaining **candidate
follow-ups (B items)** and **Round X** are standing. Rounds 11, 12, 14, 15, 16 and 17
are complete (records in [completed.md](completed.md)); [improvements.md](improvements.md)
carries the measured gains to date.

## Standing constraints (carry into any future round)

- All temp/work files inside the morpheus folder (`tmp/`, git-ignored) — never
  `~/.lmstudio/scratchpads`. Read `Agent.md` first; plan in todo.md → check in before
  non-trivial implementation; verify before marking complete; update `lessons.md` after
  corrections. Push only when asked.
- **GitHub pushes allowed when asked; never run GitHub CI (revised 2026-10-15).**
  Earlier (2026-10-14) the direction was "no GitHub processing"; that is now: commit/push
  is fine on request, but **do not trigger GitHub Actions/CI** (they cost money). Include
  **`[skip ci]`** in every pushed commit message, and keep verification in the local
  scripts (`scripts/benchmark.py`, `pytest`) rather than CI.
- No Latin work (user direction); the Round-8 Latin benchmark + table remain as committed,
  untouched.
- PROIEL-derived content stays out of committed files (CC BY-NC-SA; measurement/docs
  only). Public dataset names (AGLDT, PROIEL) are fine in docs.
- **Private corpora (TLG / PHI) are personal-study-only:** nothing TLG/PHI-derived (text,
  miss lists, frequency/normalization tables) may be committed; `tmp/` only. See Round 12
  and Round X.
- NT behavior unchanged: no stemlib edits that alter SBLGNT/NT output to fit another
  edition's conventions.
- **Process (user direction, 2026-10-15):** always **migrate completed items from
  `todo.md` to [`completed.md`](completed.md)** when a round closes — `todo.md` holds only
  the active plan. And **every round's plan ends with an item to re-evaluate and update
  [`improvements.md`](improvements.md)**.

---

# Round 18 (agreed, deferred) — canonical-lemma scoring + learned retrain

**Context.** Morpheus's `form,lemma` candidate field pollutes frequency scoring: an
inflected-form element makes a zero-frequency lemma (πηρός) outrank a frequent one
(παρά). Scoring on the canonical lemma only is measured at **+1.2pp on the PG plain
path** (SBLGNT wash). The fix changes feature semantics for the learned model, so it is
held back to land together with a retrain on the shipped candidate distribution — now
also including PapyGreek (CC BY-SA, committable statistics) with a **document-level
held-out split** so the PG evaluation is honest (no same-document leakage).

- [ ] 18.1 **Canonical-lemma scoring fix (plain path)** — rank on the canonical lemma
      (not the form element); measure PG plain path (expect ≈ +1.2pp), SBLGNT wash;
      update tests.
- [ ] 18.2 **Learned-feature cleanup** — drop/repair features that encoded the polluted
      scoring; align the feature set with the shipped candidate distribution
      (Round 15 lesson: candidate generation defines the task).
- [ ] 18.3 **Retrain with PG + document-level split** — pool PG with the existing
      SBLGNT/AF/AGLDT pool (balanced; `--agldt-limit` precedent); train/evaluate with
      a document-level held-out split; report honest PG learned numbers + all gate
      corpora.
- [ ] 18.4 **Measurement + docs + wrap-up (required)** — full gate, PG re-measure,
      improvements.md Round 18 section, lessons.md; re-evaluate/update
      [`improvements.md`](improvements.md); migrate the completed record to
      [`completed.md`](completed.md).

---

# Round 13 (proposed) — CSNTM / NT-manuscript morphology outreach

**Context.** Daniel B. Wallace (the user was an early student) is Executive Director of
the Center for the Study of New Testament Manuscripts (CSNTM). CSNTM's current flagship
technical project is **"AI for Manuscript Transcription"** — training a model to read
ancient Greek NT manuscripts into *searchable digital text* (alongside the new Digital
Manuscript Collection, Feb 2026, and the Bodleian/Oxford digitization expedition).
Morphology is the natural layer after recognition: lemma tagging, lemma/parse search, and
morphological-vs-orthographic variant classification for collation. **Note:** the
documentary names / abbreviations / dialectal forms surfaced in Round 12 may also help
tag and align CSNTM transcriptions, so Rounds 12 and 13 feed each other.

- [x] 13.1 One-page demo: [`docs/csntm-morphology-demo.md`](docs/csntm-morphology-demo.md)
      (public-domain Greek only) — what the toolkit does, why it fits a transcription →
      searchable-text pipeline, a worked John 1:1–2 example with real output, the uncial
      caveat, and how to run it.
- [ ] 13.2 **User action:** contact CSNTM/Wallace to ask whether
      lemmatization/morphology is on their transcription roadmap.
- [x] 13.3 Reference integration: CLI + JSONL already shipped; added
      [`docs/csntm/lemma_index.py`](docs/csntm/lemma_index.py) (lemma / `--parse` search
      over the JSONL) + `docs/csntm/sample.txt`.
- [ ] 13.4 Round wrap-up (required every round): re-evaluate/update
      [`improvements.md`](improvements.md); migrate the completed record to
      [`completed.md`](completed.md). (13.2 pending, so the round stays open.)

**Finding for the CSNTM use case (recorded):** uncial manuscripts are unaccented
**and unbreathed**; the toolkit's `--ignore-accents` strips **accents but not breathings**,
so a bare form can mis-resolve (e.g. `εν` → εἰμί instead of ἐν). A breathing-restoration
or context-disambiguation step is a natural joint improvement. Demo uses accented
critical-text Greek, where the pipeline is clean (100% analyzed).

---

# Candidate follow-ups (carried from Round 11 Item B)

- [ ] B3. Implement the **Unicode-native C path** (`docs/unicode-native-input.md`).
      (Round 15 assessment: robustness/parity work, own round; no accuracy effect.)
- [ ] B4. Per-config confidence calibration — **freq and learned paths done (Round
      15)**; remaining: joint-path temperature + a calibrated **POS** confidence.
- [ ] B5. Finish the profile registry: analyzer-guarded `--base-lemmas` mode.
- [ ] B6. Cross-environment build determinism: the tracked STEMPROG helper binaries
      (`stemsrc/{stripref,zapfirstf,headnolen,goodstem,flatlems}`) still change on
      `make clean`.
- [ ] B7. Tokenizer robustness: crasis / multiword tokens and editorial-mark
      normalization as first-class behavior.
- [ ] B8. **Ancient Greek transformer LMs as the disambiguation layer** — head-to-head
      done (Round 15, `tmp/lm/head2head.py`): the LM-MLP beats the bundled learned on
      accented text (SBLGNT test 99.4 vs 97.9 ambiguous-only; AF 98.0 vs 97.3) but
      regresses on the shipped accent-insensitive pipeline (PROIEL 92.3 vs 96.4 —
      `ignore_accents` inflates multi-candidate rate 37.8% → 59.4%). Not shipped
      (torch + GPL-3.0-derived ~440 MB weights). Next: a licence-clean model trained
      on the shipped candidate distribution (incl. `ignore_accents` examples), then
      re-measure and decide.
- [ ] B9. **Ithaca/Pythia lacuna restoration as a pre-pass** for fragmentary texts (the
      largest miss class in the Round 12 probe). The I.PHI-for-Round-12 part is retired
      with Round 12's close-out. Note: I.PHI's *text* is still PHI's → `tmp/`-only,
      commit-nothing-derived rule applies to any such experiment.

## Explicitly out of scope (standing constraints)

- Latin work (user direction); PROIEL-derived content in committed files (CC BY-NC-SA;
  docs/measurement only); NT behavior changes; **any GitHub Actions/CI run** (pushes are
  fine with `[skip ci]` — see standing constraints).
- Coverage fishing already declined: classical one-off names/fragments, the LXX ἕως/ἠώς
  homograph, sub-threshold PapyGreek numerals, bare-letter numeral false hits.

---

# Round X — held private corpora (TLG / PHI): remember, but probably do not use

**Status: noted; the safe subset is planned as [Round 12](#round-12-proposed--license-safe-private-corpus-coverage-harvest).**
The user holds private copies of:
- **TLG** (Thesaurus Linguae Graecae) — very large, **untagged**, beta code;
- **PHI CD-ROMs** — the Latin texts, **and** a Greek CD of *inscriptions + documentary
  papyri* (also beta code; the register with the most headroom).

**Why they're tempting.** The PHI Greek documentary CD in particular covers the register
Morpheus is weakest in (epigraphic/papyrological Greek) at far greater scale than the
PapyGreek treebanks, so it could seed systematic coverage/stemlib additions the same way
the PapyGreek round did.

**Why we probably will NOT use them wholesale:**
- **Licensing:** PHI states its terms explicitly — *"use this website only for personal
  study and not to make copies except for my personal use under 'Fair Use' principles of
  Copyright law"*; the CD-ROMs were **licensed** to scholars/institutions. So **personal
  study/analysis is permitted**, but **any copy beyond personal use** (including committing
  PHI-derived text or lists to a repo) is **not** — regardless of a missing copyright
  notice or non-commercial intent; "fair use" authorizes the personal copy, not
  redistribution. TLG is all-rights-reserved/scholarly-use. Nothing TLG/PHI-derived may be
  committed: not the text, not the miss lists, not any frequency or normalization tables.
  `tmp/`-only if ever touched.
- **Untagged:** no lemmas/POS, so they cannot be training gold or a shippable ranking
  table — coverage probing only.
- **Fishing risk:** huge untagged corpora surface thousands of one-off misses that the
  rounds deliberately declined to add.
- **Overlap:** most PHI documentary text overlaps the PapyGreek treebanks and IGDS; only
  the residual would be new.
- **Open alternatives capture most of the value** and are commit-safe: First1KGreek /
  Open Greek and Latin (CC BY-SA).
- **PHI-Latin** additionally conflicts with the standing "no Latin work" direction.

**If ever revisited:** a private `tmp/`-only probe — normalize PHI/TLG beta (reuse the
PapyGreek marker-stripping inventory), collect unanalyzable tokens, separate *systematic*
gaps from one-off damage, add only generic entries justified by **public** lexica
(LSJ/Bechtel), keep all derived material in `tmp/`, and document method/counts rather than
content. Requires an explicit user decision first.

_Remembered; the safe subset is Round 12._
