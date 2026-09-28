"""NL query -> typed ScenarioEvent via Instructor + Ollama. Never schedules anything itself.

Output is a classification with a calibrated confidence, threshold-gated:
  >= ACCEPT          auto_accepted       -> engine runs the event
  >= REVIEW          accepted_low_conf   -> engine runs it, flagged in the audit log
  below / any error  escalated           -> human review, engine is not called
"""
import json
import os
import time
from pathlib import Path
from typing import Literal

import numpy as np
import structlog
from pydantic import BaseModel, Field

from .graph import load_catalog
from .models import Plan, ScenarioEvent

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
ACCEPT, REVIEW = 0.90, 0.60  # placeholders until scripts/calibrate.py is run on real labels
BREAKER_FAILS, BREAKER_COOLDOWN = 3, 60
ROOT = Path(__file__).parent.parent
AUDIT = Path(os.getenv("AUDIT_LOG", ROOT / "audit.jsonl"))
CALIBRATION = ROOT / "calibration.json"

audit = structlog.wrap_logger(
    structlog.WriteLogger(AUDIT.open("a", encoding="utf8")),
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()],
)


class ScenarioQueryClassification(BaseModel):
    intent: Literal["scenario", "unsupported"]
    event: ScenarioEvent | None = None
    confidence: float = Field(ge=0, le=1, description="How sure you are the event matches the student's request")


# ponytail: in-process breaker state; move to shared store if the API runs multi-worker.
_breaker = {"fails": 0, "opened_at": 0.0}


def calibrate(raw: float) -> float:
    """Map raw LLM confidence through the isotonic/Platt table from scripts/calibrate.py, if present."""
    if not CALIBRATION.exists():
        return raw
    table = json.loads(CALIBRATION.read_text())
    return float(np.interp(raw, table["x"], table["y"]))


def llm_classify(text: str, plan: Plan) -> ScenarioQueryClassification:
    import instructor
    from openai import OpenAI

    client = instructor.from_openai(OpenAI(base_url=OLLAMA_URL, api_key="ollama", timeout=30), mode=instructor.Mode.JSON)
    terms = "\n".join(f"- {t.term_label}: {', '.join(t.courses)}" for t in plan.terms)
    system = (
        "You convert a student's what-if question about their degree plan into ONE structured scenario event. "
        "event_type is one of Pass, Fail, Withdraw, Add Summer, Change Unit Load. "
        "course_id must be a course in the plan, written like 'CSE 2020'. term_label must be a term from the plan, "
        "except Add Summer which uses 'Summer YYYY'. Change Unit Load sets unit_load. "
        "If the question is not a scenario, set intent=unsupported. Be honest in confidence.\n"
        f"Current plan:\n{terms}"
    )
    return client.chat.completions.create(
        model=OLLAMA_MODEL, response_model=ScenarioQueryClassification, max_retries=2,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
    )


def validate(event: ScenarioEvent | None, plan: Plan) -> str | None:
    """Deterministic sanity check on the LLM's typed output. Returns a reason if it must be escalated."""
    if event is None:
        return "no event produced"
    labels = {t.term_label for t in plan.terms}
    if event.event_type == "Add Summer":
        return None if event.term_label.startswith("Summer") else "summer term label invalid"
    if event.term_label not in labels:
        return f"term {event.term_label} not in plan"
    if event.event_type == "Change Unit Load":
        return None if event.unit_load and 3 <= event.unit_load <= 21 else "unit_load missing or out of range"
    if event.course_id not in load_catalog().courses:
        return f"unknown course {event.course_id}"
    if not any(event.course_id in t.courses for t in plan.terms if t.term_label == event.term_label):
        return f"{event.course_id} not planned in {event.term_label}"
    return None


def classify(text: str, plan: Plan, llm=llm_classify) -> dict:
    result = {"input": text, "parsed_event": None, "raw_confidence": None, "confidence": 0.0, "reason": None}
    if _breaker["fails"] >= BREAKER_FAILS and time.time() - _breaker["opened_at"] < BREAKER_COOLDOWN:
        result.update(outcome="escalated", reason="circuit breaker open: LLM unavailable")
    else:
        try:
            out = llm(text, plan)
            _breaker["fails"] = 0
        except Exception as e:  # timeout, rate limit, retries exhausted, Ollama down
            _breaker["fails"] += 1
            if _breaker["fails"] >= BREAKER_FAILS:
                _breaker["opened_at"] = time.time()
            out = None
            result["reason"] = f"LLM error: {type(e).__name__}: {e}"[:300]
        if out is None:
            result["outcome"] = "escalated"
        else:
            conf = calibrate(out.confidence)
            reason = "not a scenario question" if out.intent != "scenario" else validate(out.event, plan)
            result.update(parsed_event=out.event.model_dump() if out.event else None,
                          raw_confidence=out.confidence, confidence=round(conf, 3), reason=reason)
            if reason or conf < REVIEW:
                result["outcome"] = "escalated"
                result["reason"] = reason or f"confidence {conf:.2f} below {REVIEW}"
            else:
                result["outcome"] = "auto_accepted" if conf >= ACCEPT else "accepted_low_confidence"
    audit.info("guardrail_decision", student_id=plan.student_id, thresholds=[REVIEW, ACCEPT], **result)
    return result


def read_audit(limit: int = 50) -> list[dict]:
    if not AUDIT.exists():
        return []
    lines = AUDIT.read_text(encoding="utf8").splitlines()[-limit:]
    return [json.loads(line) for line in reversed(lines)]
