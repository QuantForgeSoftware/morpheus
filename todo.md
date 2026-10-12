# Active plan — Round 8 candidates: new corpora (needs approval)

Round 7 (Apostolic Fathers) is complete and committed (`d760a3e`, `259df21`,
`23b33d3`, `b3707de`); its full record now lives in [completed.md](completed.md).
Working files for Round 8 go in `tmp/<corpus>/` (git-ignored).

## Context: where Morpheus stands, and what "improve" can still mean

The Greek biblical side is near saturation: LXX 99.81% coverage (Round 2), NT
~95% top-1 after the name additions, AF 99.35% / 96.6–97.4% lemma (Round 7).
Remaining levers found in corpus research (2026-10-11):

**Key caveat — most Perseus "morph texts" are circular.** Celano's OGA/OLA
treebanks (45M Greek / 17M Latin words; the data behind morph.perseus.org) were
auto-annotated *with Morpheus* (LemmatizedAncientGreekXML). They cannot serve as
independent gold for improving Morpheus — at best a scale benchmark or POS-bigram
source. The valuable resources are the **manually curated treebanks** and a few
independent lemmatized corpora:

| corpus | size | annotation | license / access | improves |
|---|---:|---|---|---|
| **PapyGreek Treebanks** (Helsinki; Zenodo `10.5281/zenodo.5074307`) | 44K tokens, documentary papyri ca. 300 BCE–700 CE (Zenon archive letters, petitions) | semi-manual + reviewed, dependency-morphosyntax; TEI XML | CC BY-SA 4.0, free | **new Koine domain** — first test of Morpheus on papyrological Greek; safe stemlib additions from human-reviewed gold |
| **PROIEL greek-nt** (Tischendorf 1869) | 140,763 tokens | fully manual morphosyntax + info structure; PROIEL XML **and CoNLL-X** | CC-BY-**NC**-SA 3.0, GitHub (`syntacticus/syntacticus-treebank-data`) | independent second NT gold — validates how much of our SBLGNT-based NT numbers are robust vs convention-fitted (some sections unannotated: HEB 13, catholics) |
| **PROIEL latin-nt** (Jerome's Vulgate) + caes-gal/cic-att/per-aeth/pal-agr | ~113K tokens total | manual; CoNLL-X available | CC-BY-**NC**-SA 3.0, GitHub | first benchmark of the **Latin analyzer** (this checkout ships a full Latin stemlib — ~286K source lines — that has never been measured) |
| **AGLDT / Perseids v2.1** (`PerseusDL/treebank_data`) | Greek ~190K words (Homer, Hesiod, Aeschylus, Sophocles, Thucydides 1, Aesop); Latin: Caesar, Cicero, Ovid, Petronius, Vergil… | manual by 200+ annotators; free on GitHub | open | classical register — expands/validates both languages beyond the biblical domain |
| **Index Thomisticus** (Busa) | 11M lemmatized words, medieval Latin | classic lemma+POS per word; plain text at corpus.thomisticum.org (+ treebank subset) | free | large-scale Latin frequency table source |
| OGA/OLA/GLAUx (Celano 2024) | 45M / 17M words | **auto, Morpheus-derived** → circular | open | not gold; scale benchmark only |
| TLG | huge | subscription; abridged untagged | paid | skip unless user has access |
| Hebrew (OSHB/SBLHBT) | — | — | free | N/A — this checkout has no Hebrew component |

No large freely available *patristic* tagged corpus exists (the AF repo remains
the main one); PapyGreek is the closest new-domain gold in the user's register.

## Round 8 candidate plan (checkable; needs approval before implementation)

1. **PapyGreek round** (top priority for this project's domain): download the
   Zenodo release; write a TEI-XML→TSV reader (token/lemma/morph, `_orig` vs
   `_reg` layers); measure Morpheus coverage + lemma agreement on all 44K tokens;
   add stemlib entries for missed forms (human-reviewed gold — safe to encode,
   unlike machine gold); derive a papyrus frequency table if the numbers warrant.
2. **Latin benchmark round**: read PROIEL latin-nt + AGLDT Latin via CoNLL-X;
   measure coverage/lemma/POS of the Latin analyzer for the first time; build
   `lemma_frequencies_latin.json` (Index Thomisticus or treebank gold) and a
   first tuning pass mirroring Rounds 3–4. ⚠️ PROIEL is CC-BY-NC-SA: use it for
   measurement/docs, but keep any derived tables out of committed files unless
   the user accepts the license terms (Index Thomisticus-derived tables avoid
   this).
3. **PROIEL Greek NT cross-validation**: CoNLL-X reader; measure our current NT
   numbers against a second independent human-verified text; document how much
   holds up (and where SBLGNT conventions were overfit). Same NC-SA caveat for
   committed artifacts — validation numbers in docs are fine.
4. **Optional: classical Greek** (AGLDT ~190K words) if the user wants Morpheus
   usable on classical texts; otherwise skip — register mismatch with the
   biblical focus, and the stemlib already carries LSJ roots.

Each item is the same shape as Rounds 2–7 (format reader + measurement +
optional tables/convention layer), so roughly one round each; items 1 and 3 are
small enough to finish quickly. Working files in `tmp/papygreek/`,
`tmp/proiel-nt/`, `tmp/latin/`.

## Decisions needed from the user

- Which item(s) to approve (and in what order)? Item 1 is the recommendation.
- Round 7 leftovers: push morpheus origin/master (4 commits ahead of `75fface`)?
  Push the AF repo's `morpheus-analysis` branch?
- License comfort with CC-BY-NC-SA (PROIEL) for anything that would be committed.
