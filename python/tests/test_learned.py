from morpheus_toolkit.analysis import Analysis
from morpheus_toolkit.learned import LearnedRanker, _freq_bucket


def make(lemma: str, pos: str, **kwargs) -> Analysis:
    kwargs.setdefault("stemtype", "")
    return Analysis(lemma=lemma, lemma_beta="", pos=pos, raw_pos=pos, **kwargs)


def test_freq_bucket_boundaries():
    assert _freq_bucket(0.0) == "0"
    assert _freq_bucket(0.5) == "1"
    assert _freq_bucket(9.9) == "7+"


def test_model_without_weights_is_neutral_frequency_order():
    # A model with no weights scores every candidate 0; ties break by frequency.
    noun = make("θεός", "N")
    verb = make("θεάομαι", "V")
    ranker = LearnedRanker({"weights": {}}, frequencies={"θεός": 1000, "θεάομαι": 5})
    ranked = ranker.rank([verb, noun], "qeo/s")
    assert ranked[0].lemma == "θεός"


def test_learned_weights_can_override_frequency():
    # A hand-made model that strongly prefers the verb reading via its POS feature.
    verb = make("θεάομαι", "V")
    noun = make("θεός", "N")
    model = {"weights": {"pos=V": 5.0, "pos=N": -5.0}}
    ranker = LearnedRanker(model, frequencies={"θεός": 1000, "θεάομαι": 5})
    ranked = ranker.rank([noun, verb], "qeo/s")
    assert ranked[0].lemma == "θεάομαι"


def test_features_include_context_and_rank():
    analysis = make("θεός", "N", stemtype="os_ou")
    ranker = LearnedRanker({"weights": {}}, frequencies={"θεός": 100})
    feats = ranker.features(analysis, "qeo/s", ("RA", "ὁ"), ("V", None), 0)
    assert feats["pos=N"] == 1.0
    assert feats["stem=os_ou"] == 1.0
    assert feats["prev*pos=RA|N"] == 1.0
    assert feats["next*pos=V|N"] == 1.0
    assert feats["rank=0"] == 1.0
    # Lemma context is off unless the model was trained with it.
    assert "plem=ὁ" not in feats
    ranker_lc = LearnedRanker({"weights": {}, "lemma_context": True}, frequencies={})
    feats_lc = ranker_lc.features(analysis, "qeo/s", ("RA", "ὁ"), ("V", None), 0)
    assert feats_lc["plem=ὁ"] == 1.0
    assert feats_lc["plem*pos=ὁ|N"] == 1.0


def test_rank_sequence_uses_neighbour_pos():
    tokens = [
        ("o(", [make("ὁ", "RA", stemtype="article")]),
        ("qeos", [make("θεός", "N", stemtype="os_ou"), make("θεός", "V", stemtype="os_ou")]),
    ]
    # Favour the nominal reading after an article (RA).
    model = {"weights": {"prev*pos=RA|N": 3.0, "prev*pos=RA|V": -3.0}}
    ranker = LearnedRanker(model, frequencies={})
    ranked = ranker.rank_sequence(tokens)
    assert ranked[1][0].pos == "N"
