"""NL query -> typed ScenarioEvent via Instructor + Ollama. Never schedules anything itself.

Output is a classification with a calibrated confidence, threshold-gated:
  >= ACCEPT          auto_accepted       -> engine runs the event
  >= REVIEW          accepted_low_conf   -> engine runs it, flagged in the audit log
  below / any error  escalated           -> human review, engine is not called
"""
import json
import os
import re
import threading
import time
from collections import deque
from pathlib import Path
from typing import Literal

import numpy as np
import structlog
from pydantic import BaseModel, Field

from .graph import load_catalog
from .models import UNIT_LOAD_RANGE, Plan, ScenarioEvent

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
ACCEPT, REVIEW = 0.90, 0.60  # placeholders until scripts/calibrate.py is run on real labels
BREAKER_FAILS, BREAKER_COOLDOWN = 3, 60
ROOT = Path(__file__).parent.parent
AUDIT = Path(os.getenv("AUDIT_LOG", ROOT / "audit.jsonl"))
CALIBRATION = ROOT / "calibration.json"


def _make_audit_logger(path: Path):
    # JSONRenderer escapes newlines and control characters, so one decision is always one line.
    return structlog.wrap_logger(
        structlog.WriteLogger(path.open("a", encoding="utf8")),
        processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()],
    )


audit = _make_audit_logger(AUDIT)


class ScenarioQueryClassification(BaseModel):
    intent: Literal["scenario", "unsupported"]
    event: ScenarioEvent | None = None
    confidence: float = Field(ge=0, le=1, description="How sure you are the event matches the student's request")


# ponytail: in-process breaker state; move to shared store if the API runs multi-worker.
_breaker = {"fails": 0, "opened_at": 0.0}
_breaker_lock = threading.Lock()  # sync endpoints run in a threadpool
_table_cache: dict = {}


def _load_table(path: Path) -> tuple[list[float], list[float]] | None:
    """The calibration table, re-read only when the file changes; None if absent or malformed."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    if _table_cache.get("key") != (path, mtime):
        try:
            t = json.loads(path.read_text(encoding="utf8"))
            x, y = [float(v) for v in t["x"]], [float(v) for v in t["y"]]
            ok = len(x) == len(y) >= 2 and x == sorted(x) and all(0 <= v <= 1 for v in x + y)
        except (ValueError, KeyError, TypeError):
            ok = False
        if not ok:
            structlog.get_logger().warning("calibration table malformed; using raw confidence", path=str(path))
        _table_cache.update(key=(path, mtime), table=(x, y) if ok else None)
    return _table_cache["table"]


def calibrate(raw: float) -> float:
    """Map raw LLM confidence through the Platt table from scripts/calibrate.py; raw if none or malformed."""
    table = _load_table(CALIBRATION)
    return raw if table is None else float(np.interp(raw, *table))


def llm_classify(text: str, plan: Plan) -> ScenarioQueryClassification:
    import instructor
    from openai import OpenAI

    client = instructor.from_openai(OpenAI(base_url=OLLAMA_URL, api_key="ollama", timeout=30), mode=instructor.Mode.JSON)
    terms = "\n".join(f"- {t.term_label}: {', '.join(t.courses)}" for t in plan.terms)
    system = (
        "You convert a student's what-if question about their degree plan into ONE structured scenario event. "
        "event_type is one of Pass, Fail, Withdraw, Add Summer, Add Winter, Change Unit Load. "
        "course_id must be a course in the plan, written like 'CSE 2020'. term_label must be a term from the plan, "
        "except Add Summer which uses 'Summer YYYY' and Add Winter which uses 'Winter YYYY' "
        "(the January intersession: Winter 2028 falls between Fall 2027 and Spring 2028). Change Unit Load sets unit_load. "
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
    if event.event_type in ("Add Summer", "Add Winter"):
        season = event.event_type.split()[1]
        return None if re.fullmatch(rf"{season} (19|20|21)\d{{2}}", event.term_label) else f"{season.lower()} term label invalid"
    if event.term_label not in labels:
        return f"term {event.term_label} not in plan"
    if event.event_type == "Change Unit Load":
        lo, hi = UNIT_LOAD_RANGE
        return None if event.unit_load and lo <= event.unit_load <= hi else "unit_load missing or out of range"
    if event.course_id not in load_catalog().courses:
        return f"unknown course {event.course_id}"
    if not any(event.course_id in t.courses for t in plan.terms if t.term_label == event.term_label):
        return f"{event.course_id} not planned in {event.term_label}"
    return None


def classify(text: str, plan: Plan, llm=None) -> dict:
    llm = llm or llm_classify  # looked up at call time so it can be swapped in tests
    result = {"input": text, "parsed_event": None, "raw_confidence": None, "confidence": 0.0, "reason": None}
    with _breaker_lock:
        is_open = _breaker["fails"] >= BREAKER_FAILS and time.time() - _breaker["opened_at"] < BREAKER_COOLDOWN
    if is_open:
        result.update(outcome="escalated", reason="circuit breaker open: LLM unavailable")
    else:
        try:
            out = llm(text, plan)
            with _breaker_lock:
                _breaker["fails"] = 0
        except Exception as e:  # timeout, rate limit, retries exhausted, Ollama down
            with _breaker_lock:
                _breaker["fails"] += 1
                if _breaker["fails"] >= BREAKER_FAILS:
                    _breaker["opened_at"] = time.time()
            out = None
            # The exception text can hold internal URLs or keys, and /audit is readable by clients.
            result["reason"] = f"LLM unavailable ({type(e).__name__})"
            structlog.get_logger().warning("llm_error", error=f"{type(e).__name__}: {e}"[:300])
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
    """Newest first. Streams the file (bounded memory) and skips a line cut short by a crash."""
    if not AUDIT.exists():
        return []
    rows: deque[dict] = deque(maxlen=max(limit, 0))
    with AUDIT.open(encoding="utf8", errors="replace") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(reversed(rows))
