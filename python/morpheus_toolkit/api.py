"""High-level API: analyze raw text or token lists."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Union

from .analysis import Analysis
from .beta import from_beta, to_beta
from .calibration import (
    class_masses,
    coarse_pos,
    load_pos_reliability,
    load_proposal_priors,
    load_temperature,
    softmax_confidences,
)
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
        use_homograph_context: bool = False,
        numerals: Union[bool, str] = False,
        recovery: bool = True,
        language: str = "greek",
        use_learned: bool = True,
        adaptive_tables: bool = True,
        temperature: Optional[float] = None,
        profile: Optional[str] = None,
        jobs: int = 1,
    ):
        self.language = (language or "greek").lower()
        self.runner = runner or MorpheusRunner(
            morpheus_dir=morpheus_dir, language=self.language, jobs=jobs
        )
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
        # Opt-in: re-rank ambiguous forms by context-conditional gold counts
        # (data/homograph_contexts.json). Off by default — behavior unchanged.
        self.use_homograph_context = use_homograph_context
        # Opt-in: unanalyzed Greek letter-numeral tokens get a synthetic analysis
        # from data/papyrus_numerals.json. Off by default — behavior unchanged.
        # ``"auto"`` applies it only when adaptive table selection picks the
        # papyri table for this input (so numeral proposals never appear in other
        # registers); it needs adaptive selection to run (explicit frequencies or
        # adaptive_tables=False disable it).
        if isinstance(numerals, str):
            if numerals.lower() != "auto":
                raise ValueError(f"numerals must be a bool or 'auto', got {numerals!r}")
            numerals = "auto"
        self.numerals = numerals
        # On by default (Greek, Round 16): unanalyzed Greek tokens are retried
        # with generic normalization candidates (spelling variants, name
        # lemmatization); analyzed tokens are never touched. Pass False to keep
        # the previous behavior (misses stay misses).
        self.recovery = recovery
        # On by default (Greek): re-rank candidates with the learned model
        # (data/learned_reranker.json). Pass False to keep frequency order.
        self.use_learned = use_learned
        self._learned_ranker = None
        # On by default (Greek): pick the best-fitting bundled frequency table per
        # input instead of one fixed table. Caller-supplied ``frequencies`` win;
        # pass False to keep the configured table.
        self.adaptive_tables = adaptive_tables
        self._table_set = None
        self._selected_table = None
        self._explicit_frequencies = frequencies is not None
        # Softmax temperature for the reported confidence. None => the bundled
        # calibrated value (data/calibration.json); 1.0 opts out. The temperature
        # is picked for the score scale that actually produced the final order
        # (frequency vs learned; see _finish).
        self._temperature = temperature
        self._proposal_priors = None
        self._pos_reliability = None
        self._learned_scores = False
        # Optional output-convention profile (e.g. "morphgnt"): rewrites lemma/POS
        # presentation only. None => natural Morpheus output.
        self.profile = profile

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
        if self.numerals is True and not self.is_latin:
            self._apply_numerals(results)
        # Adaptive table selection runs before recovery so name proposals can be
        # re-accented from the chosen table; the proper-noun fallback runs after
        # recovery so the more specific proposals win.
        if self.adaptive_tables and not self.is_latin:
            self._apply_adaptive_tables(results)
            # ``numerals="auto"`` fires only on papyri-selected inputs; it runs
            # here (not above) so numeral proposals cannot skew the selection.
            if self.numerals == "auto" and self._selected_table == "papyri":
                self._apply_numerals(results)
        if self.recovery and not self.is_latin:
            self._apply_recovery(results)
        if self.unknown_as_proper:
            for result in results:
                if not result.analyses and result.beta:
                    result.analyses = [self._propose(result)]
        for result in results:
            result.analyses = self.ranker.rank(result.analyses)
        if self.use_learned and not self.is_latin:
            self._apply_learned(results)
            self._learned_scores = True
        if self.ranker.use_context:
            self.ranker.rerank_with_context([result.analyses for result in results])
            self._learned_scores = False
        if self.use_homograph_context and not self.is_latin:
            self._apply_homographs(results)
            self._learned_scores = False
        if self.profile:
            from .profiles import apply_profile

            for result in results:
                apply_profile(self.profile, result.analyses, analyzer=self)
        for result in results:
            self._annotate(result.analyses, result.token or from_beta(result.beta) or "")
        return results

    def _apply_homographs(self, results: List[TokenResult]) -> None:
        """Re-rank ambiguous forms using the context table (opt-in; Greek only).

        Context = the neighbours' current top-1 POS, so this runs after all other
        ranking passes. Tokens whose form is not in the table are untouched.
        """
        from .homographs import rerank

        for i, result in enumerate(results):
            if len(result.analyses) < 2 or not result.beta:
                continue
            prev = results[i - 1].analyses[0].pos if i > 0 and results[i - 1].analyses else None
            nxt = (results[i + 1].analyses[0].pos
                   if i + 1 < len(results) and results[i + 1].analyses else None)
            result.analyses = rerank(result.analyses, result.beta, prev, nxt)

    def _apply_adaptive_tables(self, results: List[TokenResult]) -> None:
        """Pick the best-fitting bundled frequency table for this input (default on).

        Runs before ranking so the whole input is ranked with one table chosen
        from its own candidate lemmas (see ``tables.TableSet``). Caller-supplied
        frequencies are never overridden.
        """
        from .tables import load_table_set

        if self._explicit_frequencies:
            return
        if self._table_set is None:
            self._table_set = load_table_set()
        name = self._table_set.select([result.analyses for result in results])
        self._selected_table = name
        self.ranker.set_frequencies(self._table_set.frequencies(name))

    def _apply_learned(self, results: List[TokenResult]) -> None:
        """Re-rank all candidates with the learned model (default on; Greek only).

        Uses the frequency tables configured on the ranker for its feature
        extraction, so it stays consistent with how the model was trained.
        """
        from .learned import LearnedRanker, load_default_model

        if self._learned_ranker is None:
            self._learned_ranker = LearnedRanker(
                load_default_model(),
                frequencies=self.ranker.frequencies,
                joint=self.ranker.joint,
            )
        ranked = self._learned_ranker.rank_sequence(
            [(result.beta, result.analyses) for result in results]
        )
        for result, analyses in zip(results, ranked):
            if analyses:
                result.analyses = analyses

    def _apply_numerals(self, results: List[TokenResult]) -> None:
        """Give unanalyzed letter-numeral tokens a synthetic analysis (opt-in).

        Fires only on tokens with NO analyses — analyzed forms are never
        overridden, so real short words/particles in other corpora stay safe.
        Runs before the proper-noun fallback: the numeral table is more specific.
        """
        from .numerals import propose

        for result in results:
            if not result.analyses and result.beta:
                analysis = propose(result.beta, result.token)
                if analysis is not None:
                    result.analyses = [analysis]

    def _apply_recovery(self, results: List[TokenResult]) -> None:
        """Retry unanalyzed tokens with generic normalization candidates.

        Fires only on tokens with NO analyses (like ``_apply_numerals``), so
        analyzed tokens are never touched; see ``recovery.recover`` for the two
        strategies and the ``proposed``/``recovered_from`` flags. Proposals go
        through the regular ranking passes below.
        """
        from .recovery import recover

        recover(
            [result.token or from_beta(result.beta) or "" for result in results],
            [result.analyses for result in results],
            self.runner,
            self.ranker.frequencies,
        )

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

    def _annotate(self, analyses: List[Analysis], surface: str = "") -> None:
        """Attach calibrated confidences and (for Greek) a Strong's number.

        ``confidence`` is the temperature-scaled softmax of the score path that
        produced the final order (frequency / joint / learned); ``pos_confidence``
        is the confidence mass of the analysis's coarse POS class. Tokens whose
        candidates are all proposals (recovery / numerals / unknown-as-proper)
        are scaled by the fitted per-strategy proposal priors — their softmax is
        conditional on the generated candidate set, and a lone proposal would
        otherwise report 1.0 unconditionally.
        """
        if not analyses:
            return
        if self._temperature is None:
            self._temperature = load_temperature(
                learned=self._learned_scores, joint=bool(self.ranker.joint)
            )
        scores = [analysis.score for analysis in analyses]
        confidences = softmax_confidences(scores, self._temperature)
        if all(analysis.proposed for analysis in analyses):
            if self._proposal_priors is None:
                self._proposal_priors = load_proposal_priors()
            priors = self._proposal_priors
            if priors:
                from .recovery import proposal_strategy

                confidences = [
                    confidence * priors.get(
                        proposal_strategy(analysis, surface), priors.get("other", 0.0)
                    )
                    for analysis, confidence in zip(analyses, confidences)
                ]
        classes = [coarse_pos(analysis.pos) for analysis in analyses]
        pos_confidences = class_masses(classes, confidences)
        if self._pos_reliability is None:
            self._pos_reliability = load_pos_reliability(
                learned=self._learned_scores, joint=bool(self.ranker.joint)
            )
        reliability = self._pos_reliability
        if reliability:
            # The class mass is peaked for the lemma, not for the class; the
            # fitted per-class reliability makes the product calibrated
            # (scripts/calibrate.py reports both ECEs).
            pos_confidences = [
                mass * reliability.get(name, reliability.get("other", 1.0))
                for mass, name in zip(pos_confidences, classes)
            ]
        for analysis, confidence, pos_confidence in zip(analyses, confidences, pos_confidences):
            analysis.confidence = confidence
            analysis.pos_confidence = pos_confidence
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
