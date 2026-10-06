"""Tokenizer for raw Unicode Greek text."""
from __future__ import annotations

import re

# Runs of Unicode letters (excludes digits and underscore); strips punctuation,
# which Morpheus does not want. Apostrophes/enclitics are handled by Morpheus.
_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Split raw text into Greek word tokens."""
    return _TOKEN_RE.findall(text or "")
