import math

from morpheus_toolkit.calibration import (
    expected_calibration_error,
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
