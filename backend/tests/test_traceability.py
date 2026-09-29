import pytest

from scripts import trace


@pytest.mark.req("COM-05")
def test_register_traced_and_matrix_current():
    reqs, links = trace.requirements(), trace.tagged_tests()
    assert len(reqs) >= 45  # every row in docs/01-product-requirements/requirements-register.md parsed
    assert trace.problems(reqs, links) == []
    assert trace.current(trace.OUT) == trace.render(reqs, links), "run: uv run python scripts/trace.py"
