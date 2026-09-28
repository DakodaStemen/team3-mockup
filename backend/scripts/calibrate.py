"""Calibrate the guardrail's LLM confidence against hand-labeled queries.

Runs each labeled query through the real Instructor+Ollama call, records raw confidence and whether the
parsed event was correct, then fits CalibratedClassifierCV (sigmoid by default) and reports out-of-fold Brier score + ECE.
Writes backend/calibration.json, which guardrail.calibrate() picks up automatically.

    uv run python scripts/calibrate.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import StratifiedKFold, cross_val_predict

sys.path.insert(0, str(Path(__file__).parent.parent))
from planner.engine import make_plan  # noqa: E402
from planner.graph import load_students  # noqa: E402
from planner.guardrail import CALIBRATION, OLLAMA_MODEL, llm_classify  # noqa: E402

MIN_PER_CLASS = 4
QUERIES = Path(__file__).parent.parent / "data" / "queries.json"  # labeled against Alex's plan


def correct(out, expected: dict | None) -> bool:
    if expected is None:
        return out.intent == "unsupported"
    e = out.event
    if out.intent != "scenario" or e is None:
        return False
    keys = ["event_type", "course_id", "term_label"] + (["unit_load"] if expected["event_type"] == "Change Unit Load" else [])
    return all(getattr(e, k) == expected[k] for k in keys)


def ece(prob: np.ndarray, y: np.ndarray, bins: int = 5) -> float:  # ~9 queries per bin at n=45; 10 bins is noise
    idx = np.minimum((prob * bins).astype(int), bins - 1)
    return float(sum(abs(prob[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean()
                     for b in range(bins) if (idx == b).any()))


def evaluate(raw: np.ndarray, y: np.ndarray, method: str = "sigmoid", folds: int = 5) -> dict:
    """Metrics come from out-of-fold predictions; the saved table comes from a fit on all rows."""
    X = raw.reshape(-1, 1)
    base = CalibratedClassifierCV(LogisticRegression(), method=method, cv=3)
    minority = int(np.bincount(y, minlength=2).min())
    if minority < MIN_PER_CLASS:  # outer folds, then the calibrator's own cv=3, each need both classes
        raise ValueError(f"Need at least {MIN_PER_CLASS} correct and {MIN_PER_CLASS} incorrect labeled queries to calibrate; "
                         f"the smaller class has {minority}. Label more queries.")
    k = min(folds, minority)
    cal = cross_val_predict(base, X, y, cv=StratifiedKFold(k, shuffle=True, random_state=0),
                            method="predict_proba")[:, 1]
    model = base.fit(X, y)
    xs = np.linspace(0, 1, 21)
    return {
        "brier_raw": brier_score_loss(y, raw), "brier_calibrated": brier_score_loss(y, cal),
        "ece_raw": ece(raw, y), "ece_calibrated": ece(cal, y),
        "method": method, "folds": k,
        "table": {"x": xs.tolist(), "y": model.predict_proba(xs.reshape(-1, 1))[:, 1].tolist()},
    }


if __name__ == "__main__":
    plan = make_plan(load_students()["alex"])
    raw, y = [], []
    labeled = json.loads(QUERIES.read_text(encoding="utf8"))
    for item in labeled:
        q, expected = item["query"], item["expected"]
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
    out_dir = Path(__file__).parent.parent / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "calibration.json").write_text(json.dumps({
        "model": OLLAMA_MODEL, "n": len(y), "accuracy": float(np.mean(y)),
        **{k: v for k, v in r.items() if k != "table"},
        "runs": [{"query": i["query"], "raw_confidence": c, "correct": bool(k)} for i, c, k in zip(labeled, raw, y, strict=True)],
    }, indent=1))
    print(f"wrote {CALIBRATION}")
