import math

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


def test_unattested_pos_scores_a_floor_not_zero():
    # The reference types αὐτός as RD; Morpheus tags it A. The joint table has
    # a row for the lemma but no count under this candidate's POS — it must not
    # score zero, but also must not get full plain-lemma credit (that would
    # over-promote it past attested readings of other lemmas).
    ranker = Ranker(
        {"αὐτός": 29000},
        joint_frequencies={"αὐτός": {"RD": 29000}},
    )
    floor = math.log1p(1) / ranker.log_max_joint
    assert abs(ranker.frequency_score(make("αὐτός", "A")) - floor) < 1e-9
    # Below the attested reading of the same lemma...
    assert ranker.frequency_score(make("αὐτός", "A")) < ranker.frequency_score(
        make("αὐτός", "RD")
    )
    # ...but above an unlisted lemma (no row, no plain frequency).
    assert ranker.frequency_score(make("ἄλλος", "N")) == 0.0


def test_joint_count_still_used_when_pos_attested():
    ranker = Ranker(
        {"ὁ": 88000, "τις": 300},
        joint_frequencies={"ὁ": {"RA": 88000}},
    )
    assert abs(ranker.frequency_score(make("ὁ", "RA")) - 1.0) < 1e-9
    # A candidate whose POS is absent from the row gets the floor, not plain
    # lemma frequency (which would credit it as if the pairing were attested).
    assert abs(ranker.frequency_score(make("ὁ", "N")) - math.log1p(1) / ranker.log_max_joint) < 1e-9


def test_context_bonus_prefers_nominals_after_an_article():
    assert context_bonus(make("θεός", "N"), "RA", None) > 0
    assert context_bonus(make("θεάομαι", "V"), "RA", None) < 0
    assert context_bonus(make("θεός", "N"), None, None) == 0
