from morpheus_toolkit.analysis import Analysis
from morpheus_toolkit.api import Morpheus


class FakeRunner:
    """Returns an analysis only for λόγος, so the second token is a miss."""

    def analyze_beta(self, forms, ignore_accents=False):
        return [
            [Analysis(lemma="λόγος", lemma_beta="lo/gos", pos="N", raw_pos="N", stemtype="os_ou")]
            if form == "lo/gos"
            else []
            for form in forms
        ]


def test_analyze_tokens_aligns_and_ranks():
    analyzer = Morpheus(runner=FakeRunner(), frequencies={"λόγος": 10})
    results = analyzer.analyze_tokens(["λόγος", "ἄνθρωπος"])
    assert results[0].best.lemma == "λόγος"
    assert results[1].is_miss


def test_analyze_text_tokenizes_and_strips_punctuation():
    analyzer = Morpheus(runner=FakeRunner(), frequencies={})
    results = analyzer.analyze_text("λόγος, ἄνθρωπος.")
    assert [result.token for result in results] == ["λόγος", "ἄνθρωπος"]


def test_token_dict_shape():
    analyzer = Morpheus(runner=FakeRunner(), frequencies={})
    payload = analyzer.analyze_tokens(["λόγος"])[0].to_dict()
    assert payload["token"] == "λόγος"
    assert payload["analyses"][0]["lemma"] == "λόγος"
    assert payload["analyses"][0]["pos"] == "N"


def test_unknown_as_proper_fallback():
    analyzer = Morpheus(runner=FakeRunner(), frequencies={}, unknown_as_proper=True)
    result = analyzer.analyze_tokens(["Δαυίδ"])[0]
    assert result.best is not None
    assert result.best.proposed is True
    assert result.best.lemma == "Δαυίδ"
    assert result.best.pos == "N"


def test_fallback_is_off_by_default():
    analyzer = Morpheus(runner=FakeRunner(), frequencies={})
    assert analyzer.analyze_tokens(["Δαυίδ"])[0].is_miss


class MissRunner:
    """Analyzes nothing, so numeral-shaped tokens stay misses without a pass."""

    def analyze_beta(self, forms, ignore_accents=False):
        return [[] for _ in forms]


class FakeTableSet:
    """Duck-typed TableSet that always selects the named table."""

    def __init__(self, name):
        self.name = name

    def select(self, candidate_lists):
        return self.name

    def frequencies(self, name):
        return {}


def _auto_analyzer(table, **kwargs):
    # No explicit frequencies: adaptive selection runs (and is faked here).
    analyzer = Morpheus(runner=MissRunner(), numerals="auto", use_learned=False,
                        recovery=False, **kwargs)
    analyzer._table_set = FakeTableSet(table)
    return analyzer


def test_numerals_auto_fires_on_papyri_table():
    result = _auto_analyzer("papyri").analyze_beta(["xmg"])[0]
    assert result.best is not None
    assert result.best.proposed is True
    assert result.best.lemma == "χμγ"


def test_numerals_auto_silent_on_other_tables():
    assert _auto_analyzer("koine").analyze_beta(["xmg"])[0].is_miss
    assert _auto_analyzer("classical").analyze_beta(["xmg"])[0].is_miss


def test_numerals_explicit_still_applies_on_other_tables():
    analyzer = Morpheus(runner=MissRunner(), numerals=True, use_learned=False,
                        recovery=False)
    analyzer._table_set = FakeTableSet("koine")
    assert analyzer.analyze_beta(["xmg"])[0].best.lemma == "χμγ"


def test_numerals_auto_requires_adaptive_selection():
    # Explicit frequencies skip selection entirely, so auto never fires.
    analyzer = Morpheus(runner=MissRunner(), frequencies={}, numerals="auto",
                        use_learned=False, recovery=False)
    assert analyzer.analyze_beta(["xmg"])[0].is_miss


def test_numerals_value_is_validated():
    import pytest

    with pytest.raises(ValueError):
        Morpheus(runner=MissRunner(), frequencies={}, numerals="sometimes")


class AccentFallbackRunner:
    """Analyzes an unaccented form only when accents are ignored."""

    def analyze_beta(self, forms, ignore_accents=False):
        return [
            [Analysis(lemma="θεός", lemma_beta="qeo/s", pos="N", raw_pos="N", stemtype="os_ou")]
            if (ignore_accents and form == "qeos")
            else []
            for form in forms
        ]


def test_ignore_accents_recovers_unaccented_words():
    analyzer = Morpheus(runner=AccentFallbackRunner(), frequencies={}, ignore_accents=True)
    result = analyzer.analyze_tokens(["θεος"])[0]  # unaccented -> beta "qeos"
    assert result.best is not None
    assert result.best.lemma == "θεός"


def test_ignore_accents_is_off_by_default():
    analyzer = Morpheus(runner=AccentFallbackRunner(), frequencies={})
    assert analyzer.analyze_tokens(["θεος"])[0].is_miss


