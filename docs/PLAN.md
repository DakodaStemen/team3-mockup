# Adaptive Degree Pathway Planner — Mock Build Plan

## Context
`C:\Projects\team3-mockup` is empty. The spec (`Adaptive Degree Pathway Planner — Technical Spec.docx`, CSE 6550 Project 3) calls for a mock that proves three things:
1. End-to-end pipeline: history + requirements → term-by-term plan → scenario event → recalculated plan + graduation delta + plain-language explanation.
2. All 8 capabilities touched: starting point, prereq logic, term-by-term generation, adaptive recalc, timeline impact, alternative pathways, availability awareness, what-if mode.
3. Visible guardrails: AI only parses NL → typed scenario; deterministic engine makes every scheduling decision; every AI judgment has confidence + audit log.

Decisions: private GitHub repo `DakodaStemen/team3-mockup`, build a working mock, Instructor → local **Ollama**.

## Repo layout (fewest files that cover the spec)
```
README.md                 run instructions + capability map
docs/spec.docx            original spec (copied in)
backend/
  pyproject.toml          uv; deps: fastapi uvicorn pydantic networkx instructor openai structlog scikit-learn pytest
  planner/
    models.py             Course, PrerequisiteEdge, StudentProfile, TermPlan, ScenarioEvent (spec fields verbatim)
    catalog.json          hand-seeded CSUSB BS CS subset (~30 courses) from public catalog + roadmap, incl. the 4 known discrepancies, Fall-only CSE 5700/5720, Spring-only PHYS 2510/L, CSE 2020 gating chain
    students.json         3 synthetic profiles (freshman / mid / senior)
    graph.py              load catalog → nx.DiGraph; reject+log cycle edges; priority = out-degree + longest downstream depth
    engine.py             plan(), apply_scenario(), timeline(), alternatives()
    guardrail.py          Instructor+Ollama NL→ScenarioQueryClassification; threshold gate; circuit breaker; structlog JSON audit
    api.py                FastAPI endpoints
  tests/test_engine.py    one file, asserts core behaviors
  scripts/calibrate.py    CalibratedClassifierCV + Brier/ECE on a small labeled set
frontend/                 Vite React+TS, single App.tsx + Reagraph DAG view
```

## Engine (deterministic, `engine.py`)
- **plan(profile, unit_cap, start_term)** — constrained greedy topo sort: each term, candidates = prereqs satisfied (AND/OR + grade minimum) AND offered that term; sort by priority; pack under unit cap. Unplaceable-this-term → `TermPlan.warnings`.
- **timeline(plan)** — term count / critical-path length (`nx.dag_longest_path` for explanation of the gating chain).
- **apply_scenario(plan, event)** — Fail/Withdraw: `nx.descendants(G, course)` = invalidated set; keep everything else in place; re-place only the invalidated set from the next term. Pass/Add Summer/Change Unit Load handled by same re-place path. Returns new plan + delta + templated sentence ("Graduation delayed by 1 term because CSE 2020 gates 3 courses now pushed to the next offering"). Explanation is a string template, not LLM.
- **What-if mode** = apply_scenario on a copy, never persisted.
- **alternatives()** = plan at two caps: "fastest" (18 units) vs "balanced" (12–15).
- Discrepancy handling: catalog wins for units/prereqs; `discrepancy_flag` surfaced in UI, never auto-resolved.

## Guardrail (`guardrail.py`)
- Instructor over Ollama's OpenAI-compatible endpoint (`http://localhost:11434/v1`, model via `OLLAMA_MODEL` env, default `llama3.1`).
- Output schema: `ScenarioQueryClassification{intent, event: ScenarioEvent|None, confidence}`.
- Gate: ≥0.90 auto-accept → engine; 0.60–0.90 accept + log low-confidence; <0.60 or retries exhausted / breaker open → escalate to human-review list (returned in API, no engine call).
- Circuit breaker: module-level counter, open after 3 consecutive failures for 60s. `# ponytail:` note — in-process only.
- Every decision logged via structlog JSON to `backend/audit.jsonl` (input, output, confidence, band, outcome).

## API (`api.py`)
- `GET /catalog` — nodes, edges, discrepancies (for DAG view)
- `GET /students` — synthetic profiles
- `POST /plan` `{student_id, unit_cap}` → plan + alternatives + timeline
- `POST /scenario` `{plan, event, what_if}` → new plan, delta, explanation, invalidated courses
- `POST /query` `{text, plan}` → guardrail result; if accepted, runs /scenario
- `GET /audit` — tail of audit.jsonl

## Frontend (`frontend/src/App.tsx`)
Student picker → term columns (warnings + discrepancy badges) → scenario form + NL query box → delta banner with explanation, invalidated courses highlighted → Reagraph DAG → audit panel. Vite dev proxy to `:8000`.

## Deferred (per spec, not needed to prove the 3 goals)
- **Scraper** (requests/BS4, pdfplumber) — seed JSON is hand-built from the same public pages; add when catalog > one program.
- **SQLite** — JSON files suffice; add when plans must persist.
- **MLflow, P@K metrics** — add once team has a labeled expected-pathway set.
- **Transcript PDF upload** — out of scope for mock.

## Steps
1. `git init`, `.gitignore`, copy spec to `docs/`, README.
2. Backend: models → catalog/students JSON → graph → engine → tests green.
3. Guardrail + API.
4. Frontend.
5. `calibrate.py` with ~30 hand-labeled examples.
6. Commit, `gh repo create DakodaStemen/team3-mockup --private --source . --push`.

## Verification
- `cd backend && uv run pytest` — asserts: no Fall-only course lands in Spring; prereqs always earlier; failing CSE 2020 in Fall invalidates exactly its descendants and delays graduation ≥1 term; cycle edge rejected+logged; alternatives differ in term count.
- `uv run uvicorn planner.api:app` + `curl POST /plan`, `/scenario` for the fail-CSE-2020 demo.
- With Ollama running: `/query "what if I fail CSE 2020 this fall"` → accepted, recalculated. With Ollama stopped: same query → escalated, breaker opens after 3, audit.jsonl shows entries.
- `cd frontend && npm run dev` — click through all 8 capabilities.
