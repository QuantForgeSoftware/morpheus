from morpheus_toolkit.analysis import Analysis
from morpheus_toolkit.api import Morpheus


class FakeRunner:
    """Returns an analysis only for λόγος, so the second token is a miss."""

    def analyze_beta(self, forms):
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
