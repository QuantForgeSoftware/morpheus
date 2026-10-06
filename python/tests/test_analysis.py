from morpheus_toolkit.analysis import fine_pos, parse_perseus_analyses


def test_parses_multiple_analyses_and_features():
    line = (
        "<NL>N a)/nqrwpos  masc nom sg\t\t\tos_ou</NL>"
        "<NL>V le/gw1  pres ind act 1st sg\t\t\tw_stem,reg_conj</NL>"
    )
    analyses = parse_perseus_analyses(line)
    assert len(analyses) == 2

    noun, verb = analyses
    assert noun.pos == "N"
    assert noun.lemma == "ἄνθρωπος"
    assert noun.features["gender"] == ("masc",)
    assert noun.features["case"] == ("nom",)
    assert noun.features["number"] == ("sg",)

    assert verb.pos == "V"
    assert verb.lemma == "λέγω"  # homonym digit stripped
    assert verb.features["mood"] == ("ind",)
    assert verb.features["person"] == ("1st",)


def test_lemma_variants_are_split_and_matched():
    line = "<NL>N gene/sew^s,ge/nesis  fem gen sg\t\t\th_hs</NL>"
    analysis = parse_perseus_analyses(line)[0]
    assert len(analysis.lemma_variants) == 2
    assert analysis.lemma == "γένεσις"  # the canonical lemma is the last variant
    assert analysis.matches_lemma("γένεσις")


def test_fine_pos_from_stemtype():
    assert fine_pos("N", "article") == "RA"
    assert fine_pos("N", "prep") == "P"
    assert fine_pos("N", "adverb") == "D"
    assert fine_pos("N", "conj") == "C"
    assert fine_pos("N", "particle") == "X"
    assert fine_pos("N", "relative") == "RR"
    assert fine_pos("N", "art_adj") == "A"
    assert fine_pos("N", "os_ou") == "N"
    assert fine_pos("V", "") == "V"
    assert fine_pos("P", "w_stem") == "V"  # participles are V
