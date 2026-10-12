# Active plan — Round 9 (DRAFT — awaiting approval; nothing implemented yet)

Round 8 (new corpora: PapyGreek, Latin benchmark, PROIEL Greek NT cross-validation)
is complete and committed (`a2b7a77`, `1935b8f`); its full record lives in
[completed.md](completed.md). **User direction for this round: no Latin work**
("I don't care about Latin at all") — everything below is Greek. Working files go
in `tmp/<corpus>/` (git-ignored).

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

## Round 9 candidates (checkable; approve what to do)

1. **Classical Greek round** — first benchmark of Morpheus on the classical register:
   - Baseline: coverage / top-1 / coarse POS over AGLDT v2.1 Greek (per-author
     breakdown; epic/Ionic dialect will be the stress test).
   - Build `lemma_frequencies_grc.json` from AGLDT (`--format agldt` already exists
     in `scripts/build_lemma_frequencies.py`; Greek lemmas are Unicode with initial
     capitals — `normalize_lemma()` lower-cases them, same as every other table).
   - Safe stemlib additions from the manual gold (classical names; epic/Ionic forms
     like ἱστορίης, Ἁλικαρνησσέος), mirroring the PapyGreek round: generated +
     curated sections, count threshold, dictionary-form check, idempotent merge.
   - Guards: index key diff purely additive (zero collisions); AF/LXX/PG snapshots
     byte-identical or explained as endtable noise; pytest 33/33.
   - Independent cross-check: PROIEL Herodotus (`hdt.conll`, ~80K word tokens,
     CC BY-NC-SA → measurement/docs only, nothing committed).
2. **Contextual homograph disambiguation** — the biggest remaining Koine lever:
   - The residual profile above is stable across SBLGNT and PROIEL (item 3), so it
     is real signal, not convention noise. Round 6's hand-built bigram tagger did
     *not* beat plain frequency ranking; the README notes a *learned* emission
     model P(lemma | context) is what would pay off.
   - Train one on commit-safe gold only (SBLGNT + LXX + AF + PG, all CC BY-SA);
     scope it to the known homograph families first (ὡς/ὅς, εἰ/εἰμί, ἢ/εἰμί,
     τε/σύ, ὃ/ὁ) rather than a general tagger.
   - **Opt-in flag only — default behavior unchanged** (respects the Round-7
     "do NOT change NT-related behavior" direction); target +2–4pp top-1 on
     SBLGNT/AF/PapyGreek, verified to transfer to PROIEL.
3. **PapyGreek numerals** — recover the 853 numeral tokens (~2.3pp of papyrus
   coverage) with a dedicated opt-in numeral mode: alphabetic numerals (αʹ βʹ γʹ…)
   and spelled-out forms (χίλιοι, ἑκατόν). They collide with real words, so this
   must be a flagged mode or explicit entries — never silent stemlib additions.

## Not doing (standing constraints)

- Any Latin work (user direction for Round 9); the Round-8 Latin benchmark + table
  remain as committed, untouched.
- PROIEL-derived content in committed files (CC BY-NC-SA; measurement/docs only).
- NT behavior changes (Round-7 direction): no stemlib edits that alter SBLGNT/NT
  output to fit another edition's conventions.
