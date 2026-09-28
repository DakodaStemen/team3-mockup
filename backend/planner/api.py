import urllib.request
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StringConstraints, ValidationError, field_validator, model_validator

from . import guardrail
from .engine import SUMMER_CAP, alternatives, apply_scenario, make_plan, term_key, timeline, validate_plan
from .graph import load_catalog, load_students
from .models import UNIT_LOAD_RANGE, Plan, ScenarioEvent, TermPlan

app = FastAPI(title="Adaptive Degree Pathway Planner (mock)")
MAX_BODY = 1_000_000  # bytes; a full plan is ~5 KB

# Request bodies are client state, so the API checks their shape before the engine sees them (NFR-03).
# The shared models stay permissive: scripts build roadmap plans with unit_cap=99, and the LLM's raw output
# is checked here too rather than failing inside the parser (which would count toward the circuit breaker).
TermLabel = Annotated[str, StringConstraints(pattern=r"^(Fall|Spring|Summer) (19|20|21)\d{2}$")]
CourseId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9 ./-]{0,23}$")]
Cap = Annotated[int, Field(ge=UNIT_LOAD_RANGE[0], le=UNIT_LOAD_RANGE[1])]


Text = Annotated[str, StringConstraints(max_length=64)]


class TermIn(TermPlan):
    term_label: Text
    courses: list[Text] = Field([], max_length=30)
    total_units: int = Field(0, ge=0, le=100)
    warnings: list[Annotated[str, StringConstraints(max_length=300)]] = Field([], max_length=60)
    unit_cap: Cap | None = None

    @model_validator(mode="after")
    def _summer_cap(self):
        if self.unit_cap and self.term_label.startswith("Summer") and self.unit_cap > SUMMER_CAP:
            raise ValueError(f"{self.term_label} cap {self.unit_cap} is over the {SUMMER_CAP}-unit summer limit")
        return self


class PlanIn(Plan):
    """Size-bounded. Content problems (bad labels, duplicates, unknown courses) are /validate's job to report."""
    student_id: Text
    unit_cap: Cap
    summers: list[Text] = Field([], max_length=20)
    credited: dict[Text, Text] = Field({}, max_length=200)
    terms: list[TermIn] = Field([], max_length=80)  # a 4-unit cap plus a late what-if runs ~60 terms


class TermStrict(TermIn):
    term_label: TermLabel
    courses: list[CourseId] = Field([], max_length=30)


class KnownPlan(PlanIn):
    """A plan the engine will re-plan: well-formed labels, each course once, every course in the catalog."""
    summers: list[Annotated[str, StringConstraints(pattern=r"^Summer (19|20|21)\d{2}$")]] = Field([], max_length=20)
    credited: dict[CourseId, TermLabel] = Field({}, max_length=200)
    terms: list[TermStrict] = Field([], max_length=80)

    @model_validator(mode="after")
    def _consistent(self):
        labels = [t.term_label for t in self.terms]
        if dup := next((lbl for lbl in labels if labels.count(lbl) > 1), None):
            raise ValueError(f"term {dup} appears more than once")
        if labels != sorted(labels, key=term_key):
            raise ValueError("terms must be in chronological order")
        courses = [c for t in self.terms for c in t.courses]
        if dup := next((c for c in courses if courses.count(c) > 1), None):
            raise ValueError(f"course {dup} is planned more than once")
        known = load_catalog().courses
        if unknown := sorted((set(courses) | set(self.credited)) - set(known)):
            raise ValueError(f"not in the catalog: {', '.join(unknown)}")
        return self


class EventIn(ScenarioEvent):
    term_label: TermLabel
    course_id: CourseId | None = None

    @model_validator(mode="after")
    def _complete(self):
        if self.event_type in ("Fail", "Withdraw", "Pass") and not self.course_id:
            raise ValueError(f"{self.event_type} needs a course_id")
        if (self.event_type == "Add Summer") != self.term_label.startswith("Summer"):
            raise ValueError("Add Summer, and only Add Summer, uses a 'Summer YYYY' term_label")
        return self


class PlanRequest(BaseModel):
    student_id: Annotated[str, StringConstraints(max_length=64)]
    unit_cap: Cap | None = None


class ScenarioRequest(BaseModel):
    plan: KnownPlan
    event: EventIn


class ValidateRequest(BaseModel):
    plan: PlanIn


class QueryRequest(BaseModel):
    text: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    plan: KnownPlan

    @field_validator("text")
    @classmethod
    def _printable(cls, v: str) -> str:
        return "".join(ch if ch.isprintable() else " " for ch in v)  # no control characters into the prompt or log


@app.middleware("http")
async def limits_and_headers(request: Request, call_next):
    length = request.headers.get("content-length") or "0"
    if not length.isdigit():
        return JSONResponse({"detail": "invalid Content-Length header"}, status_code=400)
    if int(length) > MAX_BODY:
        return JSONResponse({"detail": f"request body over {MAX_BODY} bytes"}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


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
    profile = student(req.plan.student_id)  # before the LLM: no model call or audit line for an unknown student
    decision = guardrail.classify(req.text, req.plan)
    if decision["outcome"] == "escalated":
        return {"guardrail": decision, "result": None}
    try:
        # The LLM's event passes the same checks as a typed /scenario request before the engine runs it.
        result = apply_scenario(profile, req.plan, EventIn(**decision["parsed_event"]))
    except ValidationError as e:
        decision.update(outcome="escalated", reason=f"parsed event invalid: {e.errors()[0]['msg']}"[:300])
        guardrail.audit.info("guardrail_decision", student_id=req.plan.student_id, **decision)
        return {"guardrail": decision, "result": None}
    except ValueError as e:
        decision.update(outcome="escalated", reason=f"engine rejected event: {e}"[:300])
        guardrail.audit.info("guardrail_decision", student_id=req.plan.student_id, **decision)
        return {"guardrail": decision, "result": None}
    return {"guardrail": decision, "result": result}


@app.get("/audit")
def audit(limit: int = Query(50, ge=1, le=500)):
    return guardrail.read_audit(limit)
