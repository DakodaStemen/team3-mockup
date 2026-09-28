"""Edge cases for the offline scripts (calibration and results roll-up); no LLM or network needed."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


@pytest.mark.req("NFR-13")
@pytest.mark.parametrize("minority", [0, 1, 2, 3])
def test_calibration_refuses_too_few_examples_of_a_class(minority):
    from calibrate import MIN_PER_CLASS, evaluate
    y = np.array([1] * (45 - minority) + [0] * minority)
    with pytest.raises(ValueError, match=f"at least {MIN_PER_CLASS} correct and {MIN_PER_CLASS} incorrect"):
        evaluate(np.random.default_rng(0).random(45), y)


@pytest.mark.req("NFR-13")
def test_calibration_works_at_the_minimum():
    from calibrate import evaluate
    y = np.array([1] * 41 + [0] * 4)
    r = evaluate(np.random.default_rng(0).random(45), y)
    assert r["folds"] == 4 and 0 <= r["brier_calibrated"] <= 1 and len(r["table"]["y"]) == 21


@pytest.mark.req("NFR-13")
def test_ece_handles_edge_confidences():
    from calibrate import ece
    assert ece(np.array([1.0, 1.0]), np.array([1, 1])) == 0  # confidence 1.0 lands in the top bin, not out of range
    assert ece(np.array([0.0, 0.0]), np.array([1, 1])) == 1


@pytest.mark.req("NFR-07")
def test_results_statistics_tolerate_empty_and_constant_samples():
    from results import mean, median, spearman
    assert mean([]) is None and math.isnan(median([]))
    assert math.isnan(spearman([1, 1, 1], [1, 2, 3])) and math.isnan(spearman([1], [2]))
    assert spearman([1, 2, 3], [2, 4, 9]) == pytest.approx(1.0)
