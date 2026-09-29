"""CH-03: opt-in winter intersessions (FR-22) and labs taken in the same term as their lecture (FR-23)."""
import pytest
from fastapi.testclient import TestClient

from planner.api import app
from planner.engine import WINTER_CAP, apply_scenario, make_plan, recover, term_key, validate_plan
from planner.graph import load_catalog, load_students
from planner.models import ScenarioEvent

CAT = load_catalog()
STUDENTS = load_students()


def _labs_with_lectures(plan):
    where = {c: t.term_label for t in plan.terms for c in t.courses}
    return [(lab, where[lec], where[lab]) for lec, lab in CAT.lab_for.items() if lec in where and lab in where]


@pytest.mark.req("FR-22")
def test_add_winter_inserts_a_january_term_with_a_small_cap():
    alex = STUDENTS["alex"]
    base = make_plan(alex)
    assert not any(t.term_label.startswith("Winter") for t in base.terms)  # never planned unless opted in
    r = apply_scenario(alex, base, ScenarioEvent(event_type="Add Winter", term_label="Winter 2028"))
    labels = [t.term_label for t in r["plan"].terms]
    assert labels.index("Fall 2027") + 1 == labels.index("Winter 2028") == labels.index("Spring 2028") - 1
    assert labels == sorted(labels, key=term_key)
    winter = next(t for t in r["plan"].terms if t.term_label == "Winter 2028")
    assert winter.unit_cap <= WINTER_CAP and winter.total_units <= WINTER_CAP
    assert all(CAT.courses[c].term_offered == "Both" for c in winter.courses)
    assert all(any("winter offerings are not published" in w and c in w for w in winter.warnings) for c in winter.courses)
    assert r["plan"].winters == ["Winter 2028"]
    assert validate_plan(r["plan"], alex, CAT) == []
    assert r["delta_terms"] <= 0


@pytest.mark.req("FR-22")
def test_winter_and_summer_together_can_catch_a_student_up():
    riley = STUDENTS["riley"]  # part-time: extra terms matter most
    plan = make_plan(riley)
    first_fall = next(t.term_label for t in plan.terms if t.term_label.startswith("Fall"))
    year = int(first_fall.split()[1])
    r = apply_scenario(riley, plan, ScenarioEvent(event_type="Add Winter", term_label=f"Winter {year + 1}"))
    r = apply_scenario(riley, r["plan"], ScenarioEvent(event_type="Add Summer", term_label=f"Summer {year + 1}"))
    assert validate_plan(r["plan"], riley, CAT) == []
    assert term_key(r["plan"].terms[-1].term_label) <= term_key(plan.terms[-1].term_label)


@pytest.mark.req("FR-22")
@pytest.mark.parametrize("event,label,status", [("Add Winter", "Winter 2028", 200), ("Add Winter", "Summer 2028", 422),
                                                ("Add Summer", "Winter 2028", 422), ("Add Winter", "Winter 2028x", 422)])
def test_api_accepts_only_matching_intersession_labels(event, label, status):
    client = TestClient(app, raise_server_exceptions=False)
    plan = client.post("/plan", json={"student_id": "alex"}).json()["plan"]
    r = client.post("/scenario", json={"plan": plan, "event": {"event_type": event, "term_label": label}})
    assert r.status_code == status, r.text


@pytest.mark.req("FR-23")
@pytest.mark.parametrize("sid", STUDENTS)
def test_every_lab_shares_its_lecture_term(sid):
    pairs = _labs_with_lectures(make_plan(STUDENTS[sid]))
    assert all(lec_term == lab_term for _, lec_term, lab_term in pairs), pairs


@pytest.mark.req("FR-23")
@pytest.mark.parametrize("course", ["PHYS 2500", "PHYS 2500L"])
def test_failing_a_lecture_or_its_lab_moves_both(course):
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    term = next(t.term_label for t in plan.terms if course in t.courses)
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Fail", course_id=course, term_label=term))
    assert all(a == b for _, a, b in _labs_with_lectures(r["plan"])), _labs_with_lectures(r["plan"])
    assert validate_plan(r["plan"], alex, CAT) == []


