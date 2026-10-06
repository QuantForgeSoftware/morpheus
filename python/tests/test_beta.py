from morpheus_toolkit.beta import from_beta, normalize_lemma, strip_homonym, to_beta


def test_roundtrip():
    assert to_beta("ἄνθρωπος") == "a)/nqrwpos"
    assert from_beta("a)/nqrwpos") == "ἄνθρωπος"


def test_strip_homonym():
    assert strip_homonym("le/gw1") == "le/gw"
    assert strip_homonym("lo/gos") == "lo/gos"


def test_normalize_lemma():
    assert normalize_lemma("Λόγος") == "λόγος"
    assert normalize_lemma("le/gw1") == normalize_lemma("le/gw2")
    # `^` (a Morpheus artifact) is removed
    assert "^" not in normalize_lemma("gene/sew^s")
