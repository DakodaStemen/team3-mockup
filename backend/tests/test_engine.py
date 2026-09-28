import json

import networkx as nx
import pytest

from planner.engine import alternatives, apply_scenario, make_plan, offered, timeline
from planner.graph import DATA, Catalog, load_catalog, load_students
from planner.models import ScenarioEvent

CAT = load_catalog()
STUDENTS = load_students()


def check_valid(plan, profile, cap=None):
    seen = set(profile.completed_courses) | set(profile.in_progress_courses) | set(plan.credited)
    for t in plan.terms:
        for c in t.courses:
            assert offered(c, t.term_label, CAT), f"{c} placed in {t.term_label}"
            assert set(CAT.g.predecessors(c)) - {e.from_course for e in CAT.prereqs(c) if e.condition == "OR"} <= seen
        assert t.total_units <= (cap or plan.unit_cap)
        seen |= set(t.courses)


@pytest.mark.parametrize("sid", STUDENTS)
def test_plans_respect_offerings_prereqs_and_caps(sid):
    check_valid(make_plan(STUDENTS[sid]), STUDENTS[sid])


def test_grade_minimum_forces_retake():
    first = make_plan(STUDENTS["jordan"]).terms[0].courses
    assert "CSE 2010" in first  # D does not meet the C minimum for CSE 2020


def test_fail_capstone_delays_a_year_and_only_touches_descendants():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    term = next(t.term_label for t in plan.terms if "CSE 5700" in t.courses)
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Fail", course_id="CSE 5700", term_label=term))
    assert set(r["invalidated"]) == {"CSE 5700", "CSE 5720"}
    assert r["delta_terms"] == 2 and "delayed by 2" in r["explanation"]
    check_valid(r["plan"], alex)
    # Nothing outside the ripple set moved.
    before = {c: t.term_label for t in plan.terms for c in t.courses}
    after = {c: t.term_label for t in r["plan"].terms for c in t.courses}
    assert all(after[c] == before[c] for c in before if c not in r["invalidated"])


def test_other_scenarios_stay_valid():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    for ev in [
        ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"),
        ScenarioEvent(event_type="Change Unit Load", term_label="Fall 2027", unit_load=12),
        ScenarioEvent(event_type="Pass", course_id="CSE 2130", term_label="Spring 2027"),
        ScenarioEvent(event_type="Withdraw", course_id="CSE 2020", term_label="Spring 2027"),
    ]:
        r = apply_scenario(alex, plan, ev)
        check_valid(r["plan"], alex, cap=15)
        assert r["explanation"].startswith("Graduation")


def test_add_summer_does_not_delay():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"))
    assert r["delta_terms"] <= 0


def test_alternatives_differ():
    alts = alternatives(STUDENTS["alex"])
    assert alts["fastest"]["timeline"]["total_units"] == alts["balanced"]["timeline"]["total_units"]
    # Same graduation here: the Fall-only capstone chain is the binding constraint, not load.
    peak = {k: max(t.total_units for t in v["plan"].terms) for k, v in alts.items()}
    assert peak["fastest"] > 15 and peak["balanced"] <= 12


def test_cycle_edge_rejected_and_logged():
    raw = json.loads((DATA / "catalog.json").read_text())
    raw["edges"].append({"from_course": "CSE 5720", "to_course": "CSE 2010"})
    cat = Catalog(raw)
    assert nx.is_directed_acyclic_graph(cat.g)
    assert any("CSE 5720 -> CSE 2010" in d for d in cat.discrepancies)


def test_discrepancies_flagged_not_resolved():
    assert CAT.courses["CSE 4010"].discrepancy_flag and CAT.courses["CSE 4010"].catalog_units == 4
    assert len(CAT.discrepancies) == 4


def test_timeline_critical_path():
    path = timeline(make_plan(STUDENTS["alex"]))["critical_path"]
    assert path[0] == "CSE 2010" and path[-1] == "CSE 5720"
