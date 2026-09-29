"""Edge cases for the offline results roll-up; no network needed."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


@pytest.mark.req("NFR-07")
def test_results_statistics_tolerate_empty_and_constant_samples():
    from results import mean, median, spearman
    assert mean([]) is None and math.isnan(median([]))
    assert math.isnan(spearman([1, 1, 1], [1, 2, 3])) and math.isnan(spearman([1], [2]))
    assert spearman([1, 2, 3], [2, 4, 9]) == pytest.approx(1.0)
