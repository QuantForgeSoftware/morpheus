# Active plan

**Round 19** (PG top-1 error audit + adaptive numerals + B8-lite + B3 + CSNTM prep) is
**complete** (record in [completed.md](completed.md)): B3 shipped (Unicode-native C
input, parity-proven), B8-lite measured and carried (MLP +0.21pp held-out — below the
ship gate; features, not capacity, are the next lever), and 19.5 refreshed the CSNTM
demo and drafted the outreach email. **Round 13 is open, not done.** Do not send
13.2 on the Round 19.5 draft — it led with accented-text accuracy and cited
PapyGreek as if it were NT-manuscript performance. The corrected draft is
[`docs/csntm-outreach.md`](docs/csntm-outreach.md) (2026-10-16); sending is still
the user's action. **Round 20** (NT passage-constrained analysis) is **proposed,
not approved**. Its feasibility note is a prototype — one simulated page plus a
non-blind spot-reading — not a ship result. Rounds 11–19 are complete (records in
[completed.md](completed.md)); [improvements.md](improvements.md) carries the measured
gains to date.

---

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

# Round 13 (open) — CSNTM / NT-manuscript morphology outreach

**Context.** Daniel B. Wallace (the user was an early student) is Executive Director of
the Center for the Study of New Testament Manuscripts (CSNTM). CSNTM's current flagship
technical project is **"AI for Manuscript Transcription"** — training a model to read
ancient Greek NT manuscripts into *searchable digital text* (alongside the new Digital
Manuscript Collection, Feb 2026, and the Bodleian/Oxford digitization expedition).
Morphology is the natural layer after recognition: lemma tagging, lemma/parse search, and
morphological-vs-orthographic variant classification for collation. **Corrected
2026-10-16:** Round 12's documentary abbreviations do **not** transfer here. NT
manuscripts need nomina sacra, itacism, and scriptio continua, not PHI documentary
shorthand. Rounds 12 and 13 do not feed each other.

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

**Verdict (2026-10-16, re-measured — supersedes the Round 13 finding):**

- **Three regimes, not one number.** SBLGNT 94.6/94.7 is accented critical text.
  PapyGreek 97.4% coverage and 89.4/90.8 top-1 is *documentary* papyri, not NT
  manuscripts. Fully bare NT text (accents and breathings removed) is a third
  task: John 1–3, n=1,913, toolkit API with `--ignore-accents`, **74.0%**
  accent-insensitive top-1 vs **93.2%** on the same accented tokens. That 93.2
  is not the gate (94.6/94.7) — do not cite them as the same measurement.
  "100% analyzed" on John 1:1–2 is **coverage of 24 tokens**, not lemma accuracy.
- **The `εν` mechanism was misstated.** Matching under `-n` ignores accents
  (`stripacc`: acute/grave/circumflex only) and does **not** ignore breathings.
  The breathing retry (smooth, then rough) runs only when `checkstring` misses
  entirely. Bare `en` is a miss without `-n`. With `-n` it hits **epic ἔν**,
  εἰμί imperfect 3pl (`e/n,ei)mi/`), and because that is the only candidate the
  API reports **confidence 1.0**. `e)n` is ἐν at 0.99. So the flag the draft
  recommended *creates* the high-confidence wrong reading; confidence does not
  "help where breathings don't." Without the flag, recovery proposes εἰ (0.49),
  not εἰμί — the published example is true only of `--ignore-accents`.
- **Round 20 is not "exactly this fix," and it is not shipped.** Passage
  alignment can restore diacritics where the manuscript's letters agree with a
  base text, complete partials, and *report* disagreements. It does not fix
  non-NT text, and it must not silently replace a real variant with the edition.
  The prototype's restored-accuracy column did exactly that substitution — do
  not cite 62.5% → 90.3% as the design. The clean diacritic-only gap is the
  John 1–3 pair above.

---

# Round 20 (proposed, pending check-in) — NT passage-constrained analysis (the CSNTM layer)

**Context (user direction 2026-10-16).** CSNTM's manuscripts are all *versions of
the NT* — a **known text**. That is a structural advantage over every other corpus:
a transcription (even unaccented, damaged, continuous) can be **aligned to a base
text** (e.g. SBLGNT), and the alignment then (a) restores the diacritics the
manuscript never had, (b) completes partial words and fills lacunae, and
(c) flags divergences from the base as **candidate variants** — the collation
signal itself. Textual variants are the *feature* here: the layer must never
silently correct them away, only classify and report. This supersedes B9's
generative lacuna restoration **for NT texts** (deterministic, no external
weights, no licensing exposure).

**What the prototype actually showed** (`tmp/r20/passage_proto.py`,
`tmp/r20/passage_proto_results.txt`; one page, one seed, text derived from the
base it was aligned to):

- Passage ID on that page: top-1 at John 5:1, ratio 0.951 vs 0.21 for the best
  *distant* region. The "top-3 all true" line is not three confirmations — the
  third hit (John 4:52, ratio 0.70) is a boundary overlap, marked true only
  because the window test was ≥50%.
