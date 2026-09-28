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


def test_threshold_bands():
    assert classify("q", PLAN, fake(0.95, **FAIL_2020))["outcome"] == "auto_accepted"
    assert classify("q", PLAN, fake(0.70, **FAIL_2020))["outcome"] == "accepted_low_confidence"
    assert classify("q", PLAN, fake(0.40, **FAIL_2020))["outcome"] == "escalated"
    assert classify("q", PLAN, fake(0.99))["outcome"] == "escalated"  # unsupported intent


def test_hallucinated_course_escalated():
    r = classify("q", PLAN, fake(0.99, event_type="Fail", course_id="CSE 9999", term_label="Spring 2027"))
    assert r["outcome"] == "escalated" and "CSE 9999" in r["reason"]


def test_circuit_breaker_opens_after_repeated_failures():
    def down(text, plan):
        raise ConnectionError("ollama down")
    guardrail._breaker.update(fails=0, opened_at=0.0)
    for _ in range(guardrail.BREAKER_FAILS):
        assert classify("q", PLAN, down)["outcome"] == "escalated"
    r = classify("q", PLAN, fake(0.99, **FAIL_2020))  # would succeed, but breaker is open
    assert r["outcome"] == "escalated" and "breaker" in r["reason"]
    guardrail._breaker.update(fails=0, opened_at=0.0)


def test_api_end_to_end():
    c = TestClient(app)
    plan = c.post("/plan", json={"student_id": "alex"}).json()["plan"]
    r = c.post("/scenario", json={"plan": plan, "event": FAIL_2020})
    assert r.status_code == 200 and "CSE 2020" in r.json()["explanation"]
    assert c.post("/scenario", json={"plan": plan, "event": {**FAIL_2020, "course_id": "CSE 9999"}}).status_code == 400
    assert c.get("/audit").json()[0]["event"] == "guardrail_decision"


def test_calibration_math():
    import numpy as np
    from scripts.calibrate import evaluate
    rng = np.random.default_rng(0)
    raw = rng.uniform(0.5, 1.0, 60)  # overconfident model: real accuracy well below stated confidence
    y = (rng.uniform(size=60) < raw - 0.3).astype(int)
    r = evaluate(raw, y)
    assert r["brier_calibrated"] < r["brier_raw"] and len(r["table"]["x"]) == 21


def test_labeled_queries_match_current_plan():
    """data/queries.json is labeled against Alex's plan; if the engine changes the plan, relabel."""
    import json
    from pathlib import Path
    from planner.guardrail import validate
    items = json.loads((Path(__file__).parent.parent / "data" / "queries.json").read_text(encoding="utf8"))
    bad = [i["query"] for i in items if i["expected"] and validate(ScenarioEvent(**i["expected"]), PLAN)]
    assert bad == []
