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


class StubRanker:
    def __init__(self, joint):
        self.joint = joint


class StubAnalyzer:
    def __init__(self, joint):
        self.ranker = StubRanker(joint)


def test_base_lemmas_strips_guarded_preverb():
    analyzer = StubAnalyzer({"λύω": {"V": 10}, "ἐκκλησιάζω": {"V": 2}})
    analyses = [make("ἀπολύω", "V"), make("ἐκκλησιάζω", "V")]
    apply_profile("base-lemmas", analyses, analyzer=analyzer)
    assert analyses[0].lemma == "λύω"
    assert analyses[0].lemma_variants == ("λύω",)
    # Remainder (κλησιάζω) is not an attested verb -> the guard keeps the lemma.
    assert analyses[1].lemma == "ἐκκλησιάζω"


def test_base_lemmas_tail_rule_for_contracted_compounds():
    analyzer = StubAnalyzer({"ἔρχομαι": {"V": 5}})
    analyses = [make("διέρχομαι", "V"), make("ἔρχομαι", "V")]
    apply_profile("base-lemmas", analyses, analyzer=analyzer)
    assert analyses[0].lemma == "ἔρχομαι"  # δι- remnant + attested tail
    assert analyses[1].lemma == "ἔρχομαι"  # simplex unchanged


def test_base_lemmas_ignores_non_verbs():
    analyzer = StubAnalyzer({"λύω": {"V": 10}})
    analyses = [make("ἀπόστολος", "N")]
    apply_profile("base-lemmas", analyses, analyzer=analyzer)
    assert analyses[0].lemma == "ἀπόστολος"


def test_base_lemmas_uses_bundled_table_standalone():
    analyses = [make("ἀπολύω", "V")]
    apply_profile("base-lemmas", analyses)
    assert analyses[0].lemma == "λύω"


def test_profiles_combine_left_to_right():
    analyzer = StubAnalyzer({"λύω": {"V": 10}})
    analyses = [make("οἱ", "RA"), make("ἀπολύω", "V")]
    apply_profile("morphgnt,base-lemmas", analyses, analyzer=analyzer)
    assert analyses[0].lemma == "ὁ"
    assert analyses[1].lemma == "λύω"
