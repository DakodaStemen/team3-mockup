"""Prerequisite-text parser checks, using phrasings copied from the live catalog and roadmaps."""
from scripts.ingest import parse_requisites


def flat(groups):
    return [[(a["course"], a["grade_minimum"], a["concurrent_ok"]) for a in g] for g in groups]


def test_grade_and_and():
    g, _, _ = parse_requisites("CSE 2010 with a grade of C or better and MATH 2372")
    assert flat(g) == [[("CSE 2010", "C", False)], [("MATH 2372", "D-", False)]]


def test_or_with_non_course_alternative():
    g, _, notes = parse_requisites("MATH 1401 or MATH 1403 or satisfactory score on department placement exam")
    assert flat(g) == [[("MATH 1401", "D-", False), ("MATH 1403", "D-", False)]]
    assert notes == ["satisfactory score on department placement exam"]


def test_c_minus_and_pre_or_coreq():
    g, _, _ = parse_requisites("MATH 2210 with a grade of C- or better; and MATH 2220 as a pre- or co-requisite")
    assert flat(g) == [[("MATH 2210", "C-", False)], [("MATH 2220", "D-", True)]]


def test_grade_with_gpa_and_q2s_code_ignored():
    g, _, _ = parse_requisites("MATH 2210 or MATH 2120Q2S with a grade of C- (1.7) or better")
    assert flat(g) == [[("MATH 2210", "C-", False)]]


def test_subject_carry_and_comma_list():
    assert flat(parse_requisites("PHYS 2000 and 2000L")[0]) == [[("PHYS 2000", "D-", False)], [("PHYS 2000L", "D-", False)]]
    assert len(parse_requisites("MATH 2220, PHYS 2500, PHYS 2500L")[0]) == 3


def test_standing_and_roadmap_coreq():
    assert parse_requisites("Senior Standing")[1] == 90
    g, _, _ = parse_requisites("MATH 2210; MATH 2220 (Corequisite)")
    assert flat(g) == [[("MATH 2210", "D-", False)], [("MATH 2220", "D-", True)]]


def test_consent_alternative_keeps_courses():
    g, _, notes = parse_requisites("CSE 5300 or CSE 4100 or consent of instructor")
    assert [a["course"] for a in g[0]] == ["CSE 5300", "CSE 4100"] and notes == ["consent of instructor"]
