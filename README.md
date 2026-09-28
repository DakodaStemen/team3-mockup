# Adaptive Degree Pathway Planner (ADPP): Engineering Dossier

CSE 6550 Software Engineering · Fall 2026 · CSUSB · Project 3. This README is the **Engineering Dossier Index** (course: *Engineering Dossier Workspace and Repository Structure*).

## Project summary

| | |
|---|---|
| **Problem** | CSUSB planning is split across PAWS, myCAP, roadmap PDFs, and Schedule Planner. None of them show how a failed course, a withdrawal, a lighter load, or a missed once-a-year offering ripples through a student's path to graduation. myCAP even allows a Fall-only course in Spring without warning. |
| **Product** | A web planner that builds a valid term-by-term pathway from a student's history and the BS CS requirements, recalculates it when something changes, and explains the graduation impact. A deterministic engine makes every scheduling decision; an optional AI guardrail only interprets plain-language questions. |
| **Stakeholders** | Students (primary), academic advisors (validators), program coordinator (data), instructor (acquirer), development team |
| **Current scope** | BS Computer Science, CSUSB 2026-27 catalog; public program data; synthetic student records |
| **Non-goals** | SIS, PAWS, or registration integration; real student records; autonomous advising or enrollment; every program and catalog year |
| **Status** | Week 5. SRS v0.1 drafted and in team review. Working prototype `v0.3` on real catalog data. CH-02 proposed. |

**This is a planning aid, not an official degree audit or advising decision.**

## Team

| Team member | Current responsibilities | GitHub |
|---|---|---|
| Dakoda Stemen | Team lead; requirements owner; prototype | `DakodaStemen` |
| *Member 2* | *TBD at team meeting* | |
| *Member 3* | *TBD* | |
| *Member 4* | *TBD* | |
| *Member 5* | *TBD* | |

