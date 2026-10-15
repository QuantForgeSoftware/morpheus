# Design: a Unicode-native input path for `cruncher`

**Status: proposed (Round 10, Item 12). Not implemented — this is the required
scoping/plan before a large C refactor.**

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

## Proposed approach

1. **Canonical decomposition in C.** Normalize each input code point with a
   Unicode canonical decomposition (NFD) table so a letter and its diacritics are
   separate code points. This turns the messy precomposed range (U+1F00–U+1FFF,
   ~500 Greek Extended code points) into a small mapping: ~24 base letters + ~8
   combining marks.

2. **Mapping tables (new `src/greeklib/gkunicode.c`).**
   - base letters → beta (`α→a`, `β→b`, … including `ου`, `γγ` digraph handling);
   - combining marks → beta operators: acute `´`, grave `` ` ``, circumflex `~`/
     `^`, rough `(` , smooth `)`, iota subscript `|`, diaeresis `+`;
   - **word-final** combining comma (U+0313) → ASCII apostrophe (elision); mid-word
     combining marks pass through as letter parts (the rule the Round-9 Python fix
     established).

3. **Entry point.** Add `-u` / `--unicode` to `cruncher` (do **not** auto-detect;
   an explicit flag avoids ambiguity with Latin ASCII input). Optionally detect a
   UTF-8 BOM. The flag converts each input word before the existing lowercase/
   lookup path, so nothing downstream changes.

4. **Single source of truth.** Generate the C mapping tables from the same
   reference data used to validate the Python converter, and add a cross-check
   test: for every distinct form in the committed gold corpora, assert
   `C_convert(w) == to_beta(w)`.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Converter divergence from `beta-code` | Oracle test over all corpus forms; fail the build on any mismatch |
| Encoding detection errors | Explicit `-u` flag; never guess |
| Performance | Conversion is O(bytes) with a 256/0x2000-entry table lookup; measure on AGLDT (469K tokens) |
| Regressions in existing beta-code callers | New path is additive; default behavior unchanged; the toolkit keeps its Python path until parity is proven |

## Effort

- Mapping tables + NFD lens: ~1 day.
- `cruncher` flag + input loop wiring: ~0.5 day.
- Oracle test harness + corpus cross-check: ~0.5 day.
- Verification (all corpora byte-identical analyses vs the Python path): ~0.5 day.

**Recommendation:** do it as its own round, gated on the oracle test, and make the
toolkit prefer the C path only once `C_convert == to_beta` holds for every form in
SBLGNT + AF + AGLDT + PROIEL + PapyGreek.
