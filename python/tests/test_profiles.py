from morpheus_toolkit.analysis import Analysis
from morpheus_toolkit.profiles import apply_profile, dictionary_forms


def make(lemma: str, pos: str) -> Analysis:
    return Analysis(lemma=lemma, lemma_beta="", pos=pos, raw_pos=pos, stemtype="")


def test_dictionary_forms_maps_articles_to_nominative():
    analyses = [make("οἱ", "RA"), make("ὅς", "RR")]
    dictionary_forms(analyses)
    assert analyses[0].lemma == "ὁ"
    assert analyses[0].pos == "RA"
    # A relative-pronoun reading of the same form is left alone.
    assert analyses[1].lemma == "ὅς"


def test_apply_profile_unknown_is_noop():
    analyses = [make("οἱ", "RA")]
    apply_profile("nope", analyses)
    assert analyses[0].lemma == "οἱ"
    apply_profile("morphgnt", analyses)
    assert analyses[0].lemma == "ὁ"
