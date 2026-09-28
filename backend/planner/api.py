import urllib.request

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import guardrail
from .engine import alternatives, apply_scenario, make_plan, timeline, validate_plan
from .graph import load_catalog, load_students
from .models import UNIT_LOAD_RANGE, Plan, ScenarioEvent

app = FastAPI(title="Adaptive Degree Pathway Planner (mock)")


class PlanRequest(BaseModel):
    student_id: str
    unit_cap: int | None = Field(None, ge=UNIT_LOAD_RANGE[0], le=UNIT_LOAD_RANGE[1])


class ScenarioRequest(BaseModel):
    plan: Plan
    event: ScenarioEvent


class ValidateRequest(BaseModel):
    plan: Plan


class QueryRequest(BaseModel):
    text: str
    plan: Plan


def student(sid: str):
    s = load_students().get(sid)
    if not s:
        raise HTTPException(404, f"unknown student {sid}")
    return s


@app.get("/health")
def health():
    """Whether the optional LLM parser is reachable; without it plain-language questions are escalated."""
    try:
        with urllib.request.urlopen(f"{guardrail.OLLAMA_URL}/models", timeout=1) as r:
            ollama = r.status == 200
    except OSError:
        ollama = False
    return {"engine": True, "ollama": ollama, "model": guardrail.OLLAMA_MODEL, "unit_load_range": UNIT_LOAD_RANGE}


@app.get("/catalog")
def catalog():
    cat = load_catalog()
    return {
        "courses": list(cat.courses.values()),
        "edges": [d["edge"] for _, _, d in cat.g.edges(data=True)],
        "priority": cat.priority,
        "discrepancies": cat.discrepancies,
    }


@app.get("/students")
def students():
    return list(load_students().values())


@app.post("/plan")
def plan(req: PlanRequest):
    s = student(req.student_id)
    try:
        p = make_plan(s, req.unit_cap)
        alts = alternatives(s)
    except ValueError as e:  # SRS FR-13: report unplaceable courses instead of a pathway
        raise HTTPException(422, str(e)) from e
    return {"plan": p, "timeline": timeline(p), "alternatives": alts}


@app.post("/scenario")
def scenario(req: ScenarioRequest):
    try:
        return apply_scenario(student(req.plan.student_id), req.plan, req.event)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/validate")
def validate(req: ValidateRequest):
    """SRS FR-14: check any pathway (engine-made, edited, or a roadmap) against catalog rules."""
    return {"problems": validate_plan(req.plan, student(req.plan.student_id))}


@app.post("/query")
def query(req: QueryRequest):
    decision = guardrail.classify(req.text, req.plan)
    if decision["outcome"] == "escalated":
        return {"guardrail": decision, "result": None}
    try:
        result = apply_scenario(student(req.plan.student_id), req.plan, ScenarioEvent(**decision["parsed_event"]))
    except ValueError as e:
        decision.update(outcome="escalated", reason=f"engine rejected event: {e}")
        guardrail.audit.info("guardrail_decision", student_id=req.plan.student_id, **decision)
        return {"guardrail": decision, "result": None}
    return {"guardrail": decision, "result": result}


@app.get("/audit")
def audit(limit: int = 50):
    return guardrail.read_audit(limit)
