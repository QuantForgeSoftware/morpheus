from morpheus_toolkit.analysis import Analysis
from morpheus_toolkit.api import Morpheus
from morpheus_toolkit.beta import to_beta
from morpheus_toolkit.recovery import (
    name_candidates,
    normalize,
    spelling_variants,
    subscript_variants,
)


def test_normalize_strips_accents_and_case():
    assert normalize("ἥμυσυ") == "ημυσυ"
    assert normalize("Δωρίωνος") == "δωριωνοσ"  # final ς normalizes to σ
    assert normalize("παρʼ") == "παρ"


def test_spelling_variants_itacism_and_monophthongization():
    variants = spelling_variants("ἥμυσυ")
    assert "ημισυ" in variants  # υ -> ι
    variants = spelling_variants("εὔχομε")
    assert "ευχομαι" in variants  # final ε -> αι
    variants = spelling_variants("χρίαν")
    assert "χρειαν" in variants  # ι -> ει


def test_spelling_variants_geminate_and_final_nu():
    assert "μελις" in spelling_variants("μέλλις")  # λλ -> λ (ς kept for display)
    assert "ευχομεν" in spelling_variants("εὔχομε")  # final -ν added


def test_spelling_variants_are_deterministic_and_capped():
    first = spelling_variants("ἀσπάζομε")
    assert first == spelling_variants("ἀσπάζομε")
    assert len(first) <= 96
    assert spelling_variants("α") == []


def test_name_candidates_oblique_to_nominative():
    assert "δωριων" in name_candidates("Δωρίωνος")
    assert "αχιλλας" in name_candidates("Ἀχιλλᾶτος")
    assert "σωτελης" in name_candidates("Σωτέλῃ")
    assert "διοσκουριδης" in name_candidates("Διοσκουρίδει")
    assert "διδυμαριον" in name_candidates("Διδυμάριν")
    assert "θαρσικαριος" in name_candidates("θαρσικαρίῳ")


def test_spelling_variants_sandhi_and_documentary_rules():
    assert "μεν" in spelling_variants("μὲγ")  # final sandhi γ -> ν
    assert "εαν" in spelling_variants("ἐὰμ")  # final sandhi μ -> ν
    assert "ημερας" in spelling_variants("ἡμείρας")  # ει -> ε
    assert "βουκολος" in spelling_variants("βυκόλος")  # υ -> ου
    assert "αντιληψεως" in spelling_variants("ἀντιλήμψεως")  # μψ -> ψ
    assert "σμηνων" in spelling_variants("ζμηνῶν")  # ζ -> σ
    # internal nasal assimilation: ν assimilates to a following labial/velar
    assert "συμπροσγενομενος" in spelling_variants("συνπροσγενόμενος")
    assert "εγγηαλλιουσαις" in spelling_variants("ἐνγηαλλιούσαις")
    assert "ανηγκασε" in spelling_variants("ἀνήνκασε")


def test_spelling_variants_compose_operations_pairwise():
    # two class substitutions (υ -> ι and ει -> ι): θρυδάκεια for θριδάκια
    assert "θριδακια" in spelling_variants("θρυδάκεια")
    # a class substitution with a geminate simplification: ὑγειαίνησς for ὑγιαίνῃς
    assert "υγιαινης" in spelling_variants("ὑγειαίνησς")
    # two geminate simplifications: ββ and λλ in one form
    assert "εμβλομενος" in spelling_variants("ἐμββλλόμενος")


def test_name_candidates_more_endings():
    assert "ρηναιος" in name_candidates("Ῥηναίους")
    assert "χοινωθμις" in name_candidates("Χοινώθμεως")
    assert "δωριων" in name_candidates("Δωρίωνα")


def test_subscript_variants_restore_eta_positions():
    assert subscript_variants("υγιαινης") == ["υγιαινῃς"]
    assert subscript_variants("ημελησεν") == ["ῃμελησεν", "ημελῃσεν"]
    assert subscript_variants("μεν") == []


class RecoveryRunner:
    """Knows only the unaccented normalized forms used by the recovery pass."""

    def __init__(self, known):
        self.known = known

    def analyze_beta(self, forms, ignore_accents=False):
        return [list(self.known.get(form, ())) for form in forms]


def _analysis(lemma):
    return Analysis(lemma=lemma, lemma_beta=to_beta(lemma), pos="V", raw_pos="V",
                    stemtype="w_pr")


def test_recovery_is_on_by_default():
    beta = to_beta("ευχομαι")
    runner = RecoveryRunner({beta: [_analysis("εὔχομαι")]})
    analyzer = Morpheus(runner=runner, frequencies={})
    result = analyzer.analyze_tokens(["εὔχομε"])[0]
    assert result.best is not None
    assert result.best.recovered_from == "ευχομαι"


