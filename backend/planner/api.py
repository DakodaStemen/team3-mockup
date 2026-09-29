import secrets
from collections import OrderedDict
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, StringConstraints, model_validator

from .engine import alternatives, apply_scenario, course_risk, make_plan, moves, off_term_max, recover, term_key, terms_later, timeline, validate_plan
from .graph import DATA, load_catalog, load_students
from .models import UNIT_LOAD_RANGE, Plan, ScenarioEvent, StudentProfile, TermPlan
from .transcript import extract_text
from .transcript import parse as parse_transcript

app = FastAPI(title="Adaptive Degree Pathway Planner (mock)")
MAX_BODY = 1_000_000  # bytes; a full plan is ~5 KB

# Request bodies are client state, so the API checks their shape before the engine sees them (NFR-03).
# The shared models stay permissive: scripts build roadmap plans with unit_cap=99.
TermLabel = Annotated[str, StringConstraints(pattern=r"^(Fall|Winter|Spring|Summer) (19|20|21)\d{2}$")]
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
    def _off_term_cap(self):
        if self.unit_cap and (off := off_term_max(self.term_label)) and self.unit_cap > off:
            season = self.term_label.split()[0].lower()
            raise ValueError(f"{self.term_label} cap {self.unit_cap} is over the {off}-unit {season} limit")
        return self


class PlanIn(Plan):
    """Size-bounded. Content problems (bad labels, duplicates, unknown courses) are /validate's job to report."""
    student_id: Text
    unit_cap: Cap
    summers: list[Text] = Field([], max_length=20)
    winters: list[Text] = Field([], max_length=20)
    credited: dict[Text, Text] = Field({}, max_length=200)
    terms: list[TermIn] = Field([], max_length=80)  # a 4-unit cap plus a late what-if runs ~60 terms


class TermStrict(TermIn):
    term_label: TermLabel
    courses: list[CourseId] = Field([], max_length=30)


class KnownPlan(PlanIn):
    """A plan the engine will re-plan: well-formed labels, each course once, every course in the catalog."""
    summers: list[Annotated[str, StringConstraints(pattern=r"^Summer (19|20|21)\d{2}$")]] = Field([], max_length=20)
    winters: list[Annotated[str, StringConstraints(pattern=r"^Winter (19|20|21)\d{2}$")]] = Field([], max_length=20)
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
        for season in ("Summer", "Winter"):
            if (self.event_type == f"Add {season}") != self.term_label.startswith(season):
                raise ValueError(f"Add {season}, and only Add {season}, uses a '{season} YYYY' term_label")
        return self


class PlanRequest(BaseModel):
    student_id: Annotated[str, StringConstraints(max_length=64)]
    unit_cap: Cap | None = None


class ScenarioRequest(BaseModel):
    plan: KnownPlan
    event: EventIn


class ValidateRequest(BaseModel):
    plan: PlanIn


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


# Uploaded transcripts live only in this process's memory, newest 200, never on disk (FR-26).
UPLOADS: OrderedDict[str, StudentProfile] = OrderedDict()
MAX_UPLOADS = 200


def student(sid: str):
    s = load_students().get(sid) or UPLOADS.get(sid)
    if not s:
        raise HTTPException(404, f"unknown student {sid}")
    return s


@app.get("/health")
def health():
    return {"engine": True, "unit_load_range": UNIT_LOAD_RANGE}


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


def with_recovery(profile, plan: Plan, event: ScenarioEvent, result: dict) -> dict:
    """FR-24: when a what-if delays graduation, offer the Summer/Winter terms that win the time back."""
    if result["delta_terms"] > 0 and plan.terms and event.event_type not in ("Add Summer", "Add Winter"):
        rec = recover(profile, result["plan"], plan.terms[-1].term_label, event.term_label)
        if rec:  # shaped like a scenario result, measured against the plan before the setback
            rec |= {"moved": moves(plan, rec["plan"]), "invalidated": [],
                    "delta_terms": terms_later(plan.terms[-1].term_label, rec["timeline"]["graduation_term"])}
        result["recovery"] = rec
    return result


@app.post("/scenario")
def scenario(req: ScenarioRequest):
    profile = student(req.plan.student_id)
    try:
        return with_recovery(profile, req.plan, req.event, apply_scenario(profile, req.plan, req.event))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/risk")
def risk(req: ValidateRequest):
    """FR-25: per planned course, the graduation delay if failed and the Summer/Winter catch-up that wins it back."""
    try:
        return course_risk(student(req.plan.student_id), req.plan)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/transcript/sample", response_class=PlainTextResponse)
def sample_transcript():
    """A synthetic transcript for demos: a D, a W, a retake, winter and summer terms, transfer credit, a term in progress."""
    return (DATA.parent / "data" / "sample_transcript.txt").read_text(encoding="utf8")


@app.post("/transcript")
async def transcript(request: Request, filename: str = Query("", max_length=200)):
    """FR-26: parse an uploaded transcript (PDF, text, or CSV body) into a temporary student profile."""
    data = await request.body()
    if not data:
        raise HTTPException(400, "empty upload")
    try:
        profile, report = parse_transcript(extract_text(data, filename))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:  # a malformed PDF: say so without echoing its contents
        raise HTTPException(422, "could not read that file as a PDF or text transcript") from e
    if not profile.history and not profile.completed_courses:
        raise HTTPException(422, "no CSUSB terms or courses found; is this an unofficial transcript?")
    profile.id = f"upload-{secrets.token_hex(6)}"
    UPLOADS[profile.id] = profile
    while len(UPLOADS) > MAX_UPLOADS:
        UPLOADS.popitem(last=False)
    return {"student": profile, "report": report}


@app.post("/validate")
def validate(req: ValidateRequest):
    """SRS FR-14: check any pathway (engine-made, edited, or a roadmap) against catalog rules."""
    return {"problems": validate_plan(req.plan, student(req.plan.student_id))}
