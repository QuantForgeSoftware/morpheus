# Active plan — Morpheus × LXX

Completed rounds 1–6 live in [completed.md](completed.md): stemlib coverage to 99.81%,
the full-corpus annotation pipeline, the repo-wide scrub, the docs refresh, and the
Round-6 convention layer (dictionary forms + base lemmas) that took the LXX annotation
past the reference on all three metrics.
Working files for this work live in `tmp/lxx/` (git-ignored): `compare.py`, `eval_morph.py`,
`report.txt`, TSVs, and `morph-lxx/` (the annotated corpus). Round 6 added analysis
tools (`diff_variants.py`, `gen_tiebreak.py`, `table_audit.py`, probes), per-variant
outputs (`morph-lxx-base2/`, `morph-lxx-dict/`, `morph-lxx-oldnat/`) and eval snapshots
(`eval_r6*.txt`).

---

# Next round — candidates (not yet approved; plan before implementing)

No active tasks. Candidate directions from the Round-6 review:

1. **Port the convention layer to NT** — `lemma_frequencies.json` already carries joint
   lemma×POS counts, so the ranking floor applies there for free; a `build_morph_gnt.py`
   with dictionary-form + base-lemma modes (tables derived from an NT reference corpus)
   would be the natural Round 7. Needs a local checkout of that reference corpus.
2. **C# port parity** — lessons.md notes placeholder stubs (`chckindecl.cs` returns 0;
   `CheckGenWordsFunc` lacks comptab/accent logic); worth fixing if any deployment path
   uses the C# runner.
3. Small LXX polish (ἕως/ἠώς homograph, ~277 tokens) — diminishing returns; optional.

