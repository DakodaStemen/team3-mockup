import json

import networkx as nx
import pytest

from planner.engine import alternatives, apply_scenario, grade_ok, make_plan, timeline, validate_plan
from planner.graph import DATA, Catalog, load_catalog, load_students
from planner.models import ScenarioEvent

CAT = load_catalog()
STUDENTS = load_students()


def check_valid(plan, profile, cap=None):
    assert validate_plan(plan, profile, CAT, cap) == []


@pytest.mark.req("FR-2", "FR-3", "FR-7", "FR-13")
@pytest.mark.parametrize("sid", STUDENTS)
def test_plans_valid_and_complete(sid):
    check_valid(make_plan(STUDENTS[sid]), STUDENTS[sid])


@pytest.mark.req("FR-3")
def test_freshman_plan_meets_catalog_total():
    assert timeline(make_plan(STUDENTS["alex"]))["total_units"] == CAT.program["catalog_total_units"]


@pytest.mark.req("FR-2")
def test_grades():
    assert grade_ok("C", "C") and grade_ok("C", "C-") and not grade_ok("C-", "C")
    assert not grade_ok("W", "D-") and not grade_ok("F", "D-")


@pytest.mark.req("FR-1", "FR-2")
def test_grade_minimum_forces_retake():
    first = make_plan(STUDENTS["jordan"]).terms[0].courses
    assert "CSE 2010" in first  # D is below the C that CSE 2020 requires


@pytest.mark.req("FR-7")
def test_spring_only_waits():
    plan = make_plan(STUDENTS["sam"])  # starts in Fall, still needs PHYS 2510
    assert "PHYS 2510" not in plan.terms[0].courses
    assert "PHYS 2510" in plan.terms[1].courses and "PHYS 2510L" in plan.terms[1].courses


@pytest.mark.req("FR-4", "NFR-2")
def test_fail_only_touches_descendants():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027"))
    planned = {c for t in plan.terms for c in t.courses}
    ripple = (nx.descendants(CAT.g, "CSE 2020") | {"CSE 2020"}) & planned
    extra = set(r["invalidated"]) - ripple
    assert ripple <= set(r["invalidated"])
    assert all(CAT.courses[c].min_standing_units for c in extra)  # only standing-gated courses beyond the DAG ripple
    check_valid(r["plan"], alex)
    before = {c: t.term_label for t in plan.terms for c in t.courses}
    after = {c: t.term_label for t in r["plan"].terms for c in t.courses}
    assert all(after[c] == before[c] for c in before if c not in r["invalidated"])


@pytest.mark.req("FR-5", "FR-7")
def test_failing_fall_only_capstone_costs_a_year():
    morgan = STUDENTS["morgan"]
    r = apply_scenario(morgan, make_plan(morgan), ScenarioEvent(event_type="Fail", course_id="CSE 5700", term_label="Fall 2027"))
    assert r["delta_terms"] == 2 and "once a year" in r["explanation"]


@pytest.mark.req("FR-4", "FR-5")
def test_other_scenarios_stay_valid():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    for ev in [
        ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"),
        ScenarioEvent(event_type="Change Unit Load", term_label="Fall 2027", unit_load=12),
        ScenarioEvent(event_type="Pass", course_id="CSE 2020", term_label="Spring 2027"),
        ScenarioEvent(event_type="Withdraw", course_id="MATH 2220", term_label="Spring 2027"),
    ]:
        r = apply_scenario(alex, plan, ev)
        check_valid(r["plan"], alex, cap=plan.unit_cap)
        assert r["explanation"].startswith("Graduation")


@pytest.mark.req("FR-6")
def test_alternatives_differ():
    alts = alternatives(STUDENTS["alex"])
    assert alts["fastest"]["timeline"]["term_count"] <= alts["balanced"]["timeline"]["term_count"]
    peak = {k: max(t.total_units for t in v["plan"].terms) for k, v in alts.items()}
    assert peak["fastest"] > 15 and peak["balanced"] <= 12


@pytest.mark.req("FR-10")
def test_cycle_edge_rejected_and_logged():
    raw = json.loads((DATA / "catalog.json").read_text(encoding="utf8"))
    raw["edges"].append({"from_course": "CSE 5720", "to_course": "CSE 2010"})
    cat = Catalog(raw)
    assert nx.is_directed_acyclic_graph(cat.g)
    assert any("CSE 5720 -> CSE 2010" in d for d in cat.discrepancies)


@pytest.mark.req("FR-10", "NFR-8")
def test_spec_audit_discrepancies_reproduced_from_source():
    text = "\n".join(CAT.discrepancies)
    for needle in ["CSE 4010 units: roadmap says 3, catalog says 4", "CSE 4550 units: roadmap says 4, catalog says 3",
                   "roadmap says 125, catalog says 120", "CSE 4600 prerequisites"]:
        assert needle in text
    assert CAT.courses["CSE 5700"].term_offered == "Fall" and CAT.courses["PHYS 2510"].term_offered == "Spring"


@pytest.mark.req("FR-13", "FR-7")
def test_validator_catches_mycap_style_errors():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    bad = plan.model_copy(deep=True)
    bad.terms[1].courses.append("CSE 5700")  # Fall-only course dropped into Spring, prerequisites unmet
    problems = validate_plan(bad, alex, CAT, cap=99)
    assert any("Fall-only" in p for p in problems) and any("prerequisites" in p for p in problems)


@pytest.mark.req("FR-8")
def test_what_if_does_not_modify_submitted_plan():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    snapshot = plan.model_dump()
    apply_scenario(alex, plan, ScenarioEvent(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027"))
    assert plan.model_dump() == snapshot


@pytest.mark.req("NFR-1")
def test_plan_generation_under_200ms():
    best = min(_timed(make_plan, STUDENTS[sid]) for sid in STUDENTS for _ in range(3))
    worst = max(_timed(make_plan, STUDENTS[sid]) for sid in STUDENTS)
    assert worst < 0.2, f"slowest plan took {worst:.3f}s (best {best:.4f}s)"


def _timed(fn, *args):
    import time
    t0 = time.perf_counter()
    fn(*args)
    return time.perf_counter() - t0