def test_recovery_opt_out_keeps_misses():
    beta = to_beta("ευχομαι")
    runner = RecoveryRunner({beta: [_analysis("εὔχομαι")]})
    analyzer = Morpheus(runner=runner, frequencies={}, recovery=False)
    assert analyzer.analyze_tokens(["εὔχομε"])[0].is_miss


def test_recovery_recovers_spelling_variant():
    beta = to_beta("ευχομαι")
    runner = RecoveryRunner({beta: [_analysis("εὔχομαι")]})
    analyzer = Morpheus(runner=runner, frequencies={}, recovery=True)
    result = analyzer.analyze_tokens(["εὔχομε"])[0]
    assert result.best is not None
    assert result.best.lemma == "εὔχομαι"
    assert result.best.proposed is True
    assert result.best.recovered_from == "ευχομαι"


def test_recovery_restores_iota_subscript():
    beta = to_beta("υγιαινῃς")
    runner = RecoveryRunner({beta: [_analysis("ὑγιαίνω")]})
    analyzer = Morpheus(runner=runner, frequencies={}, recovery=True)
    result = analyzer.analyze_tokens(["ὑγειαίνῃς"])[0]
    assert result.best is not None
    assert result.best.lemma == "ὑγιαίνω"
    assert result.best.proposed is True
    assert result.best.recovered_from == "υγιαινῃς"


def test_recovery_never_touches_analyzed_tokens():
    beta = to_beta("λόγος")
    runner = RecoveryRunner({beta: [Analysis(lemma="λόγος", lemma_beta=beta, pos="N",
                                             raw_pos="N", stemtype="os_ou")]})
    analyzer = Morpheus(runner=runner, frequencies={}, recovery=True)
    result = analyzer.analyze_tokens(["λόγος"])[0]
    assert result.best.lemma == "λόγος"
    assert result.best.proposed is False
    assert result.best.recovered_from is None


def test_recovery_name_proposal_reaccented_from_table():
    analyzer = Morpheus(runner=RecoveryRunner({}), frequencies={"δωρίων": 9},
                        recovery=True)
    result = analyzer.analyze_tokens(["Δωρίωνος"])[0]
    assert result.best.lemma == "Δωρίων"  # re-accented, capitalized
    assert result.best.pos == "N"
    assert result.best.proposed is True
    assert result.best.recovered_from == "δωριων"


def test_recovery_name_confirmed_by_stemlib_reading():
    beta = to_beta("μακεδων")
    runner = RecoveryRunner({beta: [Analysis(lemma="Μακεδών", lemma_beta=beta, pos="N",
                                             raw_pos="N", stemtype="ont_ontos")]})
    analyzer = Morpheus(runner=runner, frequencies={}, recovery=True)
    result = analyzer.analyze_tokens(["Μακεδώνος"])[0]
    assert result.best.lemma == "Μακεδών"
    assert result.best.proposed is True
    assert result.best.recovered_from == "μακεδων"


def test_recovered_from_is_in_dict():
    analyzer = Morpheus(runner=RecoveryRunner({}), frequencies={"δωρίων": 9},
                        recovery=True)
    payload = analyzer.analyze_tokens(["Δωρίωνος"])[0].to_dict()
    assert payload["analyses"][0]["recovered_from"] == "δωριων"
    assert payload["analyses"][0]["proposed"] is True


def test_proposal_strategy_classes():
    from morpheus_toolkit.analysis import Analysis
    from morpheus_toolkit.recovery import proposal_strategy

    native = Analysis(lemma="λόγος", lemma_beta="", pos="N", raw_pos="N", stemtype="os_ou")
    assert proposal_strategy(native, "λόγος") == ""
    numeral = Analysis(lemma="α", lemma_beta="", pos="N", raw_pos="N",
                       stemtype="numeral", proposed=True)
    assert proposal_strategy(numeral, "α") == "numeral"
    proper = Analysis(lemma="Δαυίδ", lemma_beta="", pos="N", raw_pos="N",
                      stemtype="proper", proposed=True)
    assert proposal_strategy(proper, "Δαυίδ") == "proper"
    spelling = Analysis(lemma="ἥμισυ", lemma_beta="", pos="N", raw_pos="N", stemtype="",
                        proposed=True, recovered_from="ημισυ")
    assert proposal_strategy(spelling, "ἥμυσυ") == "spelling"
    name = Analysis(lemma="Δωρίων", lemma_beta="", pos="N", raw_pos="N",
                    stemtype="proper", proposed=True, recovered_from="δωριων")
    assert proposal_strategy(name, "Δωρίωνος") == "name"
