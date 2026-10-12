# Active plan — Round 9: classical Greek, contextual homographs, papyrus numerals

Round 8 (new corpora) is complete and committed (`a2b7a77`, `1935b8f`); its full
record lives in [completed.md](completed.md). **User approved all three items**
("Do all 3"); standing constraints hold: no Latin work, PROIEL-derived content stays
out of committed files (NC-SA), default NT behavior unchanged. Working files go in
`tmp/<corpus>/` (git-ignored); the AGLDT clone lives at `tmp/agldt/`.

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
3. **PapyGreek numerals** (opt-in mode)
   - [ ] Inspect ALDT numeral gold (postag `m`): forms, lemmas, marker patterns.
   - [ ] Build bundled papyrus-numeral table from PapyGreek gold (CC BY-SA);
     opt-in flag emits synthetic analyses for unanalyzed numeral tokens
     (`unknown_as_proper` precedent) — never silent stemlib additions.
   - [ ] Verify: coverage gain on PapyGreek; AF/LXX/NT snapshots byte-identical;
     pytest 33/33.

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

## Not doing (standing constraints)

- Any Latin work (user direction for Round 9); the Round-8 Latin benchmark + table
  remain as committed, untouched.
- PROIEL-derived content in committed files (CC BY-NC-SA; measurement/docs only).
- NT behavior changes (Round-7 direction): no stemlib edits that alter SBLGNT/NT
  output to fit another edition's conventions.
