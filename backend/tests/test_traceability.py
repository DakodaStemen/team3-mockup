import pytest

from scripts import trace


@pytest.mark.req("NFR-10")
def test_every_testable_requirement_has_a_test_and_matrix_is_current():
    reqs, links = trace.requirements(), trace.tagged_tests()
    assert len(reqs) >= 26  # every FR and NFR row in docs/SRS.md parsed
    assert trace.problems(reqs, links) == []
    assert trace.OUT.read_text(encoding="utf8") == trace.render(reqs, links)
