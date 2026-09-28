# Adaptive Degree Pathway Planner (mock)

CSE 6550 Project 3 pre-team prototype. Spec: [`docs/spec.docx`](docs/spec.docx).

## Documentation

The process and documents follow Sommerville, *Software Engineering* 10e.

| Document | Textbook basis |
|---|---|
| [SRS](docs/SRS.md): requirements, use cases, API contract | Ch 4 (Fig 4.17 structure) |
| [Design](docs/DESIGN.md): system models, 4+1 views, patterns, ADRs | Ch 5, 6, 7 |
| [Test plan](docs/TEST_PLAN.md) and [traceability matrix](docs/TRACEABILITY.md) | Ch 8, §4.6 |
| [Project plan](docs/PROJECT_PLAN.md): Scrum roles, sprints, milestones | Ch 3, 23 |
| [Risk register](docs/RISKS.md) | Ch 22 |
| [Quality and CM plan](docs/QUALITY_AND_CM.md): standards, reviews, branching, change and release management | Ch 24, 25 |
| [Security and ethics](docs/SECURITY.md) | Ch 13, §1.2 |
| [Changelog](CHANGELOG.md) | §25.4 |

Contributing: branch → PR (template checklist) → CI green → non-author review. Requirement changes use the *Change request* issue form.

**Core rule:** the deterministic engine makes every scheduling decision. The LLM only turns a plain-language question into a typed `ScenarioEvent`. Each LLM decision gets a confidence score and a threshold gate, and is logged to an audit trail.

## Run

```sh
# backend (Python 3.12+, uv)
cd backend
uv sync
uv run pytest                                # engine, guardrail, and parser tests
uv run python scripts/ingest.py              # rebuild planner/catalog.json from cached sources (--refresh to re-download)
uv run python scripts/results.py             # write results/ (pathway quality, scenario sweep, bottlenecks)
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

## Data

These come from public CSUSB pages. No login is involved, `robots.txt` is checked, requests are 2s apart, and raw copies are kept in `backend/data/raw/`:

| Source | Used for |
|---|---|
| catalog.csusb.edu `coursesaz/{cse,math,phys}` | units, titles, prerequisite text (the catalog is authoritative) |
| catalog.csusb.edu BS Computer Science page | degree requirements: required courses, choose-1 AI group, 12 elective units, 120 total |
| csusb.edu freshman + transfer roadmap PDFs | term offerings and the recommended sequence (used as the expected pathways) |

`scripts/ingest.py` parses all of this into `backend/planner/catalog.json`: 63 courses, 69 prerequisite edges with AND/OR groups, grade minimums, corequisites and standing, plus requirement groups and the roadmaps. Every catalog-vs-roadmap disagreement it finds is logged. From the source alone it reproduces the spec's audit (CSE 4010 and CSE 4550 units, 125 vs 120 total units, CSE 4600 prerequisites) and finds 7 more.

Datasets for tests and results:
- `planner/students.json`: 6 synthetic profiles (freshman, transfer, retake, missed Spring-only course, part-time, senior).
- `data/queries.json`: 45 labeled natural-language queries (scenario, ambiguous, off-topic, one prompt injection) for `calibrate.py`.
- `data/labeled_records.json`: 80 good and deliberately broken catalog records, labeled with the defect, for a future intake guardrail.

## Results

`backend/results/summary.md` holds the latest run. What it measures:
- **Pathway quality** against the official roadmaps: precision and recall per term, and how many terms each course lands from where the roadmap puts it.
- **Roadmap audit**: the official roadmaps checked against catalog rules.
- **Scenario sweep**: 282 what-if runs.
- **Bottleneck analysis**: the priority score vs betweenness centrality vs the delay actually measured when a course is failed.

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
backend/tests/    test_engine.py  test_guardrail.py  test_ingest.py
backend/scripts/  ingest.py  results.py  calibrate.py
backend/data/     raw/  queries.json  labeled_records.json
backend/results/  summary.md  *.json  scenario_runs.csv
frontend/src/     App.tsx  index.css
```

## Known limits / deferred

- Only the BS CS program is ingested. Courses that aren't on a roadmap have `Unknown` term offering: the planner allows them and warns.
- Upper-division GE is assumed to need 60 units. Prerequisites outside the program (CSE 1250, MATH 1401/1403) are treated as placement.
- Deferred until needed: SQLite persistence, MLflow (results are plain CSV/JSON for now), transcript PDF parsing, and the intake-record guardrail (`MalformedRecordCheck`; its labeled data is ready).
- Guardrail thresholds of 0.90 / 0.60 are placeholders until `calibrate.py` runs on real model output.
