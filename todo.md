# Active plan — Morpheus × Apostolic Fathers (Round 7)

Rounds 1–6 live in [completed.md](completed.md). **User direction: do NOT change
anything NT-related; improve Morpheus against the Apostolic Fathers corpus.**
All five approved items are implemented, verified and committed. Working files in
`tmp/af/` (git-ignored): evaluators (`eval_af.py`, `eval_out.py`, `bd_acc.py`,
`gaps_af*.py`), snapshots (`ev2_*.txt`, `ev3_*.txt`), driver outputs
(`morph-af/`, `morph-af-nocconv/`, `morph-af-top1/`), and the AF table sources.

## Round 7 plan (all complete)

1. ✅ **Commit the two toolkit fixes** (guard fix + matches_lemma hardening) —
   `d760a3e`. Verified: pytest 33/33; LXX rebuild byte-identical.
2. ✅ **AF convention table + annotation pipeline** — `scripts/build_morph_af.py`
   (`23b33d3`). Convention layer derived at run time from MorphGNT-derived gold
   with three guards (single target per source lemma, ≥10 tokens, and M==0: no
   agreeing trustworthy token for that choice). The M==0 guard rejects
   form-dependent splits — κύριος/κυρία gender (10 mismatching vs 613 agreeing),
   ἐγώ/κἀγώ enclitic (22/1198), ἐπεί/ἐπειδή (17/33) — which a plain single-target
   guard would have applied globally and broken. Rejected pairs are printed in the
   summary for auditability.
3. ✅ **Stemlib additions for elided forms** — `stemsrc/nom.elided` + rebuilt
   nomind (`259df21`). 13 elided forms (δι, κατ, παρ, μετ, ἀπ, ὑπ, ἐπ, ἀφ, ὑφ, ἐφ,
   καθ, μεθ, ἀλλ) mapping to the existing full-form lemmas; resolve only in
   accent-insensitive mode (`-n`), so default-mode behavior is unchanged and vbind
   is byte-identical.
4. ✅ **Bundle AF tables + repo tooling** — `lemma_frequencies_af.json` /
   `pos_bigram_af.json` in `python/morpheus_toolkit/data/` (neutral source label,
   LXX precedent); `scripts/agreement_report.py` gained `--frequencies/--model`
   flags (`23b33d3`).
5. ✅ **Upgrade the AF repo** — `tools/morpheus/analyze.py` rewritten as a
   self-contained mirror of build_morph_af.py (runtime-derived tables, no stale
   bundled copies; conventions on by default with `--no-conventions` escape); all
   15 `data/morph-morpheus/*.txt` regenerated + new `.fb` sidecars and
   `summary.txt`; README rewritten (reference-corpus name mentions removed);
   committed locally in the AF repo (`2b51d98`, branch `morpheus-analysis`)
   — **not pushed**.

## Review section

**Headline numbers** (63,222 Greek tokens; driver = accent-insensitive mode +
AF frequency ranking + top-1 candidate + convention layer):

| subset | tokens | lemma | acc-insens lemma | POS | coverage |
|---|---:|---:|---:|---:|---:|
| all Greek | 63,222 | 91.1% | 92.1% | 75.3% | 99.35% (413 fallbacks) |
| `source=MorphGNT` (trustworthy) | 52,094 | **96.6%** | **97.4%** | 75.7% | 99.95% |
| `source=grc_proiel_lg` (machine gold) | 11,128 | 65.4% | 67.2% | 73.1% | 96.5% |

- Baseline before this round: 90.4/74.3 (ALL), 96.3/75.5 (MG subset) with NT
  tables, no `-n`, ~1,027 misses. The convention layer lifts the trustworthy
  subset to 96.6% exact / 97.4% accent-insensitive lemma; `-n` mode cuts misses
  from ~1,027 to 413 (elided forms + unaccented spellings).
- **Config trade measured**: Viterbi (`--tagger`) costs ~1.4pp MG-subset lemma for
  +1.0pp POS — the opposite of LXX, where it was net positive. Default is top-1
  (lemma-first); `--tagger`/`--joint` available for POS-optimized output.
- **Verification**: saved ev2 evaluator snapshots re-run byte-identical after all
  toolkit changes (no behavioral drift); pytest 33/33; AF repo's analyze.py output
  verified byte-identical to morpheus's build_morph_af.py across all 15 files.
- **NT/LXX untouched**: no shared stemlib lemma changes, no NT table changes; the
  elided entries resolve only in `-n` mode (default-mode controls re-checked).

**Decisions made this round** (veto-able):
- Convention table derived at run time from gold rather than hardcoded: fully
  reproducible from the corpus, self-auditing via the summary's applied/rejected
  lists, and no Greek lemma pairs committed to morpheus.
- Fallbacks keep the corpus's own annotation (original fields + source) with `.fb`
  sidecars — LXX-driver parity; gaps stay visible instead of being dropped or
  invented as synthetic proper nouns.
- AF repo tables are derived at run time from its own gold (always current);
  README pins morpheus master ≥ `23b33d3`. origin/master already contained every
  toolkit feature analyze.py needs, so the AF repo is reproducible without a push.

**Open questions for the user:**
- Push morpheus origin/master? (Round 7 adds three commits: `d760a3e`, `259df21`,
  `23b33d3`.) The AF README pins `23b33d3`; pushing makes that pin real.
- Push the AF repo's `morpheus-analysis` branch to its remote? (Currently local
  only, per this round's default.)
