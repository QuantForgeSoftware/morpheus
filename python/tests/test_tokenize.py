from morpheus_toolkit.tokenize import tokenize


def test_strips_punctuation_and_digits():
    assert tokenize("ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος.") == [
        "ἐν",
        "ἀρχῇ",
        "ἦν",
        "ὁ",
        "λόγος",
        "καὶ",
        "ὁ",
        "λόγος",
    ]
    assert tokenize("1:1 ἐν") == ["ἐν"]
    assert tokenize("") == []
