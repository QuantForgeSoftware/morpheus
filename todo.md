# Active plan

The active plan is **Round 12 (private-corpus coverage harvest)**; **Round 13** (CSNTM /
NT-manuscript outreach) and **Round X** are queued proposals. Round 11 is complete (record
in [completed.md](completed.md)); [improvements.md](improvements.md) carries the measured
gains to date.

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

# Round 12 (proposed) — license-safe private-corpus coverage harvest

**Context.** TLG/PHI are private and license-restricted, but their stated terms **permit
personal study** (PHI: *"use this website only for personal study and not to make copies
except for my personal use"*). This round does only the part that is safe: mine the
private copies **locally** (`tmp/`, git-ignored) to find *systematic* coverage gaps, and
commit **only generic stemlib entries justified by public lexica**. **Nothing
TLG/PHI-derived is committed.** Target register: Greek documentary (the PHI7 Greek CD of
inscriptions + papyri — the register Morpheus is weakest in, cf. PapyGreek's 92.9%
coverage after Round 8).

**Inputs:** PHI7 Greek documentary CD (user's copy); LSJ at
`/Users/johnbaima/Code/bibloi/data/lsj-logeion` (public-domain LSJ XML) for justifying
entries; the PapyGreek marker-stripping inventory in `lessons.md`.

**PHI7 format found (2026-10-15).** `/Users/johnbaima/Code/PHI7` = TLG beta
(**UPPERCASE**; `*` marks a capital) with Leiden-style markup: `[…]` restorations,
`[…]`/`!`/`?` underdots, `{…}` variant readings, `_ _` lacunae, plus numeric codes
(`#nn`, `#8X` standalone diacritics, `%n`), `&xx`, `$n`, `@n`, and `\x7f`-delimited
record/tag metadata. Per-file `.IDT` indexes + `AUTHTAB.DIR` region directory. Regions:
`INS` inscriptions (~49 MB), `DDP` documentary papyri (~45 MB), `CHR` Christian
(~12 MB), `COP` Coptic (excluded).

**Parser (user's own, for reference/porting).** `BetaExport` (Delphi) — `ExportFormat.pas`
(+ `*Beta/HTML` formatters), with library units under `…/Smsprog/Novisual/`
(`Idtparse.pas`, `Idtnib.pas` = TLG nibble **citation** decoder; `Adjgreek.pas` =
beta→Unicode + markup engine) and `…/Smsprog/Common/` (`Cdref.pas`, `Adjuni.pas`); docs
`Beta Code Export.doc` + the `Default.css` markup legend; a clean sample export in
`BetaExport/Output/test3.txt`.

**Extraction status — SOLVED, no parser port needed (2026-10-15).** PHI7 `.TXT` stores all
reference/metadata (region, author, work, citation values, the nibble codes) as
**high-ASCII bytes (≥0x80)** and the **beta text as plain 7-bit ASCII (<0x80)**. Dropping
`b >= 0x80` yields clean beta text; then strip TLG/Leiden markup (`#nn`/`%n`/`&xx`/`@n`/`$n`/`^n`,
bracket/brace wrappers `[ ] {n…}n <1…>1`, `_` lacunae, `!`/`?` marks, line-break hyphens).
Extractor in `tmp/phi/probe.py`. **Validated against the user's `BetaCode/Attica.TXT`
export: 99.6% distinct / 99.9% token overlap** (raw extraction is a superset). Reference
bytes can be decoded separately later (for per-work attribution) if wanted.

**Actionable subset (2026-10-15).** Of the 26.5% missed token mass:
- **~50% is ≤4-letter fragments** (`tro\s`, `uri/ou`, `dra x`) — inherent, not fixable.
- **~21.5% (466,789 tokens) is name-like** (`*` + ≥4 letters: `*peqe/ws` = Πεθεύς,
  `*)antwnei/nou` = Ἀντωνείνου, `*seouh/rou` = Σεουήρου, `*(wri/wnos` = Ὡρίωνος,
  `*)onnw=fris` = Ὀννῶφρις, `*macimianou=` = Μαξιμιανοῦ, plus truncations) → the biggest
  systematic bucket; a generated **proper-name** source (PapyGreek `nom.papyri` precedent)
  addresses it.
- a **documentary word family** (`mi/smata`/`misma/twn`/`misma/tion` = μίσμα/μισμάτιον ×~15K),
  a few real verb forms (`pro/kitai` = πρόκειται), and **~17K numeral tokens** (`iiii`).
- **Tokenizer leak**: leading stray letters from line-splits (`sdiagrafome/nwn`) — fixable.

**License narrowing for 12.3 + LSJ filter result (2026-10-15).** The *selection* (scanned
from PHI) stays in `tmp/`; only entries **attested in public references** (LSJ lemmas —
Unicode, public-domain TEI at `/Users/johnbaima/Code/bibloi/data/lsj-logeion`) may be
committed. Matching the 383,888 missed distinct forms against LSJ (`tmp/phi/lsj_filter.py`,
accent-stripped skeleton + stem + plausible-ending rule, LSJ prefix-entries excluded) finds
only **14,097 forms / 61,318 tokens = 2.8% of missed tokens** (≈**0.75% of the corpus**)
attested, mapping to **6,127 candidate lemmas** — and these are still fragment-contaminated
(`ριον`, `σεως`, `ρακος`, `ρους`); the genuinely real ones are a curated subset
(ὑοθεσία, Ἡρακλῆς, Σάραπις, Θερμοῦθις, δῆμος, στῆλη, εὐλογία, ἀρτάβη, στῆλη, …).

**Conclusion (so far):** PHI documentary coverage is **73.5%**, but the gaps are dominated
by *fragments* (inherent to broken texts) and by *proper names that are not in LSJ* (so
not committable under the license-clean rule). The **license-clean actionable upside is
modest** (~0.75% of tokens at best, minus curation) — this vindicates the earlier "coverage
probe only / probably not a windfall" stance, now with data. Remaining options: a curated
LSJ-attested word/name addition, a numeral table, and the line-split tokenizer artifacts.

- [ ] 12.1 Build a `tmp/phi/` probe: parse the PHI7 data (beta code; reuse the PapyGreek
      marker-stripping), run `cruncher`, collect the unanalyzable tokens. Greek only.
- [ ] 12.2 Cluster the misses and separate **systematic** gaps (a missing paradigm, a
      dialectal class, a name family) from one-off damage. Only systematic gaps are
      actionable — no fishing.
- [ ] 12.3 For each systematic gap, add a generic entry (e.g. into `nom.papyri` /
      `vbs.papyri` or a new generated source) **justified and checked against LSJ** (and
      other public references). Rebuild and verify.
- [ ] 12.4 Cross-check against the PapyGreek ALDT gold so existing coverage isn't
      duplicated.
- [ ] 12.5 Where an open corpus (First1KGreek / Open Greek and Latin, CC BY-SA) covers the
      same ground, prefer it and commit from there.
- [ ] 12.6 Re-baseline the benchmark gate; document **method/counts only** — no
      PHI/TLG-derived data in any committed file.
- [ ] 12.7 Round wrap-up (required every round): re-evaluate and update
      [`improvements.md`](improvements.md); migrate the completed record to
      [`completed.md`](completed.md).

**Hard license guard:** nothing PHI/TLG-derived (text, miss lists, frequency or
normalization tables) may be committed; `tmp/` only. Generic dictionary entries (the
words/forms themselves) are fine; the *selection scanned from PHI* stays in `tmp/`.

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

- [ ] B1. Validate and then **default** `--learned` and `--adaptive-tables` (all corpora
      incl. LXX and PapyGreek; default only if it matches-or-beats the best single
      table / frequency ranking everywhere) with an opt-out.
- [ ] B2. **Proper POS/sequence model** (CRF or small neural) with learned emissions
      `P(lemma | tag)` — the piece `python/README.md` names as missing. (Round 11 tested
      the bigram tagger again and it still loses to frequency ranking; a learned-emission
      model is the real lever.)
- [ ] B3. Implement the **Unicode-native C path** (`docs/unicode-native-input.md`).
- [ ] B4. Per-config confidence calibration (freq / joint / learned) and a calibrated
      **POS** confidence.
- [ ] B5. Finish the profile registry: analyzer-guarded `--base-lemmas` mode.
- [ ] B6. Cross-environment build determinism: the tracked STEMPROG helper binaries
      (`stemsrc/{stripref,zapfirstf,headnolen,goodstem,flatlems}`) still change on
      `make clean`.
- [ ] B7. Tokenizer robustness: crasis / multiword tokens and editorial-mark
      normalization as first-class behavior.

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
