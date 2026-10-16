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


def test_editorial_markers_inside_words_do_not_split():
    assert tokenize("ἀδελφ[οῦ]") == ["ἀδελφοῦ"]
    assert tokenize("πρὸ⸢ς⸣") == ["πρὸς"]
    assert tokenize("πο-λεως") == ["πολεως"]
    # At word edges the characters still separate tokens.
    assert tokenize("λόγος [καὶ]") == ["λόγος", "καὶ"]


def test_papygreek_annotation_spans_are_removed():
    assert tokenize("πα|gap:1|ρά") == ["παρά"]
    assert tokenize("λόγος|num:5|") == ["λόγος"]


def test_combining_editorial_marks_are_removed():
    assert tokenize("τῆ\u0323ς") == ["τῆς"]  # dot-below
    assert tokenize("λό\u0305γος") == ["λόγος"]  # overline


def test_nfd_input_is_normalized():
    assert tokenize("λο\u0301γος") == ["λόγος"]


def test_apostrophes_stay_attached_to_elided_words():
    assert tokenize("ἀλλʼ ἐγώ") == ["ἀλλʼ", "ἐγώ"]
    assert tokenize("δ' ἐγώ") == ["δ'", "ἐγώ"]


def test_crasis_stays_a_single_token():
    assert tokenize("κἀγὼ καὶ") == ["κἀγὼ", "καὶ"]
    assert tokenize("τοὐμόν") == ["τοὐμόν"]