Lanes and backups: [agile engineering plan §2](docs/03-planning-risk/agile-engineering-plan.md#2-team-organization).

## Current milestone

| Milestone | Status | Responsible | Due | Blockers / decisions |
|---|---|---|---|---|
| **SRS v0.1: Requirements Baseline** (graded, Week 5) | Draft, in team review | Dakoda Stemen + team | Week 5 | Team must accept or reject [CH-02](docs/01-product-requirements/srs-change-proposal-CH-02.md) and decide conflicts C-1 through C-6. The instructor and team members must be added to this repo. |

## Engineering Dossier Index

| Artifact | Version | Owner | Status | Authoritative location | Last updated |
|---|---|---|---|---|---|
| Project Confirmation Card | 0.1 | Dakoda Stemen | Confirmed | *Add link (not yet in repo or Drive index)* | |
| Software Requirements Specification | 0.1 | Dakoda Stemen | In review | [Google Doc: SRS v0.1](https://docs.google.com/document/d/1h-cgCt8wF0NcHRoyRzOdYJiq81ip6GJhvYBi4g2LHtY/edit) (snapshot to `docs/01-product-requirements/` when baselined) | 2026-09-27 |
| Evidence Register | 0.1 | Dakoda Stemen | Drafting | SRS §5.2, plus proposed updates in [CH-02 §A](docs/01-product-requirements/srs-change-proposal-CH-02.md#a-evidence-register-updates-srs-52) | 2026-09-28 |
| SRS change proposal CH-02 | 0.1 | Dakoda Stemen | In review | [srs-change-proposal-CH-02.md](docs/01-product-requirements/srs-change-proposal-CH-02.md) | 2026-09-28 |
| Requirement attribute register | 0.3 | Dakoda Stemen | Active | [requirements-register.md](docs/01-product-requirements/requirements-register.md) | 2026-09-28 |
| Traceability (verification side) | generated | CI | Active | [traceability.md](docs/01-product-requirements/traceability.md) | per commit |
| Technical spec (design input, EV-08) | 0.1 | Dakoda Stemen | Baselined | [ADPP_TechnicalSpec_v0.1_2026-09-28.docx](docs/01-product-requirements/ADPP_TechnicalSpec_v0.1_2026-09-28.docx) | 2026-09-28 |
| References | 0.1 | Dakoda Stemen | Drafting | [references.md](docs/01-product-requirements/references.md) | 2026-09-28 |
| Team research: offering and roadmap findings (EV-09) | 1.0 | Team | Confirmed | Team Drive: *Course Offering & Roadmap Data – Team Findings* | 2026-09-24 |
| System models, architecture views, ADRs | 0.3 | *TBD* | In review | [design.md](docs/02-models-architecture/design.md) | 2026-09-28 |
| Agile Engineering Plan (incl. Definition of Done) | 0.3 | *TBD (ScrumMaster)* | Drafting | [agile-engineering-plan.md](docs/03-planning-risk/agile-engineering-plan.md) | 2026-09-28 |
| Risk register | 0.3 | *TBD (ScrumMaster)* | Active | [risk-register.md](docs/03-planning-risk/risk-register.md) | 2026-09-28 |
| Backlog | live | Product Owner | Active | GitHub Issues, label `backlog` | live |
| Weekly stand-ups and retrospectives | — | ScrumMaster | Not started | `docs/03-planning-risk/standups/` (created at the first stand-up) | |
| Verification strategy (STP elements) | 0.3 | *TBD (quality lane)* | Drafting | [verification-strategy.md](docs/04-quality-security-testing/verification-strategy.md) | 2026-09-28 |
| Quality gates and CM plan (SQAP elements) | 0.3 | *TBD (quality lane)* | Drafting | [quality-and-cm-plan.md](docs/04-quality-security-testing/quality-and-cm-plan.md) | 2026-09-28 |
| Threat and misuse analysis; ethics | 0.3 | *TBD* | Drafting | [threat-analysis.md](docs/04-quality-security-testing/threat-analysis.md) | 2026-09-28 |
| CI evidence | live | CI | Active | GitHub Actions: `.github/workflows/ci.yml` | per commit |
| Evaluation results (EV-07) | 0.2 | *TBD* | Provisional | [backend/results/summary.md](backend/results/summary.md) | 2026-09-28 |
| AI Engineering Log (AI provenance) | 0.3 | Dakoda Stemen | Active | [ai-engineering-log.md](docs/05-ai-provenance/ai-engineering-log.md) | 2026-09-28 |
| Release notes | 0.3.0 | Dakoda Stemen | Active | [CHANGELOG.md](CHANGELOG.md), git tags | 2026-09-28 |

Status labels follow the course list: Not started, Drafting, In review, Baselined, Revision required, Revised, Superseded.

**Process in brief:**
- Branch, then a PR using the template checklist. CI must be green and a non-author must review.
- Requirement changes go into the SRS first, as CH-nn in Appendix A.
- Significant AI help is logged in the AI Engineering Log.
- Methods follow Sommerville 10e (Ch 3–8, 13, 22–25) as tailored in each document.

## Setup and run

```sh
# backend (Python 3.12+, uv)
cd backend
uv sync
uv run pytest                                # 49 tests incl. traceability check
uv run ruff check .
uv run python scripts/trace.py               # regenerate traceability.md after changing tests or register
uv run python scripts/ingest.py              # rebuild planner/catalog.json from cached sources (--refresh re-downloads)
uv run python scripts/results.py             # regenerate results/
uv run uvicorn planner.api:app --port 8000   # OpenAPI contract at /openapi.json

# frontend
cd frontend
npm install
npm run dev                                  # http://localhost:5173 (proxies /api -> :8000)

# optional: natural-language queries (self-hosted LLM)
ollama pull llama3.1 && ollama serve
uv run python scripts/calibrate.py           # confidence calibration (NFR-13)
```

Without Ollama, plain-language queries are **escalated**. The engine never acts on a guess.

## Data

- **Program data:** public CSUSB pages, fetched by `backend/scripts/ingest.py`. It checks robots.txt, waits 2 s between requests, and keeps byte-exact raw copies in `backend/data/raw/`. Sources:
  - catalog course pages (CSE, MATH, PHYS);
  - the BS CS program page;
  - the freshman and transfer roadmap PDFs.
- **Output:** `backend/planner/catalog.json`, with 63 courses, 69 AND/OR prerequisite edges (grade minimums, corequisites, standing), requirement groups, roadmaps, and 11 catalog-vs-roadmap discrepancies.
- **Test data:**
  - `planner/students.json`: 6 synthetic students.
  - `data/queries.json`: 45 labeled NL queries.
  - `data/labeled_records.json`: 80 labeled good and bad catalog records.

## Repository layout

The course's recommended `src/`, `tests/`, and `prototype/` are adapted as backend/frontend packages; the dossier folders follow the course layout.

```
README.md                         Dossier Index (this file)
CHANGELOG.md                      release notes
docs/01-product-requirements/     register, traceability, CH-02, references, tech spec
docs/02-models-architecture/      design.md: models, 4+1 views, ADRs, interface spec
docs/03-planning-risk/            agile engineering plan, risk register
docs/04-quality-security-testing/ verification strategy, quality and CM plan, threat analysis
docs/05-ai-provenance/            AI Engineering Log
backend/planner/                  models, graph, engine, guardrail, api, catalog.json, students.json
backend/scripts/                  ingest, results, calibrate, trace
backend/tests/                    requirement-tagged tests
backend/data/, backend/results/   raw sources and datasets; evaluation outputs
frontend/src/                     React client
.github/                          CI, PR template, issue forms (change request, bug, backlog)
```