- 11/11 prefix completions and 4/4 lacuna fills are nearly tautological once
  the region is correct and the damage is a prefix or a deletion. They are not
  a detection rate. 10/10 "variants flagged" is the wrong success metric: those
  injections were orthographic interchanges (αι/ε, ο/ω), which the design says
  should be classed as orthographic, not substantive. The prototype had no
  equivalence classes, so it flagged all of them.
- Do **not** cite page 62.5% → 90.3%. That mixes truncation with diacritic
  loss, and the restored column substituted the edition token even where a
  variant had been injected — the opposite of "never silently correct."
- The number that is worth keeping: John 1–3 undamaged, same API flag, bare
  **74.0%** vs accented **93.2%** (n=1,913). Residual misses on restored forms
  (ἀπεκρίθη→ἀποκρίνω, εἶπεν→εἶπον, ἐγένετο→γίγνομαι) are analyzer conventions,
  not alignment errors — on that one page.
- P46 spot-reading (`tmp/r20/papyri/reading_notes.md`) is a sanity check, not a
  result. The site already labeled the leaf Rom 5:17–6:3. A few hand-segmented
  strings, after ς→σ normalization, intersect there; "ὁ θάνατος ἐβασίλευσεν" is
  unique at 5:17. Not a blind ID, not a full transcription, not a variant find
  (the strings read agree with SBLGNT).

**Do not claim,** in the email or the demo: a shipped aligner; 11/11 or 10/10
as evaluation; PapyGreek as NT-papyrus accuracy; confidence as a guard on bare
function words; "100% analyzed" as accuracy.

**Proposed scope:**
- [ ] 20.1 `passage.py`: base-text index (k-gram + ratio verification) + token
      alignment with classes (equal / partial / orthographic-equivalent /
      substantive divergence / lacuna / extra); base text supplied by the caller
      (MorphGNT dir or plain text; nothing committed).
- [ ] 20.2 Manuscript input handling: nomina sacra table (θς/κς/ις/χς/πν(α)…),
      scriptio-continua mode (word boundaries derived from the edition), the
      existing tokenizer's editorial marks; three-way variant classification
      (orthographic equivalence vs substantive divergence).
- [ ] 20.3 Outputs: per-token annotation (`aligned_to`, restoration class,
      passage-confidence) in the JSONL; a variants TSV (manuscript reading, base
      reading, ref, class); refuse below a confidence threshold.
- [ ] 20.4 CLI: `morpheus-toolkit align transcript.txt --base-text DIR`.
- [ ] 20.5 Evaluation, still open. The 2026-10-16 image spot-check does not
      close this item. A real eval needs blind pages, scriptio continua, nomina
      sacra, synoptic parallels, and heavier damage — plus a full transcription
      whose license is actually checked. "P.Oxy. pre-1930 = public domain" is
      too coarse to commit a fixture on (volume, jurisdiction, and any EES
      claim). Sanders 1935 stays out of committed files. A CSNTM sample is a
      *follow-up*, not the first email.
- [ ] 20.6 Records when the round actually closes. The demo and email honesty
      fixes are done (2026-10-16); they do not describe passage alignment as
      shipped.

**Still open:** proceed with 20.1–20.4? Sending 13.2 is unblocked by the draft
correction, but it is still the user's action — and email 1 does not ask for
data. Image → transcription is a separate plan ([ocr.md](ocr.md)); Round 20
assumes a transcription already exists. Do not fold HTR into 20.1.

---

# Candidate follow-ups (carried from Round 11 Item B)

B3, B4, B5, B6 and B7 are complete (Round 18/19 records in
[completed.md](completed.md)).

- [ ] B8. **Contextual disambiguation layer** — Round 15's transformer head-to-head
      regressed on the shipped accent-insensitive pipeline (PROIEL 92.3 vs 96.4 —
      `ignore_accents` inflates the multi-candidate rate 37.8% → 59.4%) and needed
      torch + a GPL-3.0-derived ~440 MB checkpoint. Round 19's licence-clean
      **B8-lite** (CPU MLP over the perceptron's own features, shipped candidate
      distribution incl. `ignore_accents`) reached 96.29% vs the perceptron's 96.08%
      on the PG document-level held-out split — +0.21pp (≈15 tokens, within noise),
      below the ≥0.3pp ship gate, so not shipped. Carried: the next lever is
      *features* — the 19.1 audit's function-word homograph families (ἀλλά/ἄλλος,
      ὅς/ὁ, εἰμί/ἐάν, πᾶς/πάντῃ) and context counts; the ranking-fixable ceiling is
      +3.1pp.
- [ ] B9. **Ithaca/Pythia lacuna restoration as a pre-pass** for fragmentary texts (the
      largest miss class in the Round 12 probe). The I.PHI-for-Round-12 part is retired
      with Round 12's close-out. Note: I.PHI's *text* is still PHI's → `tmp/`-only,
      commit-nothing-derived rule applies to any such experiment. (Round 18: carried —
      needs external model weights and PHI-derived text, both `tmp/`-only.) Round 20,
      if built, covers only the *known-text NT* case and does not retire B9.

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
