# Morphological analysis for CSNTM's transcription → searchable-text pipeline

*A one-page proposal for the Center for the Study of New Testament Manuscripts.
Prepared 2026-10-15; numbers refreshed 2026-10-16 (Round 19). Demo below uses
public-domain Greek only; no CSNTM data is used or included.*

## What it is
**Morpheus** is an Ancient Greek morphological analyzer from the Perseus/Perseids
lineage, with a Python toolkit (`morpheus-toolkit`, MIT-licensed). It takes UTF-8 Greek
and returns, for every token, its **lemma**, fine-grained **POS**, **full morphological
parse** (person/number/tense/mood/voice/case/gender/degree), **Strong's number**, and a
**calibrated confidence**, as structured **JSON/JSONL**. It runs fully offline.

Measured on the SBLGNT (accented critical text): **94.6% exact / 94.7%
accent-insensitive top-1 lemma**, 78.1% coarse POS. On unaccented papyri (PapyGreek
treebank originals): **97.4% coverage, 89.4 / 90.8% top-1** with the numeral pass;
learned re-ranking adds ~2 points on top of the frequency baseline.

## Why it fits a transcription pipeline
After handwritten-text recognition produces raw Greek, morphology is the layer that turns
it into *searchable, comparable* text:

- **Lemma/parse search** across all transcriptions — "show every form of λόγος", or
  "every 3rd-plural aorist imperative".
- **Collation support**: classify variant-unit differences as **morphological vs
  orthographic** by comparing lemma+parse, not raw strings.
- **Conventions that match NT scholarship**: MorphGNT-style codes and **Strong's numbers**
  (SBLGNT lemma mapping) for cross-referencing apparatus and lexica.
- **Practical scale**: Unicode in / JSONL out, parallel jobs, per-reading **confidence**
  so downstream tools can weigh ambiguous forms.

## Worked example (public-domain John 1:1–2)
Input (accented critical-text Greek):

```bash
$ morpheus-toolkit analyze sample.txt --json sample.jsonl
24 tokens, 24 analyzed (100.0%), 0 misses
  Ἐν     P ἐν     []                              (0.99)
  ἀρχῇ  N ἀρχή   [case=dat number=sg gender=fem]  (1.00)
  ἦν     V εἰμί   [tense=imperf mood=ind …]        (0.88)
```

JSONL (one record per token), excerpt:

```json
{"token": "θεόν", "beta": "qeo/n", "analyses": [
  {"lemma": "θεός", "pos": "N", "features": {"gender": ["masc"], "case": ["acc"], "number": ["sg"]},
   "stemtype": "os_ou", "confidence": 1.0, "pos_confidence": 0.75, "strongs": 2316,
   "proposed": false, "recovered_from": null}]}
```

Lemma search over the JSONL — "give me every token whose reading is λόγος":

```python
rows = [json.loads(l) for l in open("sample.jsonl")]
[r["token"] for r in rows if any(a["lemma"] == "λόγος" for a in r["analyses"])]
# -> ['λόγος', 'λόγος', 'λόγος']
```

## One honest nuance for manuscript text
Uncial manuscripts are **unaccented and unbreathed**, and the toolkit's
accent-insensitive pass (`--ignore-accents`) strips **accents but not breathings**. So a
fully bare form can mis-resolve: `εν` (no breathing) → εἰμί instead of ἐν. Practically,
(a) breathings/accents (or a light restoration step) raise accuracy a lot, and
(b) the confidence scores and context help where they don't. This is worth a short
conversation — a breathing-restoration or context-disambiguation step is a natural joint
improvement.

## Try it
```bash
scripts/build.sh                                   # build the analyzer -> bin/cruncher
python3 -m venv .venv && .venv/bin/pip install -e python/ pytest
.venv/bin/morpheus-toolkit analyze transcript.txt --json out.jsonl
.venv/bin/morpheus-toolkit analyze transcript.txt --ignore-accents --jobs 4
```

## License
`morpheus-toolkit` is MIT; the analyzer is the Perseus Morpheus codebase (see the
repository). Nothing here requires CSNTM to license or share its data — the toolkit runs
locally on whatever text you supply.

## References (CSNTM)
- **AI for Manuscript Transcription** — <https://www.csntm.org/ai-for-manuscript-transcription/>
  ("CSNTM proposes to train an AI model to read the text of ancient Greek manuscripts and
  put that text into digital, searchable form.")
- CSNTM projects index (carries the Dan Wallace photo) — <https://www.csntm.org/projects/>
- CSNTM "Who We Are" (Wallace founded CSNTM, 2002) — <https://www.csntm.org/who-we-are/>
- Daniel B. Wallace — <https://danielbwallace.com/>

(Note: the AI project page is CSNTM's; the "Wallace" naming appears on the projects index
and the Who-We-Are page rather than in the AI page body.)

**Question:** is lemmatization / morphological tagging on CSNTM's transcription roadmap?
If so, this is a drop-in morphology layer we can wire to your HTR output (JSONL) and
extend (e.g. uncial-specific handling) together.
