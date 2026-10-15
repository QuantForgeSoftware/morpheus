from morpheus_toolkit.numerals import propose


def test_numeral_case_fallback():
    # Numeral case is meaningless (α = Α = 1): a lowercase letter resolves via
    # the table's capital entry (beta ``*`` prefix).
    assert propose("a").lemma == propose("*a").lemma == "Α"
    assert propose("e").lemma == propose("*e").lemma == "Ε"


def test_unknown_form_is_none():
    assert propose("zzz") is None
    assert propose("") is None
