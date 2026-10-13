# Active plan

None — Round 9 (classical Greek, contextual homographs, papyrus numerals) is complete;
its full record lives in [completed.md](completed.md). The user chose to stop here
(2026-10-13); no further rounds planned at this time.

## Standing constraints (carry into any future round)

- All temp/work files inside the morpheus folder (`tmp/`, git-ignored) — never
  `~/.lmstudio/scratchpads`. Read `Agent.md` first; plan in todo.md → check in before
  non-trivial implementation; verify before marking complete; update `lessons.md` after
  corrections. Push only when asked.
- No Latin work (user direction); the Round-8 Latin benchmark + table remain as
  committed, untouched.
- PROIEL-derived content stays out of committed files (CC BY-NC-SA; measurement/docs
  only). Public dataset names (AGLDT, PROIEL) are fine in docs.
- NT behavior unchanged: no stemlib edits that alter SBLGNT/NT output to fit another
  edition's conventions.

## Candidate follow-ups if a new round is ever wanted

- Retrain the homograph-context table with LXX included (excluded from Round 9 — no
  annotated `.mlxx` gold in this workspace, only Morpheus outputs).
- The 38 sub-threshold PapyGreek numeral forms (~0.1pp; diminishing returns).
- False-hit letter numerals on papyri (315 wrong top-1): would need stemlib entries for
  bare-letter numerals, which changes default behavior — out of scope per user direction.
