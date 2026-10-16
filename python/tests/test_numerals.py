from morpheus_toolkit.numerals import propose


def test_numeral_case_fallback():
    # Numeral case is meaningless (α = Α = 1): a lowercase letter resolves via
    # the table's capital entry (beta ``*`` prefix).
    assert propose("a").lemma == propose("*a").lemma == "Α"
    assert propose("e").lemma == propose("*e").lemma == "Ε"
    # …and the reverse: a capital letter the table lacks (no ``*b`` entry)
    # resolves via its lowercase entry, re-capitalized.
    assert propose("*b").lemma == "Β"
    assert propose("*f").lemma == "Φ"


def test_unknown_form_is_none():
    assert propose("cab") is None  # vowel present: not a numeral run
    assert propose("") is None


def test_compositional_rule_vowel_less_runs():
    analysis = propose("xmg", "χμγ")
    assert analysis is not None
    assert analysis.lemma == "χμγ"
    assert analysis.stemtype == "numeral"
    assert analysis.proposed is True
    assert analysis.features["value"] == ("643",)
    assert propose("yp", "ψπ").lemma == "ψπ"
    assert propose("rcb", "ρξβ").features["value"] == ("162",)
    # the capital marker is stripped for the letter check, the surface kept
    assert propose("*gs", "Γσ").lemma == "Γσ"
    # beta-only callers (analyze_beta) get the reconstructed spelling
    assert propose("xmg").lemma == "χμγ"
    assert propose("gs").lemma == "γσ"


def test_compositional_rule_needs_two_letters_and_no_vowel():
    assert propose("at", "Ατ") is None  # α is a vowel (thousands sign)
    assert propose("c", "ξ") is None  # a single letter without a table entry