def test_confidence_is_a_distribution():
    analyzer = Morpheus(runner=FakeRunner(), frequencies={})
    analyses = analyzer.analyze_tokens(["λόγος"])[0].analyses
    assert abs(sum(analysis.confidence for analysis in analyses) - 1.0) < 1e-9


def test_strongs_is_attached_for_greek():
    analyzer = Morpheus(runner=FakeRunner(), frequencies={})
    assert analyzer.analyze_tokens(["λόγος"])[0].best.strongs == 3056


class LatinFakeRunner:
    def analyze_beta(self, forms):
        return [
            [Analysis(lemma="femina", lemma_beta="femina", pos="N", raw_pos="N", stemtype="a_ae")]
            for _ in forms
        ]


def test_latin_skips_beta_and_strongs():
    analyzer = Morpheus(runner=LatinFakeRunner(), frequencies={}, language="latin")
    result = analyzer.analyze_tokens(["femina"])[0]
    assert result.beta == "femina"  # not beta-converted
    assert result.best.lemma == "femina"
    assert result.best.strongs is None


def test_learned_and_adaptive_are_on_by_default():
    analyzer = Morpheus(runner=FakeRunner())
    assert analyzer.use_learned is True
    assert analyzer.adaptive_tables is True


def test_learned_and_adaptive_can_be_disabled():
    analyzer = Morpheus(runner=FakeRunner(), use_learned=False, adaptive_tables=False)
    assert analyzer.use_learned is False
    assert analyzer.adaptive_tables is False


def test_explicit_frequencies_are_never_overridden():
    analyzer = Morpheus(runner=FakeRunner(), frequencies={"λόγος": 10})
    analyzer.analyze_tokens(["λόγος"])
    assert analyzer.ranker.frequencies.get("λόγος") == 10


class TwoPosRunner:
    """Two candidates with different coarse POS classes (N vs V)."""

    def analyze_beta(self, forms, ignore_accents=False):
        return [
            [
                Analysis(lemma="λόγος", lemma_beta="lo/gos", pos="N", raw_pos="N", stemtype="os_ou"),
                Analysis(lemma="λέγω", lemma_beta="le/gw", pos="V", raw_pos="V", stemtype="w_pr"),
            ]
            for _ in forms
        ]


def test_pos_confidence_is_the_class_mass(monkeypatch):
    from morpheus_toolkit import api as api_module

    monkeypatch.setattr(api_module, "load_pos_reliability", lambda **kwargs: {})
    analyzer = Morpheus(
        runner=TwoPosRunner(), frequencies={"λόγος": 10, "λέγω": 1},
        use_learned=False, adaptive_tables=False,
    )
    analyses = analyzer.analyze_tokens(["λόγος"])[0].analyses
    top = analyses[0]
    assert top.pos == "N"
    # Each class has one member here, so the class mass equals the confidence.
    assert abs(top.pos_confidence - top.confidence) < 1e-9
    other = analyses[1]
    assert abs(other.pos_confidence - other.confidence) < 1e-9
    assert abs(top.pos_confidence + other.pos_confidence - 1.0) < 1e-9


def test_pos_confidence_is_scaled_by_fitted_reliability(monkeypatch):
    from morpheus_toolkit import api as api_module

    monkeypatch.setattr(
        api_module, "load_pos_reliability", lambda **kwargs: {"N": 0.5, "other": 0.9}
    )
    analyzer = Morpheus(
        runner=TwoPosRunner(), frequencies={"λόγος": 10, "λέγω": 1},
        use_learned=False, adaptive_tables=False,
    )
    analyses = analyzer.analyze_tokens(["λόγος"])[0].analyses
    top, other = analyses[0], analyses[1]
    assert top.pos == "N"
    assert abs(top.pos_confidence - top.confidence * 0.5) < 1e-9
    # V has no fitted row -> falls back to the overall rate.
    assert abs(other.pos_confidence - other.confidence * 0.9) < 1e-9


def test_lone_proposal_confidence_uses_fitted_prior(monkeypatch):
    from morpheus_toolkit import api as api_module

    monkeypatch.setattr(api_module, "load_proposal_priors", lambda: {"other": 0.4})
    analyzer = Morpheus(
        runner=FakeRunner(), frequencies={}, unknown_as_proper=True, use_learned=False,
        adaptive_tables=False,
    )
    result = analyzer.analyze_tokens(["Δαυίδ"])[0]
    assert result.best.proposed is True
    # A lone candidate's softmax is 1.0; the fitted prior must replace it.
    assert abs(result.best.confidence - 0.4) < 1e-9


def test_native_confidence_ignores_proposal_priors(monkeypatch):
    from morpheus_toolkit import api as api_module

    monkeypatch.setattr(api_module, "load_proposal_priors", lambda: {"other": 0.4})
    analyzer = Morpheus(
        runner=FakeRunner(), frequencies={"λόγος": 10}, use_learned=False,
        adaptive_tables=False,
    )
    result = analyzer.analyze_tokens(["λόγος"])[0]
    assert result.best.proposed is False
    assert result.best.confidence > 0.9  # not scaled by the prior
