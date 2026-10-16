# CSNTM outreach email — draft (revised 2026-10-16, after the AI-project page)

*Draft for the user to send. Sending is still Round 13.2 (user action). This
revision matches their published objectives and the Kraken/CSNTM-access notes
below. Attach or link [`docs/csntm-morphology-demo.md`](csntm-morphology-demo.md).
Keep the tone: offer, not pitch; the only ask is a routing question. Do not
ask for images in this email.*

---

**Subject:** Morphological tagging after transcription — an offline, open-source
analyzer

Dear CSNTM team,

I read the AI-for-manuscript-transcription page: index the collection by
Scripture reference, and train a reader on paired images and existing
transcriptions. I work on the layer after a transcription exists — **lemma +
full parse + Strong's + confidence**, as JSONL, fully offline. It is not a
reader, and it is not yet a drop-in for a damaged uncial page.

A short summary:

- **What it does.** Input: UTF-8 Greek (accented or not). Output: for every
  token — lemma, fine-grained POS, full morphological parse, Strong's number,
  and a calibrated confidence, one JSON record per token. It's
  `morpheus-toolkit`, MIT-licensed, wrapping the Perseus Morpheus analyzer;
  nothing to license, nothing to upload — it runs locally on whatever text you
  supply.
- **Why it fits a transcription pipeline.** Lemma/parse search across
  transcriptions ("every form of λόγος", "every 3rd-plural aorist imperative");
  MorphGNT-style codes and Strong's numbers for apparatus/lexica
  cross-referencing. Collation by lemma+parse, and per-reading confidence, are
  only as good as the parse — see the bare-page failure below; confidence does
  not catch it.
- **Measured accuracy — three tasks, not one number.** Accented critical text
  (SBLGNT): 94.6% exact / 94.7% accent-insensitive top-1 lemma. That is not
  manuscript performance. Fully bare text (no accents, no breathings) is the
  uncial condition: on John 1–3, n=1,913, the same flag scores **74%**
  accent-insensitive top-1 (toolkit API, not the published gate). Documentary
  papyri (PapyGreek, 89.4/90.8%) are a third register, not NT manuscripts. A
  one-page demo is attached; its "100% analyzed" line is coverage of a 24-token
  sample, not lemma accuracy.
- **What fails on a bare page.** `--ignore-accents` ignores accents in matching
  but not breathings, and it retries only when the accented match misses.
  Bare `εν` is such a miss; the retry locks onto epic ἔν (εἰμί, imperfect 3pl)
  and, as the only candidate, reports confidence 1.0 — not ἐν. `ἐν` is ἐν at
  0.99. Confidence does not catch this.
- **Where this meets your two objectives.** Verse-indexing, once a page has any
  readable letters, is alignment to a base text. A prototype does that against
  the SBLGNT and refuses a weak match. It is not shipped, and it has not been
  run on your images. The reader itself is your project. Morphology sits on
  whatever transcription that reader produces. A model trained to match a
  critical edition will fill lacunae from memory and hide variants; we would
  rather flag the disagreement than correct it.

**The one question:** is lemmatization / morphological tagging on CSNTM's
transcription roadmap? If so, this is a local morphology layer we can wire to
your HTR output (JSONL) and extend for uncial text together — including the
bare-form failure above, which we would not paper over. If it's not your
team's layer, I'd be grateful for a pointer to whoever owns it.

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

- Recipients: if writing as a former student, address Wallace directly and say
  so in one line. The AI page does not name him; Who We Are does. A cold copy
  can still go to the general contact. Do not open with the image collection.
- Link (or attach) the demo doc; it is public-domain-only and uses no CSNTM
  data.
- If they reply about uncial text: do **not** offer `--ignore-accents` plus
  confidence as the fix. That flag is what turns bare `εν` into εἰμί at 1.0.
  Offer the measured gap (74% vs the accented sample) and the prototype as
  prototype.
- Do not "improve" the 74% figure into the SBLGNT 94.6% gate, or cite PapyGreek
  as NT-papyrus accuracy, in a later edit.
- Log the send date + outcome here (Round 13.2 closes when the email is out).

## What access to CSNTM would and would not change

Read 2026-10-16 from their AI project page and their terms of use. Knowing the
director opens a conversation. It is not a license.

Their published project is two jobs, and only one of them is ours:

1. **Index ~500,000 images by Scripture reference** (their example is John
   3:16). That is passage alignment once any letters are readable. Round 20's
   prototype is the relevant piece. It does not read a photograph.
2. **Train a reader** on about 56,000 already-transcribed pages paired with
   their high-resolution images. That is HTR. We should not offer to do it
   for them in email 1, and we should not pretend a morphology toolkit is that
   reader.

Access would matter for job 2, on the manuscripts they actually hold. Those
are mostly later majuscules and minuscules, digitized on site visits, not the
early-papyrus corpus. P45, P46, and P47 were photographed for a Hendrickson
facsimile **in partnership with the holding institutions**. Chester Beatty,
Bodmer, and Michigan still own those objects. A conversation with Wallace does
not transfer those rights.

Their terms (section 3) say CSNTM is a custodian. The owner retains rights.
Any use beyond viewing — derivative work, reproduction, training a model —
needs permission from **both** the holding institution and CSNTM
(`manuscripts@csntm.org`). Viewing the Digital Manuscript Collection is
non-commercial research. Do not download the collection into a training run
because a reply was friendly.

So: access would make a real difference for a minuscule/majuscule reader and
for evaluating verse-indexing on their pages, if both permissions are in
writing and the gold is a diplomatic transcription. It would not, by itself,
produce a reader of an unseen papyrus hand. Most of the 56,000 pages are the
wrong script for P46.

## Kraken, local tree `/Users/johnbaima/Code/kraken`

Apache 2.0. This is the right tool class. It is a line-level recognizer
(`ketos` recognition, default architecture `vgsl`, CTC added automatically;
`ppocrv6` is the other arch), plus a trainable baseline segmenter. Training
data is PageXML/ALTO, or an image plus a `.gt.txt`. `--load` fine-tunes an
existing model and can resize the codec; `--freeze-backbone` exists;
`--augment` exists. Output is lines, with word boxes and character cuts. That
is the correct output for scriptio continua: do not teach it word spaces the
scribe did not write.

It is not improved for NT papyri by a larger network, a fork, or a language
model in the decoder. The shipped default model is printed French
(`catmus-print-fondue-large`). A 9th–12th century minuscule model is the wrong
start for a papyrus hand. The codec, the segmenter mask, and per-character
confidence are already in the tree. What is missing is diplomatic line gold,
not a subsystem. The one code change worth making later — a default-off gap
when a letter's confidence is weak — is in [`kraken.md`](../kraken.md). It is
not an offer, and it is not in the letter above.

A few hundred aligned lines of one hand is the usual Kraken training set, and
it still fails on a different hand. CSNTM's 56,000 pages would be the right
corpus for a **minuscule** model, which is their Objective 2, not a papyrus
model. Do not start that training on images we are not allowed to use. Do not
put Kraken, a patch, or an offer to train it, in email 1.
