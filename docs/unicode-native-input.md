# Design: a Unicode-native input path for `cruncher`

**Status: implemented (Round 19.4, 2026-10-16).** The C path is
`src/anal/gkunicode.c` (+ generated `gkunicode_tab.c`), exposed as `cruncher -u`
and as the `gkconvert` oracle binary. Parity with the Python converter holds for
**110,927 forms** (6,623 synthetic + every distinct form in MorphGNT, AF, AGLDT,
PROIEL and PapyGreek): 0 mismatches. The toolkit still converts in Python by
default; switching it to `-u` is a follow-up decision, gated on that parity.

## Problem

Today the analyzer only accepts **beta code**, and the toolkit bridges the gap in
Python:

```
UTF-8 Greek ──to_beta()──► beta code ──cruncher──► Perseus analyses ──parse──► JSON
```

Every Greek-text defect in the round records lived in that converter, not in the
analyzer:

- the **classical elision mark** (word-final U+0313, δ̓) was rejected outright —
  34K AGLDT tokens, coverage 92.8% → 99.8% only after a Python fix;
- **breathings/case**: cruncher matches only lowercase beta, so uppercase corpora
  returned nothing until `_normalize_beta`;
- **letter-numeral collisions** and mixed editorial marks are handled by ad-hoc
  Python scrubbing in each pipeline.

The conversion is also a moving target: the rules live in Python (`beta-code`
plus local fixes) while the analyzer's expectations live in C. Two sources of
truth drift.

## Goal

Let `cruncher` read UTF-8 Greek directly, so the toolkit can pass text through
unchanged and the conversion has **one** implementation, covered by tests.

## Implemented approach (Round 19.4)

1. **Generated tables, not hand rules** (`scripts/gen_gkunicode_tables.py` →
   `src/anal/gkunicode_tab.c`). The reference is the *same* beta-code package
   JSON the Python converter uses (`unicode_to_beta_code.json`), so parity is by
   construction where possible:
   - the 271 single-codepoint map entries (values are pure ASCII beta);
   - **NFC composition pairs** (449) derived by asking `unicodedata` for every
     (starter, mark) combination — starters include every decomposition piece
     (U+00A8, backtick, space) so spacing characters recompose;
   - **NFD expansions** (259) for every Greek/combining/mapped codepoint —
     singleton decompositions (U+0340→U+0300, U+0343→U+0313, U+0344→U+0308
     U+0301) are not composition pairs and must be expanded;
   - combining classes (111) for canonical ordering; Unicode lowercase
     mappings (153) for pass-through Greek codepoints (the Python reference
     lowercases the whole converted string).

2. **Conversion order mirrors `to_beta` + `_normalize_beta` exactly**:
   apostrophe translation (U+2019/2018/02BC/00B4 → `'`) → word-final U+0313 →
   `'` → full NFD → canonical reorder → greedy recomposition with the UAX #15
   blocking rule → per-codepoint map (unmapped codepoints pass through) →
   lowercase (ASCII beta + Unicode table).

3. **Entry points.**
   - `cruncher -u`: converts each input word before the existing pipeline;
     conversion failure counts as a miss. Greek only — Latin input keeps its
     case (the Latin path is case-sensitive). Default behavior (no `-u`) is
     byte-identical.
   - `bin/gkconvert`: the oracle binary (`src/anal/gkconvert.c`) — reads forms,
     prints the conversion (or `\x1fFAIL`); used by the parity script and tests.

4. **Single source of truth + oracle test.** `scripts/unicode_parity.py` asserts
   `C_convert(w) == to_beta(w).lower()` over the synthetic exhaustive set and
   every distinct corpus form; `python/tests/test_unicode_c_path.py` runs it
   (skipped when the binary is not built) plus direct behavior checks.

## Results (Round 19.4)

| check | result |
| --- | --- |
| synthetic exhaustive (map keys, Greek ranges, compositions NFC+NFD, mark orders, apostrophes, 3K random) | 6,623 forms, 0 mismatches |
| corpora (MorphGNT 137K, AF 63K, AGLDT 469K, PROIEL 132K, PapyGreek 36K rows) | 104,304 distinct forms, 0 mismatches |
| conversion speed | 104K forms / 1.0 MB in 0.05 s (~2M forms/s) |
| `cruncher -u` vs beta input | byte-identical output (`-q` echo + analyses) |
| default path | unchanged (no `-u` ⇒ old code path) |

## Remaining follow-ups

- Switch the toolkit's `runner` to `-u` (one conversion implementation) once a
  round can absorb the regression surface; keep `to_beta` for the API's
  `beta` field.
- Non-Greek pass-through is ASCII-lowercased in C (the Python reference
  applies full Unicode lowercase); Greek + punctuation are covered by the
  lowercase table, other scripts are out of scope for the corpus set.
- The beta-code package's three multi-character map keys (space + combining
  mark) cannot occur inside a word and are not carried into C.

## Original proposal (Round 10, Item 12) — kept for the record

The scoping below estimated ~2.5 days and proposed hand-written base+mark
mapping rules; the implementation instead generated every table from the
reference JSON, which removed the hand-rule divergence risk entirely.

| Risk | Mitigation (as implemented) |
| --- | --- |
| Converter divergence from `beta-code` | Oracle test over all corpus forms (110,927 forms, 0 mismatches) |
| Encoding detection errors | Explicit `-u` flag; never guess |
| Performance | O(bytes) table lookups; measured ~2M forms/s |
| Regressions in existing beta-code callers | New path additive; default unchanged; toolkit keeps the Python path until parity is proven (proven) |
