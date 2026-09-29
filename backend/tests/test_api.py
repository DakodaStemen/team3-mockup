import pytest
from fastapi.testclient import TestClient

from planner.api import app

FAIL_2020 = dict(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027")


@pytest.mark.req("FR-10")
def test_api_end_to_end():
    c = TestClient(app)
    plan = c.post("/plan", json={"student_id": "alex"}).json()["plan"]
    r = c.post("/scenario", json={"plan": plan, "event": FAIL_2020})
    assert r.status_code == 200 and "CSE 2020" in r.json()["explanation"]
    assert c.post("/scenario", json={"plan": plan, "event": {**FAIL_2020, "course_id": "CSE 9999"}}).status_code == 400


@pytest.mark.req("NFR-03")
def test_api_rejects_invalid_requests():
    c = TestClient(app)
    assert c.post("/plan", json={"student_id": "nobody"}).status_code == 404
    plan = c.post("/plan", json={"student_id": "alex"}).json()["plan"]
    wrong_term = {**FAIL_2020, "term_label": "Fall 2026"}  # CSE 2020 is not planned in Fall 2026
    assert c.post("/scenario", json={"plan": plan, "event": wrong_term}).status_code == 400
    assert c.post("/scenario", json={"plan": plan, "event": {**FAIL_2020, "term_label": "Fall 2099"}}).status_code == 400


@pytest.mark.req("FR-14")
def test_validate_endpoint_flags_offering_violation():
    c = TestClient(app)
    plan = c.post("/plan", json={"student_id": "alex"}).json()["plan"]
    assert c.post("/validate", json={"plan": plan}).json()["problems"] == []
    spring = next(t for t in plan["terms"] if t["term_label"].startswith("Spring"))
    spring["courses"].append("CSE 5700")  # Fall-only
    problems = c.post("/validate", json={"plan": plan}).json()["problems"]
    assert any("CSE 5700 is Fall-only" in p for p in problems)


@pytest.mark.req("FR-13")
def test_unschedulable_plan_reports_courses_instead_of_pathway(monkeypatch):
    from planner import api

    def impossible(*args, **kwargs):
        raise ValueError("Cannot schedule ['CSE 5720']: prerequisites or offerings never satisfied.")
    monkeypatch.setattr(api, "make_plan", impossible)
    r = TestClient(app).post("/plan", json={"student_id": "alex"})
    assert r.status_code == 422 and "CSE 5720" in r.json()["detail"]


@pytest.mark.req("NFR-03", "FR-11")
@pytest.mark.parametrize("units", [0, 2, 22, 40])
def test_scenario_api_rejects_out_of_range_unit_load(units):
    c = TestClient(app)
    plan = c.post("/plan", json={"student_id": "alex"}).json()["plan"]
    ev = {"event_type": "Change Unit Load", "term_label": plan["terms"][0]["term_label"], "unit_load": units}
    r = c.post("/scenario", json={"plan": plan, "event": ev})
    assert r.status_code == 400 and "between 3 and 21" in r.json()["detail"]
    assert c.post("/scenario", json={"plan": plan, "event": {**ev, "unit_load": 21}}).status_code == 200


@pytest.mark.req("NFR-03", "FR-06")
def test_plan_api_rejects_bad_unit_caps():
    c = TestClient(app)
    assert c.post("/plan", json={"student_id": "alex", "unit_cap": 40}).status_code == 422
    r = c.post("/plan", json={"student_id": "alex", "unit_cap": 3})
    assert r.status_code == 422 and "cap of at least 4" in r.json()["detail"]
    assert c.post("/plan", json={"student_id": "alex", "unit_cap": 12}).status_code == 200


@pytest.mark.req("NFR-03")
def test_health_reports_the_unit_load_range():
    r = TestClient(app).get("/health").json()
    assert r == {"engine": True, "unit_load_range": [3, 21]}
