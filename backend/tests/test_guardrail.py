import pytest
from fastapi.testclient import TestClient

from planner import guardrail
from planner.api import app
from planner.engine import make_plan
from planner.graph import load_students
from planner.guardrail import ScenarioQueryClassification, classify
from planner.models import ScenarioEvent

PLAN = make_plan(load_students()["alex"])


def fake(conf, **event):
    ev = ScenarioEvent(**event) if event else None
    return lambda text, plan: ScenarioQueryClassification(intent="scenario" if ev else "unsupported", event=ev, confidence=conf)


FAIL_2020 = dict(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027")


@pytest.fixture(autouse=True)
def raw_confidence(monkeypatch, tmp_path):
    """Tests reason about raw confidence; ignore any local calibration.json and reset the breaker."""
    monkeypatch.setattr(guardrail, "CALIBRATION", tmp_path / "none.json")
    guardrail._breaker.update(fails=0, opened_at=0.0)


@pytest.mark.req("FR-19")
def test_threshold_bands():
    assert classify("q", PLAN, fake(0.95, **FAIL_2020))["outcome"] == "auto_accepted"
    assert classify("q", PLAN, fake(0.70, **FAIL_2020))["outcome"] == "accepted_low_confidence"
    assert classify("q", PLAN, fake(0.40, **FAIL_2020))["outcome"] == "escalated"
    assert classify("q", PLAN, fake(0.99))["outcome"] == "escalated"  # unsupported intent


@pytest.mark.req("FR-19")
def test_hallucinated_course_escalated():
    r = classify("q", PLAN, fake(0.99, event_type="Fail", course_id="CSE 9999", term_label="Spring 2027"))
    assert r["outcome"] == "escalated" and "CSE 9999" in r["reason"]


@pytest.mark.req("NFR-12")
def test_circuit_breaker_opens_after_repeated_failures():
    def down(text, plan):
        raise ConnectionError("ollama down")
    for _ in range(guardrail.BREAKER_FAILS):
        assert classify("q", PLAN, down)["outcome"] == "escalated"
    r = classify("q", PLAN, fake(0.99, **FAIL_2020))  # would succeed, but breaker is open
    assert r["outcome"] == "escalated" and "breaker" in r["reason"]


@pytest.mark.req("FR-10", "FR-21")
def test_api_end_to_end():
    classify("what if I fail CSE 2020", PLAN, fake(0.95, **FAIL_2020))  # ensure an audit line exists, independent of test order
    c = TestClient(app)
    plan = c.post("/plan", json={"student_id": "alex"}).json()["plan"]
    r = c.post("/scenario", json={"plan": plan, "event": FAIL_2020})
    assert r.status_code == 200 and "CSE 2020" in r.json()["explanation"]
    assert c.post("/scenario", json={"plan": plan, "event": {**FAIL_2020, "course_id": "CSE 9999"}}).status_code == 400
    assert c.get("/audit").json()[0]["event"] == "guardrail_decision"


@pytest.mark.req("NFR-13")
def test_calibration_math():
    import numpy as np

    from scripts.calibrate import evaluate
    rng = np.random.default_rng(0)
    raw = rng.uniform(0.5, 1.0, 60)  # overconfident model: real accuracy well below stated confidence
    y = (rng.uniform(size=60) < raw - 0.3).astype(int)
    r = evaluate(raw, y)
    assert r["brier_calibrated"] < r["brier_raw"] and len(r["table"]["x"]) == 21


@pytest.mark.req("FR-19")
def test_labeled_queries_match_current_plan():
    """data/queries.json is labeled against Alex's plan; if the engine changes the plan, relabel."""
    import json
    from pathlib import Path

    from planner.guardrail import validate
    items = json.loads((Path(__file__).parent.parent / "data" / "queries.json").read_text(encoding="utf8"))
    bad = [i["query"] for i in items if i["expected"] and validate(ScenarioEvent(**i["expected"]), PLAN)]
    assert bad == []


@pytest.mark.req("FR-19")
@pytest.mark.parametrize("conf,outcome", [(0.59, "escalated"), (0.60, "accepted_low_confidence"),
                                          (0.89, "accepted_low_confidence"), (0.90, "auto_accepted")])
def test_threshold_boundaries(conf, outcome):
    assert classify("q", PLAN, fake(conf, **FAIL_2020))["outcome"] == outcome


@pytest.mark.req("FR-19", "NFR-03")
@pytest.mark.parametrize("units,ok", [(2, False), (3, True), (21, True), (22, False)])
def test_unit_load_bounds(units, ok):
    from planner.guardrail import validate
    ev = ScenarioEvent(event_type="Change Unit Load", term_label=PLAN.terms[0].term_label, unit_load=units)
    assert (validate(ev, PLAN) is None) == ok


@pytest.mark.req("FR-21")
def test_every_decision_writes_a_complete_audit_line():
    classify("what if I fail CSE 2020", PLAN, fake(0.7, **FAIL_2020))
    line = guardrail.read_audit(1)[0]
    for key in ("timestamp", "student_id", "input", "parsed_event", "raw_confidence", "confidence", "thresholds", "outcome", "reason"):
        assert key in line
    assert line["outcome"] == "accepted_low_confidence" and line["raw_confidence"] == 0.7


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
