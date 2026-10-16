# CSNTM outreach email — draft (Round 19.5)

*Draft for the user to send. Sending is Round 13.2 — the last blocked step.
Attach or link [`docs/csntm-morphology-demo.md`](csntm-morphology-demo.md) (or
paste its body). Keep the tone: offer, not pitch; the only ask is a routing
question.*

---

**Subject:** Morphological tagging for your transcription pipeline — an offline
drop-in (open source)

Dear CSNTM team,

I read about your AI-for-manuscript-transcription project — turning manuscript
images into digital, searchable text. I work on Ancient Greek morphological
analysis, and I built a toolkit that may be useful for the layer right after
handwriting recognition: turning transcribed Greek into **lemma + full parse +
Strong's + confidence**, as JSONL, fully offline.

A short summary:

- **What it does.** Input: UTF-8 Greek (accented or not). Output: for every
  token — lemma, fine-grained POS, full morphological parse, Strong's number,
  and a calibrated confidence, one JSON record per token. It's
  `morpheus-toolkit`, MIT-licensed, wrapping the Perseus Morpheus analyzer;
  nothing to license, nothing to upload — it runs locally on whatever text you
  supply.
- **Why it fits a transcription pipeline.** Lemma/parse search across
  transcriptions ("every form of λόγος", "every 3rd-plural aorist imperative");
  collation support (classify variant-unit differences as morphological vs
  orthographic by comparing lemma+parse, not strings); MorphGNT-style codes and
  Strong's numbers for apparatus/lexica cross-referencing; per-reading
  confidence so downstream tools can weigh ambiguity.
- **Measured accuracy** (public data, reproducible): on the SBLGNT, 94.6% exact
  top-1 lemma (94.7% accent-insensitive); on unaccented papyrus originals
  (PapyGreek treebank), 97.4% coverage and 89.4/90.8% top-1 with the numeral
  pass. A one-page demo with a worked John 1:1–2 example and JSONL output is
  attached.
- **The honest nuance for manuscript text.** Uncial text is unaccented and
  unbreathed, and the accent-insensitive pass strips accents but not breathings,
  so fully bare forms can mis-resolve (e.g. `εν` → εἰμί instead of ἐν). With
  breathings/accents (or a light restoration step) accuracy rises a lot, and the
  confidence scores + context help where they don't. A breathing-restoration or
  context-disambiguation step is a natural joint improvement.

**The one question:** is lemmatization / morphological tagging on CSNTM's
transcription roadmap? If so, this is a drop-in morphology layer we can wire to
your HTR output (JSONL) and extend (e.g. uncial-specific handling) together. If
it's not your team's layer, I'd be grateful for a pointer to whoever owns it.

The demo document (`docs/csntm-morphology-demo.md` in the repo) has the full
worked example, JSONL shapes, and reproduction steps:

```
scripts/build.sh
python3 -m venv .venv && .venv/bin/pip install -e python/ pytest
.venv/bin/morpheus-toolkit analyze transcript.txt --json out.jsonl
```

Thank you for the work your team does making these manuscripts accessible.

Best regards,
[Name]

---

## Notes for sending

- Recipients: CSNTM general contact / the AI-for-transcription project; Dan
  Wallace is on the projects and Who-We-Are pages (the AI page itself doesn't
  name him — see the references in the demo doc).
- Link (or attach) the demo doc; it is public-domain-only and uses no CSNTM
  data.
- If they reply about uncial text: offer the `--ignore-accents` run plus the
  confidence field as the first experiment; the breathing-restoration idea is
  the natural joint follow-up.
- Log the send date + outcome here (Round 13.2 closes when the email is out).
