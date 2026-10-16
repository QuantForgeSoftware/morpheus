"""Tokenizer for raw Unicode Greek text.

The tokenizer normalizes editorial conventions that would otherwise split or
mangle words, then splits on everything that is not a letter:

- the input is NFC-normalized, so decomposed (NFD) accents do not split tokens;
- PapyGreek-style annotation spans (``|gap:1|``, ``|num:2|``) are removed;
- editorial combining marks (dot-below *U+0323*, overline *U+0305*) are removed;
- editorial bracket/ellipsis/hyphen runs *inside* a word (letters on both
  sides) are removed, so ``ἀδελφ[οῦ]`` is one token (``ἀδελφοῦ``), not two;
- elision/crasis apostrophes (``ʼ`` *U+02BC*, ``’`` *U+2019*, ASCII ``'``,
  koronis *U+1FBD*) stay attached to their word, because Morpheus analyses
  elided forms (``ἀλλʼ`` → ἀλλά, ``δʼ`` → δέ).

Crasis (κρᾶσις) tokens are single orthographic words and stay single tokens:
Morpheus's stemlib carries the common crasis forms (κἀγώ → ἐγώ, τοὐμόν → ἐμός,
τἀληθές → ἀληθής, χὠ → ὁ), and the rare ones go through the recovery pre-pass
(μοὐ → μοι). Do not split them — the contracted vowel cannot be restored
without a lexicon, and the corpora tokenize them as one word too.
"""
from __future__ import annotations

import re
import unicodedata

# PapyGreek annotation spans (|num:N|, |gap:1|, |g:...|).
_PIPE_ANN = re.compile(r"\|[a-z]+:[^|]*\|")

# Editorial combining marks: dot-below (letter underdot) and overline. Applied
# after NFC, so composed accents are untouched.
_EDITORIAL_COMBINING = re.compile(r"[\u0323\u0305]")

# Editorial markers. Runs of these *between letters* belong to the word
# (supplements, uncertain letters, line-break hyphens); at word edges the
# characters simply separate tokens as before.
_EDITORIAL = "∼∽∤⋰⋱⸢⸣❨❩<>[]{}()〚〛⊢⊣⸌⸍⎴⎵⦑⦒⸜⸝⧼?…-"
_INTRA_WORD_MARKERS = re.compile(
    rf"(?<=[^\W\d_])[{re.escape(_EDITORIAL)}]+(?=[^\W\d_])"
)

# Apostrophes that stay attached to their word (elision and crasis marks).
_APOSTROPHES = "'ʼ’\u1fbd"

# Runs of Unicode letters, with attached apostrophes (trailing or internal).
_TOKEN_RE = re.compile(rf"[^\W\d_]+(?:[{_APOSTROPHES}][^\W\d_]*)*", re.UNICODE)


def normalize_editorial(text: str) -> str:
    """Normalize editorial conventions (markers, NFD accents) without splitting."""
    text = unicodedata.normalize("NFC", text or "")
    text = _PIPE_ANN.sub("", text)
    text = _EDITORIAL_COMBINING.sub("", text)
    return _INTRA_WORD_MARKERS.sub("", text)


def tokenize(text: str) -> list[str]:
    """Split raw text into Greek word tokens."""
    return _TOKEN_RE.findall(normalize_editorial(text))
