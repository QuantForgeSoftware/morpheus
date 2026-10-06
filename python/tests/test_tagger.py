from morpheus_toolkit.analysis import Analysis
from morpheus_toolkit.tagger import PosTagger


def make(lemma: str, pos: str, score: float) -> Analysis:
    analysis = Analysis(lemma=lemma, lemma_beta="", pos=pos, raw_pos=pos, stemtype="")
    analysis.score = score
    return analysis


def test_tagger_uses_context_to_choose_pos():
    # The model strongly prefers an article followed by a noun.
    model = {
        "unigrams": {"RA": 10, "N": 10, "V": 10},
        "bigrams": {"<s>": {"RA": 10}, "RA": {"N": 10, "V": 1}},
        "starts": {"RA": 10},
    }
    tagger = PosTagger(model, emission_weight=0.1)

    article = [make("ὁ", "RA", 1.0)]
    noun = make("θεός", "N", 0.5)
    verb = make("θεάομαι", "V", 0.6)  # higher emission, but worse context

    chosen = tagger.tag([article, [verb, noun]])
    assert chosen[0] is article[0]
    assert chosen[1] is noun


def test_tagger_handles_misses():
    model = {"unigrams": {"N": 1}, "bigrams": {"<s>": {"N": 1}, "N": {"N": 1}}, "starts": {"N": 1}}
    tagger = PosTagger(model)
    chosen = tagger.tag([[], [make("λόγος", "N", 1.0)]])
    assert chosen[0] is None
    assert chosen[1].lemma == "λόγος"
