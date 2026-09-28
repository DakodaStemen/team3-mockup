# Adaptive Degree Pathway Planner (mock)

CSE 6550 Project 3 pre-team prototype. Spec: [`docs/spec.docx`](docs/spec.docx). Build plan: [`docs/PLAN.md`](docs/PLAN.md).

**Core rule:** the deterministic engine makes every scheduling decision. The LLM only turns a plain-language question into a typed `ScenarioEvent`. Each LLM decision gets a confidence score and a threshold gate, and is logged to an audit trail.

## Run

```sh
# backend (Python 3.12+, uv)
cd backend
uv sync
uv run pytest                                # engine + guardrail tests
uv run uvicorn planner.api:app --port 8000

# frontend
cd frontend
npm install
npm run dev                                  # http://localhost:5173 (proxies /api -> :8000)

# optional: natural-language queries
ollama pull llama3.1 && ollama serve         # OLLAMA_MODEL / OLLAMA_URL env vars override
uv run python scripts/calibrate.py           # fits confidence calibration -> backend/calibration.json
```

Without Ollama running, NL queries are **escalated** to human review. The engine is never called with a guess.

## The 8 required capabilities

| Capability | Where |
|---|---|
| Starting point | `students.json` profiles; grade minimums force retakes (Jordan's D in CSE 2010) |
| Prerequisite / sequencing logic | `graph.py` NetworkX DAG, AND/OR edges, grade minimums, cycle rejection |
| Term-by-term generation | `engine.place()`: constrained greedy topological sort under a unit cap |
| Adaptive recalculation | `engine.apply_scenario()`: re-places only `nx.descendants()` of the changed course |
| Graduation timeline impact | term delta plus a templated one-sentence explanation (no LLM) |
| Alternative pathways | `alternatives()`: fastest (18u) vs balanced (12u) |
| Course availability awareness | Fall-only / Spring-only filtering plus per-term warnings |
| What-if mode | UI previews any scenario; you choose to keep it or discard it |

## API

`GET /catalog` · `GET /students` · `POST /plan {student_id, unit_cap?}` · `POST /scenario {plan, event}` · `POST /query {text, plan}` · `GET /audit`

## Layout

```
backend/planner/  models.py  graph.py  engine.py  guardrail.py  api.py  catalog.json  students.json
backend/tests/    test_engine.py  test_guardrail.py
backend/scripts/  calibrate.py
frontend/src/     App.tsx  index.css
```

## Known limits / deferred

- `catalog.json` is a **hand-seeded, partly illustrative** subset modeled on public CSUSB pages. Verify it against catalog.csusb.edu; the scraper is deferred.
- In this seed data, CSE 5700 and CSE 5720 are both Fall-only. That chain decides graduation, so "fastest" and "balanced" end in the same term and differ only in load.
- Deferred until needed: SQLite persistence, MLflow, P@K metrics, transcript PDF parsing, intake-record guardrail (`MalformedRecordCheck`).
- Guardrail thresholds of 0.90 / 0.60 are placeholders until `calibrate.py` runs on real model output.
