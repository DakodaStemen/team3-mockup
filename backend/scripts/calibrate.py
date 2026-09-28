"""Calibrate the guardrail's LLM confidence against hand-labeled queries.

Runs each labeled query through the real Instructor+Ollama call, records raw confidence and whether the
parsed event was correct, then fits CalibratedClassifierCV (isotonic) and reports Brier score + ECE.
Writes backend/calibration.json, which guardrail.calibrate() picks up automatically.

    uv run python scripts/calibrate.py
"""
import json
import sys

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from planner.engine import make_plan  # noqa: E402
from planner.graph import load_students  # noqa: E402
from planner.guardrail import CALIBRATION, llm_classify  # noqa: E402

F, S = "Fail", "Pass"
LABELED = [  # (query, expected (event_type, course_id, term_label, unit_load) or None if not a scenario)
    ("What if I fail CSE 2020 in spring 2027?", (F, "CSE 2020", "Spring 2027", None)),
    ("I think I'm going to fail CS II this spring", (F, "CSE 2020", "Spring 2027", None)),
    ("what happens if I flunk discrete structures", (F, "CSE 2130", "Spring 2027", None)),
    ("If I don't pass CSE 3100 in Fall 2027 how bad is it?", (F, "CSE 3100", "Fall 2027", None)),
    ("fail capstone 1", (F, "CSE 5700", "Fall 2029", None)),
    ("What if I fail Capstone Project I in Fall 2029", (F, "CSE 5700", "Fall 2029", None)),
    ("suppose I fail calculus 1 my first semester", (F, "MATH 2110", "Fall 2026", None)),
    ("I might fail physics 2 in spring 2028", (F, "PHYS 2510", "Spring 2028", None)),
    ("what if CSE 4550 doesn't go well in fall 2028 and I fail", (F, "CSE 4550", "Fall 2028", None)),
    ("fail operating systems fall 2027", (F, "CSE 4600", "Fall 2027", None)),
    ("What if I withdraw from CSE 2020 in Spring 2027?", ("Withdraw", "CSE 2020", "Spring 2027", None)),
    ("I want to drop computer organization in fall 2027", ("Withdraw", "CSE 3300", "Fall 2027", None)),
    ("withdraw from theory of computation spring 2028", ("Withdraw", "CSE 4200", "Spring 2028", None)),
    ("W in databases fall 2028?", ("Withdraw", "CSE 4700", "Fall 2028", None)),
    ("What if I test out of CSE 2130 in spring 2027", (S, "CSE 2130", "Spring 2027", None)),
    ("I got credit by exam for calc 2 in spring 2027", (S, "MATH 2120", "Spring 2027", None)),
    ("pretend I already passed linear algebra fall 2027", (S, "MATH 2250", "Fall 2027", None)),
    ("What if I take summer classes in 2027?", ("Add Summer", None, "Summer 2027", None)),
    ("add a summer 2028 term", ("Add Summer", None, "Summer 2028", None)),
    ("can I speed things up with summer school next year (2027)", ("Add Summer", None, "Summer 2027", None)),
    ("what if I only take 12 units starting fall 2027", ("Change Unit Load", None, "Fall 2027", 12)),
    ("I need to work part time, 9 units from spring 2028", ("Change Unit Load", None, "Spring 2028", 9)),
    ("bump me to 18 units per term from fall 2027", ("Change Unit Load", None, "Fall 2027", 18)),
    ("go full time 15 units starting spring 2027", ("Change Unit Load", None, "Spring 2027", 15)),
    ("What's the best pizza near campus?", None),
    ("who teaches CSE 2020?", None),
    ("is CSE 5160 a hard class?", None),
    ("when does registration open", None),
    ("can you write my essay", None),
    ("what is my GPA", None),
]


def correct(out, expected) -> bool:
    if expected is None:
        return out.intent == "unsupported"
    e = out.event
    if out.intent != "scenario" or e is None:
        return False
    return (e.event_type, e.course_id, e.term_label, e.unit_load) == expected or (
        expected[0] != "Change Unit Load" and (e.event_type, e.course_id, e.term_label) == expected[:3])


def ece(prob: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    idx = np.minimum((prob * bins).astype(int), bins - 1)
    return float(sum(abs(prob[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean()
                     for b in range(bins) if (idx == b).any()))


def evaluate(raw: np.ndarray, y: np.ndarray) -> dict:
    model = CalibratedClassifierCV(LogisticRegression(), method="isotonic", cv=3).fit(raw.reshape(-1, 1), y)
    cal = model.predict_proba(raw.reshape(-1, 1))[:, 1]
    xs = np.linspace(0, 1, 21)
    return {
        "brier_raw": brier_score_loss(y, raw), "brier_calibrated": brier_score_loss(y, cal),
        "ece_raw": ece(raw, y), "ece_calibrated": ece(cal, y),
        "table": {"x": xs.tolist(), "y": model.predict_proba(xs.reshape(-1, 1))[:, 1].tolist()},
    }


if __name__ == "__main__":
    plan = make_plan(load_students()["alex"])
    raw, y = [], []
    for q, expected in LABELED:
        try:
            out = llm_classify(q, plan)
        except Exception as e:
            sys.exit(f"LLM call failed ({e}). Is Ollama running with the model pulled?")
        raw.append(out.confidence)
        y.append(int(correct(out, expected)))
        print(f"{'ok ' if y[-1] else 'BAD'} {out.confidence:.2f}  {q}")
    r = evaluate(np.array(raw), np.array(y))
    print(f"accuracy {np.mean(y):.2f} | Brier raw {r['brier_raw']:.3f} -> {r['brier_calibrated']:.3f}"
          f" | ECE raw {r['ece_raw']:.3f} -> {r['ece_calibrated']:.3f} (recalibrate if > 0.02)")
    CALIBRATION.write_text(json.dumps(r["table"]))
    print(f"wrote {CALIBRATION}")
