"""
morpheus-toolkit — a Unicode/JSON layer around the Morpheus Ancient Greek
morphological analyzer.

Morpheus itself speaks beta code and prints Perseus-format analyses. This package
adds what is needed to apply it to arbitrary Greek texts:

  * Unicode <-> beta-code conversion (via `beta-code`);
  * a runner for `bin/cruncher` that returns structured analyses;
  * fine-grained part-of-speech recovery from Morpheus's coarse tags;
  * frequency- and context-aware ranking of the candidate analyses;
  * a tokenizer for raw Greek text and JSON/CLI output.
"""

from .analysis import Analysis, parse_perseus_analyses
from .api import Morpheus, TokenResult
from .beta import from_beta, to_beta
from .morphgnt import parsing_code, pos_code
from .ranking import Ranker
from .runner import MorpheusRunner
from .tagger import PosTagger
from .tokenize import tokenize

__all__ = [
    "Analysis",
    "Morpheus",
    "MorpheusRunner",
    "PosTagger",
    "Ranker",
    "TokenResult",
    "from_beta",
    "parse_perseus_analyses",
    "parsing_code",
    "pos_code",
    "to_beta",
    "tokenize",
]
