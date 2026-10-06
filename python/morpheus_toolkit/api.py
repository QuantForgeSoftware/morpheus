"""High-level API: analyze raw text or token lists."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .analysis import Analysis
from .beta import to_beta
from .ranking import Ranker, load_default_frequencies
from .runner import MorpheusRunner
from .tokenize import tokenize


@dataclass
class TokenResult:
    token: str
    beta: str
    analyses: List[Analysis] = field(default_factory=list)

    @property
    def best(self) -> Optional[Analysis]:
        return self.analyses[0] if self.analyses else None

    @property
    def is_miss(self) -> bool:
        return not self.analyses

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "beta": self.beta,
            "analyses": [analysis.to_dict() for analysis in self.analyses],
        }


class Morpheus:
    """A configured Morpheus analyzer (runner + ranker)."""

    def __init__(
        self,
        morpheus_dir: Optional[str] = None,
        frequencies: Optional[Dict[str, int]] = None,
        use_context: bool = False,
        runner: Optional[MorpheusRunner] = None,
    ):
        self.runner = runner or MorpheusRunner(morpheus_dir=morpheus_dir)
        self.ranker = Ranker(
            frequencies if frequencies is not None else load_default_frequencies(),
            use_context=use_context,
        )

    def analyze_beta(self, forms: List[str]) -> List[TokenResult]:
        results = [TokenResult(token=form, beta=form) for form in forms]
        raw = self.runner.analyze_beta(forms)
        for result, analyses in zip(results, raw):
            result.analyses = self.ranker.rank(analyses)
        if self.ranker.use_context:
            self.ranker.rerank_with_context([result.analyses for result in results])
        return results

    def analyze_tokens(self, tokens: Iterable[str]) -> List[TokenResult]:
        results = [TokenResult(token=token, beta=to_beta(token)) for token in tokens]
        valid = [(index, result.beta) for index, result in enumerate(results) if result.beta]
        if valid:
            raw = self.runner.analyze_beta([beta for _, beta in valid])
            for (index, _), analyses in zip(valid, raw):
                results[index].analyses = self.ranker.rank(analyses)
        if self.ranker.use_context:
            self.ranker.rerank_with_context([result.analyses for result in results])
        return results

    def analyze_text(self, text: str) -> List[TokenResult]:
        return self.analyze_tokens(tokenize(text))
