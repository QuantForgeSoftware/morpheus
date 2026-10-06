from morpheus_toolkit.analysis import Analysis
from morpheus_toolkit.morphgnt import parsing_code, pos_code


def analysis(**kwargs) -> Analysis:
    base = dict(lemma="x", lemma_beta="", pos="N", raw_pos="N", stemtype="")
    base.update(kwargs)
    return Analysis(**base)


def test_pos_codes():
    assert pos_code(analysis(pos="N")) == "N-"
    assert pos_code(analysis(pos="V")) == "V-"
    assert pos_code(analysis(pos="RA")) == "RA"
    assert pos_code(analysis(pos="N", proposed=True)) == "NP"


def test_parsing_code_finite_verb():
    verb = analysis(
        pos="V",
        features={"person": ("3rd",), "tense": ("aor",), "voice": ("act",), "mood": ("ind",), "number": ("sg",)},
    )
    assert parsing_code(verb) == "3AAI-S--"


def test_parsing_code_participle_and_article():
    participle = analysis(
        pos="V",
        features={
            "tense": ("pres",),
            "voice": ("act",),
            "mood": ("part",),
            "case": ("nom",),
            "number": ("sg",),
            "gender": ("fem",),
        },
    )
    assert parsing_code(participle) == "-PAPNSF-"
    assert parsing_code(analysis(pos="RA", features={"case": ("acc",), "number": ("sg",), "gender": ("masc",)})) == "----ASM-"
