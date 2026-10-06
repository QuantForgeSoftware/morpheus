"""High-level API: analyze raw text or token lists."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .analysis import Analysis
from .beta import from_beta, to_beta
from .ranking import Ranker, load_default_frequencies
from .runner import MorpheusRunner
from .strongs import strongs_for
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
        unknown_as_proper: bool = False,
        ignore_accents: bool = False,
        language: str = "greek",
    ):
        self.language = (language or "greek").lower()
        self.runner = runner or MorpheusRunner(morpheus_dir=morpheus_dir, language=self.language)
        self.ranker = Ranker(
            frequencies if frequencies is not None else load_default_frequencies(),
            use_context=use_context,
        )
        # When set, tokens Morpheus cannot analyze get a synthetic proper-noun
        # analysis (lemma = the surface form), so names are never left blank.
        self.unknown_as_proper = unknown_as_proper
        # When set, tokens the accented match misses are retried without accents
        # (recovering unaccented text such as verse-initial capitals).
        self.ignore_accents = ignore_accents

    @property
    def is_latin(self) -> bool:
        return self.language in {"latin", "la", "lat"}

    def analyze_beta(self, forms: List[str]) -> List[TokenResult]:
        results = [TokenResult(token=form, beta=form) for form in forms]
        for result, analyses in zip(results, self.runner.analyze_beta(forms)):
            result.analyses = analyses
        return self._finish(results)

    def analyze_tokens(self, tokens: Iterable[str]) -> List[TokenResult]:
        tokens = list(tokens)
        if self.is_latin:
            results = [TokenResult(token=token, beta=token) for token in tokens]
            for result, analyses in zip(results, self.runner.analyze_beta(tokens)):
                result.analyses = analyses
        else:
            results = [TokenResult(token=token, beta=to_beta(token)) for token in tokens]
            valid = [(index, result.beta) for index, result in enumerate(results) if result.beta]
            if valid:
                raw = self.runner.analyze_beta([beta for _, beta in valid])
                for (index, _), analyses in zip(valid, raw):
                    results[index].analyses = analyses
        return self._finish(results)

    def analyze_text(self, text: str) -> List[TokenResult]:
        return self.analyze_tokens(tokenize(text))

    def _finish(self, results: List[TokenResult]) -> List[TokenResult]:
        if self.ignore_accents:
            self._recover_unaccented(results)
        if self.unknown_as_proper:
            for result in results:
                if not result.analyses and result.beta:
                    result.analyses = [self._propose(result)]
        for result in results:
            result.analyses = self.ranker.rank(result.analyses)
        if self.ranker.use_context:
            self.ranker.rerank_with_context([result.analyses for result in results])
        for result in results:
            self._annotate(result.analyses)
        return results

    def _recover_unaccented(self, results: List[TokenResult]) -> None:
        """Retry, without accents, the words the accented match missed.

        Transcriptions often drop accents and breathings (e.g. a verse-initial
        capital); Morpheus's ``-n`` mode matches them against the stemlib.
        """
        misses = [
            (index, result.beta)
            for index, result in enumerate(results)
            if not result.analyses and result.beta
        ]
        if not misses:
            return
        raw = self.runner.analyze_beta([beta for _, beta in misses], ignore_accents=True)
        for (index, _), analyses in zip(misses, raw):
            results[index].analyses = analyses

    def _annotate(self, analyses: List[Analysis]) -> None:
        """Attach a softmax confidence and (for Greek) a Strong's number."""
        if not analyses:
            return
        scores = [analysis.score for analysis in analyses]
        top = max(scores)
        weights = [math.exp(score - top) for score in scores]
        total = sum(weights) or 1.0
        for analysis, weight in zip(analyses, weights):
            analysis.confidence = weight / total
            if not self.is_latin:
                analysis.strongs = strongs_for(analysis.lemma)
                if analysis.strongs is None:
                    for variant in analysis.variants():
                        found = strongs_for(variant)
                        if found:
                            analysis.strongs = found
                            break

    def _propose(self, result: TokenResult) -> Analysis:
        lemma = result.token if self.is_latin else (from_beta(result.beta) or result.token)
        return Analysis(
            lemma=lemma,
            lemma_beta=result.beta,
            pos="N",
            raw_pos="N",
            stemtype="proper",
            proposed=True,
        )
