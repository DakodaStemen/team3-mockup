"""Hostile or malformed input must get a clear 4xx, never a 500 or a leaked internal (NFR-03)."""
import copy

import pytest
from fastapi.testclient import TestClient

from planner.api import app

client = TestClient(app, raise_server_exceptions=False)
PLAN = client.post("/plan", json={"student_id": "alex"}).json()["plan"]
FAIL = {"event_type": "Fail", "course_id": "CSE 2020", "term_label": "Spring 2027"}


def plan(**changes):
    p = copy.deepcopy(PLAN)
    p.update(changes)
    return p


@pytest.mark.req("NFR-03")
@pytest.mark.parametrize("label", ["Summer abc", "Summer", "Summer 99999999999", "Winter 2027", "Fall"])
def test_malformed_term_labels_rejected_cleanly(label):
    r = client.post("/scenario", json={"plan": plan(), "event": {"event_type": "Add Summer", "term_label": label}})
    assert r.status_code == 422
    assert "invalid literal" not in r.text and "unpack" not in r.text


@pytest.mark.req("NFR-03")
def test_plan_bodies_are_bounded_and_consistent():
    first = PLAN["terms"][0]
    bad = {
        "unit cap": plan(unit_cap=0),
        "negative cap": plan(unit_cap=-5),
        "duplicate course": plan(terms=[{**first, "courses": [*first["courses"], "CSE 2010"]}, *PLAN["terms"][1:]]),
        "duplicate term": plan(terms=[first, first, *PLAN["terms"][1:]]),
        "bad term label": plan(terms=[{**first, "term_label": "Fall"}, *PLAN["terms"][1:]]),
        "too many terms": plan(terms=[{"term_label": f"Fall {2000 + i}", "courses": []} for i in range(81)]),
        "huge course id": plan(terms=[{**first, "courses": ["X" * 10_000]}, *PLAN["terms"][1:]]),
        "junk summer": plan(summers=["junk"]),
        "credited junk term": plan(credited={"CSE 2010": "whenever"}),
        "out of order": plan(terms=list(reversed(PLAN["terms"]))),
    }
    for name, p in bad.items():
        assert client.post("/scenario", json={"plan": p, "event": FAIL}).status_code == 422, name
    # /validate only bounds size and the cap; it reports content problems instead of refusing the plan
    for name in ["unit cap", "negative cap", "too many terms", "huge course id"]:
        assert client.post("/validate", json={"plan": bad[name]}).status_code == 422, name
    for name in ["duplicate course", "duplicate term", "bad term label", "junk summer", "credited junk term", "out of order"]:
        assert client.post("/validate", json={"plan": bad[name]}).status_code == 200, name


@pytest.mark.req("NFR-03")
def test_unknown_courses_rejected_before_the_engine():
    first = PLAN["terms"][0]
    for p in [plan(terms=[{**first, "courses": [*first["courses"], "FOO 1"]}, *PLAN["terms"][1:]]),
              plan(credited={"FOO 1": "Fall 2026"})]:
        for ev in [FAIL, {"event_type": "Change Unit Load", "term_label": "Fall 2026", "unit_load": 12}]:
            r = client.post("/scenario", json={"plan": p, "event": ev})
            assert r.status_code == 422 and "FOO 1" in r.text
    # /validate still reports a hand-edited plan's unknown course as a problem rather than refusing it
    r = client.post("/validate", json={"plan": plan(terms=[{**first, "courses": ["FOO 1"]}])})
    assert r.status_code == 200 and any("FOO 1 is not in the catalog" in p for p in r.json()["problems"])


@pytest.mark.req("NFR-03")
def test_course_event_needs_a_course():
    r = client.post("/scenario", json={"plan": plan(), "event": {"event_type": "Fail", "term_label": "Spring 2027"}})
    assert r.status_code == 422 and "course_id" in r.text


@pytest.mark.req("NFR-03")
def test_basic_security_headers():
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["X-Frame-Options"] == "DENY"


@pytest.mark.req("NFR-03")
def test_api_accepts_every_plan_it_produces():
    """The strict input models must never reject the engine's own output, or a user gets stuck mid-session."""
    from planner.api import EventIn, KnownPlan
    from planner.engine import apply_scenario, make_plan
    from planner.graph import load_students

    for profile in load_students().values():
        for cap in (8, 12, 21):
            base = make_plan(profile, cap)
            KnownPlan.model_validate(base.model_dump())
            t = base.terms[len(base.terms) // 2]
            events = [dict(event_type=k, course_id=t.courses[0], term_label=t.term_label) for k in ("Fail", "Pass")]
            events += [dict(event_type="Change Unit Load", term_label=t.term_label, unit_load=4),
                       dict(event_type="Add Summer", term_label=f"Summer {int(t.term_label.split()[1]) + 1}")]
            for ev in events:
                try:
                    out = apply_scenario(profile, base, EventIn(**ev))["plan"]
                except ValueError:  # e.g. a cap too small to finish: refused with a message, not a plan
                    continue
                KnownPlan.model_validate(out.model_dump())


@pytest.mark.req("NFR-03", "FR-06")
@pytest.mark.parametrize("term,cap", [(0, 40), (0, 2), ("summer", 15), ("winter", 5)])
def test_term_caps_are_bounded(term, cap):
    p = copy.deepcopy(PLAN)
    if term == "summer":
        p["summers"] = ["Summer 2027"]
        p["terms"].insert(2, {"term_label": "Summer 2027", "courses": [], "unit_cap": cap})
    elif term == "winter":
        p["winters"] = ["Winter 2027"]
        p["terms"].insert(1, {"term_label": "Winter 2027", "courses": [], "unit_cap": cap})
    else:
        p["terms"][term]["unit_cap"] = cap
    assert client.post("/validate", json={"plan": p}).status_code == 422
    assert client.post("/scenario", json={"plan": p, "event": FAIL}).status_code == 422


@pytest.mark.req("FR-11", "NFR-03")
def test_term_caps_round_trip_through_the_api():
    ev = {"event_type": "Change Unit Load", "term_label": "Fall 2027", "unit_load": 12}
    out = client.post("/scenario", json={"plan": PLAN, "event": ev}).json()["plan"]
    assert [t["unit_cap"] for t in out["terms"][:2]] == [16, 16] and out["terms"][2]["unit_cap"] == 12
    again = client.post("/scenario", json={"plan": out, "event": FAIL})
    assert again.status_code == 200 and again.json()["plan"]["terms"][0]["unit_cap"] == 16
    assert client.post("/validate", json={"plan": again.json()["plan"]}).json()["problems"] == []


@pytest.mark.req("NFR-03")
def test_malformed_content_length_is_a_400_not_a_500():
    r = TestClient(app).post("/plan", content=b"{}", headers={"content-length": "abc", "content-type": "application/json"})
    assert r.status_code == 400
