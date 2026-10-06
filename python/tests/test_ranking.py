from morpheus_toolkit.analysis import Analysis
from morpheus_toolkit.ranking import Ranker, context_bonus


def make(lemma: str, pos: str, **kwargs) -> Analysis:
    return Analysis(lemma=lemma, lemma_beta="", pos=pos, raw_pos=pos, stemtype="", **kwargs)


def test_frequency_ranking_promotes_the_common_lemma():
    noun = make("θεός", "N")
    verb = make("θεάομαι", "V")
    ranker = Ranker({"θεός": 1000, "θεάομαι": 5})
    ranked = ranker.rank([verb, noun])
    assert ranked[0].lemma == "θεός"


def test_lemma_variants_are_used_for_frequency():
    analysis = Analysis(
        lemma="γενεσως",
        lemma_beta="",
        pos="N",
        raw_pos="N",
        stemtype="",
        lemma_variants=("γενεσως", "γένεσις"),
    )
    ranker = Ranker({"γένεσις": 500})
    assert ranker.frequency_score(analysis) > 0


def test_context_bonus_prefers_nominals_after_an_article():
    assert context_bonus(make("θεός", "N"), "RA", None) > 0
    assert context_bonus(make("θεάομαι", "V"), "RA", None) < 0
    assert context_bonus(make("θεός", "N"), None, None) == 0
