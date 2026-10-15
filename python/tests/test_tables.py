from morpheus_toolkit.analysis import Analysis
from morpheus_toolkit.tables import TableSet


def cand(lemma: str) -> list:
    return [Analysis(lemma=lemma, lemma_beta="", pos="N", raw_pos="N", stemtype="")]


def test_select_prefers_better_fitting_table():
    ts = TableSet(
        tables={"a": {"λύω": 100, "θεός": 90}, "b": {"ἄλλος": 100}},
        min_tokens=1,
    )
    lists = [cand("θεός"), cand("λύω"), cand("θεός")]
    assert ts.select(lists) == "a"


def test_short_input_keeps_default():
    ts = TableSet(tables={"classical": {"θεός": 100}, "koine": {"θεός": 1}}, min_tokens=40)
    assert ts.select([cand("θεός")]) == "koine"


def test_blend_normalizes_before_weighting():
    ts = TableSet(tables={"a": {"x": 1}, "b": {"x": 3}}, min_tokens=1)
    only_a = ts.blend(weights={"a": 1.0, "b": 0.0})
    only_b = ts.blend(weights={"a": 0.0, "b": 1.0})
    assert only_a["x"] > 0
    # Each table is normalized to a common mass first, so single-lemma tables
    # blend to the same value regardless of the raw counts.
    assert only_a["x"] == only_b["x"]


def test_blend_sums_masses():
    ts = TableSet(tables={"a": {"x": 1}, "b": {"x": 1}}, min_tokens=1)
    both = ts.blend(weights={"a": 1.0, "b": 1.0})
    one = ts.blend(weights={"a": 1.0, "b": 0.0})
    assert both["x"] == 2 * one["x"]
