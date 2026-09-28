import json
import time

import networkx as nx
import pytest

from planner.engine import alternatives, apply_scenario, grade_ok, make_plan, timeline, validate_plan
from planner.graph import DATA, Catalog, load_catalog, load_students
from planner.models import ScenarioEvent

CAT = load_catalog()
STUDENTS = load_students()


def check_valid(plan, profile, cap=None):
    assert validate_plan(plan, profile, CAT, cap) == []


@pytest.mark.req("FR-03", "FR-05", "FR-06", "FR-08", "NFR-07")
@pytest.mark.parametrize("sid", STUDENTS)
def test_plans_valid_and_complete(sid):
    check_valid(make_plan(STUDENTS[sid]), STUDENTS[sid])


@pytest.mark.req("FR-05")
def test_freshman_plan_meets_catalog_total():
    assert timeline(make_plan(STUDENTS["alex"]))["total_units"] == CAT.program["catalog_total_units"]


@pytest.mark.req("FR-02", "DR-04")
def test_grades():
    assert grade_ok("C", "C") and grade_ok("C", "C-") and not grade_ok("C-", "C")
    assert not grade_ok("W", "D-") and not grade_ok("F", "D-")


@pytest.mark.req("FR-01", "FR-02")
def test_grade_minimum_forces_retake():
    first = make_plan(STUDENTS["jordan"]).terms[0].courses
    assert "CSE 2010" in first  # D is below the C that CSE 2020 requires


@pytest.mark.req("FR-08")
def test_spring_only_waits():
    plan = make_plan(STUDENTS["sam"])  # starts in Fall, still needs PHYS 2510
    assert "PHYS 2510" not in plan.terms[0].courses
    assert "PHYS 2510" in plan.terms[1].courses and "PHYS 2510L" in plan.terms[1].courses


@pytest.mark.req("FR-04", "FR-10", "NFR-11")
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


@pytest.mark.req("FR-10", "FR-12")
def test_failing_fall_only_capstone_costs_a_year():
    morgan = STUDENTS["morgan"]
    r = apply_scenario(morgan, make_plan(morgan), ScenarioEvent(event_type="Fail", course_id="CSE 5700", term_label="Fall 2027"))
    assert r["delta_terms"] == 2 and "once a year" in r["explanation"]


@pytest.mark.req("FR-09", "FR-11", "NFR-07")
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


@pytest.mark.req("FR-17")
def test_alternatives_differ():
    alts = alternatives(STUDENTS["alex"])
    assert alts["fastest"]["timeline"]["term_count"] <= alts["balanced"]["timeline"]["term_count"]
    peak = {k: max(t.total_units for t in v["plan"].terms) for k, v in alts.items()}
    assert peak["fastest"] > 15 and peak["balanced"] <= 12


@pytest.mark.req("DR-03", "FR-20")
def test_cycle_edge_rejected_and_logged():
    raw = json.loads((DATA / "catalog.json").read_text(encoding="utf8"))
    raw["edges"].append({"from_course": "CSE 5720", "to_course": "CSE 2010"})
    cat = Catalog(raw)
    assert nx.is_directed_acyclic_graph(cat.g)
    assert any("CSE 5720 -> CSE 2010" in d for d in cat.discrepancies)


@pytest.mark.req("FR-20", "DR-08")
def test_spec_audit_discrepancies_reproduced_from_source():
    text = "\n".join(CAT.discrepancies)
    for needle in ["CSE 4010 units: roadmap says 3, catalog says 4", "CSE 4550 units: roadmap says 4, catalog says 3",
                   "roadmap says 125, catalog says 120", "CSE 4600 prerequisites"]:
        assert needle in text
    assert CAT.courses["CSE 5700"].term_offered == "Fall" and CAT.courses["PHYS 2510"].term_offered == "Spring"


@pytest.mark.req("FR-14")
def test_validator_catches_mycap_style_errors():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    bad = plan.model_copy(deep=True)
    bad.terms[1].courses.append("CSE 5700")  # Fall-only course dropped into Spring, prerequisites unmet
    problems = validate_plan(bad, alex, CAT, cap=99)
    assert any("Fall-only" in p for p in problems) and any("prerequisites" in p for p in problems)


@pytest.mark.req("FR-15")
def test_what_if_does_not_modify_submitted_plan():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    snapshot = plan.model_dump()
    apply_scenario(alex, plan, ScenarioEvent(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027"))
    assert plan.model_dump() == snapshot


@pytest.mark.req("NFR-04")
def test_generation_and_recalculation_within_2s():
    """SRS NFR-04 (provisional 2 s). Best of 3 per student, so a noisy CI runner can't fail it."""
    def best(fn, *args):
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            fn(*args)
            times.append(time.perf_counter() - t0)
        return min(times)

    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    fail = ScenarioEvent(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027")
    assert max(best(make_plan, STUDENTS[sid]) for sid in STUDENTS) < 2.0
    assert best(apply_scenario, alex, plan, fail) < 2.0


@pytest.mark.req("NFR-08")
def test_identical_inputs_give_identical_pathway():
    for sid in STUDENTS:
        assert make_plan(STUDENTS[sid]).model_dump() == make_plan(STUDENTS[sid]).model_dump()


@pytest.mark.req("FR-07")
def test_no_summer_unless_selected():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    assert not any(t.term_label.startswith("Summer") for t in plan.terms)
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"))
    summer = [t for t in r["plan"].terms if t.term_label.startswith("Summer")]
    assert [t.term_label for t in summer] == ["Summer 2027"]
    assert all(CAT.courses[c].term_offered == "Both" for t in summer for c in t.courses)


@pytest.mark.req("DR-01")
def test_every_prerequisite_endpoint_is_a_catalog_course():
    assert all(u in CAT.courses and v in CAT.courses for u, v in CAT.g.edges)
    assert all(g_course in CAT.courses for g in CAT.program["groups"] for g_course in g.get("all", []) + g.get("from", []))
