# Morphological analysis for CSNTM's transcription → searchable-text pipeline

*A one-page proposal for the Center for the Study of New Testament Manuscripts.
Prepared 2026-10-15; numbers refreshed 2026-10-16; claims corrected the same day
after re-measuring bare uncial input. Demo below uses public-domain Greek only;
no CSNTM data is used or included.*

## What it is
**Morpheus** is an Ancient Greek morphological analyzer from the Perseus/Perseids
lineage, with a Python toolkit (`morpheus-toolkit`, MIT-licensed). It takes UTF-8 Greek
and returns, for every token, its **lemma**, fine-grained **POS**, **full morphological
parse** (person/number/tense/mood/voice/case/gender/degree), **Strong's number**, and a
**calibrated confidence**, as structured **JSON/JSONL**. It runs fully offline.

Three different tasks, not one number:

- **Accented critical text** (SBLGNT, the published gate): **94.6% exact / 94.7%
  accent-insensitive top-1 lemma**, 78.1% coarse POS. This is not manuscript
  performance.
- **Fully bare text** (accents and breathings removed — the uncial condition),
  John 1–3, n=1,913, toolkit API with `--ignore-accents`: **74.0%**
  accent-insensitive top-1, against 93.2% on the same accented tokens under the
  same flag. That 93.2% is a chapter sample, not the gate.
- **Documentary papyri** (PapyGreek): 97.4% coverage, 89.4/90.8% top-1 with the
  numeral pass. A different register. Not NT papyri, and not a CSNTM number.

## Why it fits a transcription pipeline
After handwritten-text recognition produces raw Greek, morphology is the layer that turns
it into *searchable, comparable* text:

- **Lemma/parse search** across all transcriptions — "show every form of λόγος", or
  "every 3rd-plural aorist imperative".
- **Collation support (intended, not shipped):** compare lemma+parse rather than
  raw strings, so a morphological difference is distinguishable from an
  orthographic one. That comparison is only as good as the parse — on bare
  uncial text it is not, yet.
- **Conventions that match NT scholarship**: MorphGNT-style codes and **Strong's numbers**
  (SBLGNT lemma mapping) for cross-referencing apparatus and lexica.
- **Practical scale**: Unicode in / JSONL out, parallel jobs, per-reading **confidence**
  so downstream tools can weigh ambiguous forms.

## Worked example (public-domain John 1:1–2)
Input (accented critical-text Greek):

```bash
$ morpheus-toolkit analyze sample.txt --json sample.jsonl
24 tokens, 24 analyzed (100.0% coverage — not lemma accuracy), 0 misses
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

## The manuscript condition, measured
Uncial text is unaccented **and unbreathed**. `--ignore-accents` (`cruncher -n`)
ignores accents in matching and does **not** ignore breathings. The breathing
retry (smooth, then rough) runs only when the accented match misses entirely.

Bare `εν` is such a miss. With the flag it locks onto **epic ἔν**, the imperfect
3pl of εἰμί (`e/n`), and because that is the only candidate the API reports
**confidence 1.0** — not ἐν. `ἐν` (`e)n`) is ἐν at 0.99. So confidence does not
catch this, and the flag is not a fix for uncial function words. Without the
flag the form is a miss; recovery then proposes εἰ (0.49), which is also wrong,
but at least not a lone 1.0.

Restoring the edition's diacritics where the letters agree closes that gap (the
John 1–3 pair above: 74% → the low 90s). A prototype does this by aligning a
bare page to a base text, and it is meant to *report* letter disagreements as
candidate variants rather than silently correct them. **Not shipped**, and not
yet measured on a full real transcription. Worth a conversation; not a claim
that the current toolkit is a drop-in for HTR output.

## Try it
```bash
scripts/build.sh                                   # build the analyzer -> bin/cruncher
python3 -m venv .venv && .venv/bin/pip install -e python/ pytest
.venv/bin/morpheus-toolkit analyze transcript.txt --json out.jsonl
# --ignore-accents is not a fix for bare uncial text; see above (εν → εἰμί at 1.0)
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
If so, this is a local morphology layer we can wire to your HTR output (JSONL) and
extend for uncial text together — including the bare-form failure above, which we
would not paper over.
