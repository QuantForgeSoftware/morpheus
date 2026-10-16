import math

from morpheus_toolkit import calibration
from morpheus_toolkit.calibration import (
    class_masses,
    coarse_pos,
    expected_calibration_error,
    load_temperature,
    softmax_confidences,
)


def test_softmax_sums_to_one():
    probs = softmax_confidences([0.5, 0.2, 0.1], 1.0)
    assert abs(sum(probs) - 1.0) < 1e-9
    assert probs[0] > probs[1] > probs[2]


def test_temperature_sharpens_and_flattens():
    scores = [1.0, 0.0]
    sharp = softmax_confidences(scores, 0.1)
    flat = softmax_confidences(scores, 10.0)
    assert sharp[0] > flat[0]
    assert flat[0] > 0.5


def test_ece_zero_when_perfectly_calibrated():
    # Confidence 1.0, always correct => per-bin gap 0.
    assert expected_calibration_error([1.0, 1.0, 1.0], [1, 1, 1]) == 0.0


def test_ece_detects_overconfidence():
    # Confidence 1.0 but only half correct => gap 0.5.
    ece = expected_calibration_error([1.0, 1.0], [1, 0])
    assert abs(ece - 0.5) < 1e-9


def test_ece_empty():
    assert expected_calibration_error([], []) == 0.0


def test_load_temperature_selects_path(monkeypatch):
    monkeypatch.setattr(calibration, "load_calibration",
                        lambda: {"temperature": 0.08, "temperature_learned": 0.31})
    assert calibration.load_temperature() == 0.08
    assert calibration.load_temperature(learned=True) == 0.31


def test_load_temperature_falls_back_to_frequency(monkeypatch):
    monkeypatch.setattr(calibration, "load_calibration", lambda: {"temperature": 0.08})
    assert calibration.load_temperature(learned=True) == 0.08


def test_coarse_pos_folds_article_pronoun_and_other_classes():
    assert coarse_pos("N") == "N"
    assert coarse_pos("RA") == "R"
    assert coarse_pos("RP") == "R"
    assert coarse_pos("I") == "X"
    assert coarse_pos("") == "?"
    assert coarse_pos("ZZ") == "?"


def test_class_masses_sum_confidences_per_class():
    masses = class_masses(["N", "V", "N"], [0.5, 0.3, 0.2])
    assert abs(masses[0] - 0.7) < 1e-9
    assert abs(masses[1] - 0.3) < 1e-9
    assert abs(masses[2] - 0.7) < 1e-9


def test_load_temperature_selects_by_score_path(monkeypatch):
    monkeypatch.setattr(
        calibration,
        "load_calibration",
        lambda: {"temperature": 0.5, "temperature_joint": 0.9, "temperature_learned": 1.2},
    )
    assert load_temperature() == 0.5
    assert load_temperature(joint=True) == 0.9
    assert load_temperature(learned=True) == 1.2
    # Unfitted paths fall back to the frequency temperature.
    monkeypatch.setattr(calibration, "load_calibration", lambda: {"temperature": 0.5})
    assert load_temperature(joint=True) == 0.5
    assert load_temperature(learned=True) == 0.5


def test_load_pos_reliability_selects_by_score_path(monkeypatch):
    monkeypatch.setattr(
        calibration,
        "load_calibration",
        lambda: {
            "pos_reliability": {"N": 0.9, "other": 0.8},
            "pos_reliability_learned": {"N": 0.95, "other": 0.85},
        },
    )
    assert calibration.load_pos_reliability()["N"] == 0.9
    assert calibration.load_pos_reliability(learned=True)["N"] == 0.95
    # The joint path falls back to the plain table when it has not been fitted.
    assert calibration.load_pos_reliability(joint=True)["N"] == 0.9