@pytest.mark.req("FR-23", "FR-14")
def test_validator_flags_a_lab_split_from_its_lecture():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    src = next(t for t in plan.terms if "PHYS 2500L" in t.courses)
    dst = plan.terms[plan.terms.index(src) + 2]  # same season a year later, so offerings still hold
    src.courses.remove("PHYS 2500L")
    dst.courses.append("PHYS 2500L")
    assert any("PHYS 2500L must be taken in the same term as PHYS 2500" in p for p in validate_plan(plan, alex, CAT, cap=21))


@pytest.mark.req("FR-24")
@pytest.mark.parametrize("course,term", [("CSE 2020", "Spring 2027"), ("MATH 2210", "Fall 2026")])
def test_recovery_wins_back_a_failed_course_with_intersessions(course, term):
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Fail", course_id=course, term_label=term))
    assert r["delta_terms"] > 0
    rec = recover(alex, r["plan"], plan.terms[-1].term_label, term, CAT)
    assert rec and rec["adds"] and "back on time" in rec["explanation"]
    assert term_key(rec["plan"].terms[-1].term_label) <= term_key(plan.terms[-1].term_label)
    assert all(term_key(a) > term_key(term) for a in rec["adds"])  # only terms after the setback
    assert validate_plan(rec["plan"], alex, CAT) == []


@pytest.mark.req("FR-24")
def test_recovery_returns_nothing_when_no_intersession_helps():
    morgan = STUDENTS["morgan"]  # senior: a Fall-only capstone chain, which no intersession can host
    plan = make_plan(morgan)
    assert recover(morgan, plan, plan.terms[0].term_label, plan.terms[0].term_label, CAT) is None


@pytest.mark.req("FR-24", "FR-17")
def test_scenario_api_offers_recovery_only_after_a_delay():
    client = TestClient(app, raise_server_exceptions=False)
    plan = client.post("/plan", json={"student_id": "alex"}).json()["plan"]
    late = client.post("/scenario", json={"plan": plan, "event": {"event_type": "Fail", "course_id": "CSE 2020", "term_label": "Spring 2027"}}).json()
    assert late["recovery"]["adds"] == ["Summer 2027"]
    fine = client.post("/scenario", json={"plan": plan, "event": {"event_type": "Add Winter", "term_label": "Winter 2028"}}).json()
    assert "recovery" not in fine
    riley = client.post("/plan", json={"student_id": "riley"}).json()
    alt = riley["alternatives"]["with summer & winter"]
    assert alt["adds"] and term_key(alt["timeline"]["graduation_term"]) < term_key(riley["timeline"]["graduation_term"])


@pytest.mark.req("FR-22")
def test_short_terms_are_planned_lighter_than_their_published_maximums():
    """Registrar maxima: summer 14, winter 4, fall/spring 18. Summer and winter are short, so summer plans one session (7)."""
    from planner.engine import REGULAR_MAX, SUMMER_CAP, SUMMER_MAX, off_term_cap, off_term_max
    assert (SUMMER_CAP, SUMMER_MAX, WINTER_CAP, REGULAR_MAX) == (7, 14, 4, 18)
    assert off_term_cap("Summer 2027") < off_term_max("Summer 2027") and off_term_cap("Winter 2028") == off_term_max("Winter 2028") == 4
    alex = STUDENTS["alex"]
    plan = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"))["plan"]
    summer = next(t for t in plan.terms if t.term_label == "Summer 2027")
    assert summer.total_units <= SUMMER_CAP
    # A hand-made plan may hold more than the engine plans, up to the published maximum, and no further.
    summer.unit_cap, summer.total_units = None, 10
    assert not any("exceeds cap" in p for p in validate_plan(plan, alex, CAT, complete=False))
    summer.total_units = 15
    assert any("exceeds cap 14" in p for p in validate_plan(plan, alex, CAT, complete=False))


@pytest.mark.req("FR-09")
def test_a_load_above_the_registrars_regular_maximum_is_flagged_as_an_overload():
    alex = STUDENTS["alex"]
    assert not any("overload" in w for t in make_plan(alex, 18).terms for w in t.warnings)
    assert all(any("approved overload" in w for w in t.warnings) for t in make_plan(alex, 21).terms)
