# Adaptive Degree Pathway Planner (ADPP): Engineering Dossier

CSE 6550 Software Engineering · Fall 2026 · CSUSB · Project 3. This README is the **Engineering Dossier Index** (course: *Engineering Dossier Workspace and Repository Structure*). **Looking for a document? Start at the [documentation index](docs/README.md).**

**Contents:** [Summary](#project-summary) · [Team](#team) · [Milestone](#current-milestone) · [Dossier index](#engineering-dossier-index) · [Quick start](#quick-start) · [Setup](#setup-and-run) · [Pages demo](#github-pages-demo) · [Data](#data) · [Layout](#repository-layout)

## Project summary

| | |
|---|---|
| **Problem** | CSUSB planning is split across PAWS, myCAP, roadmap PDFs, and Schedule Planner. None of them show how a failed course, a withdrawal, a lighter load, or a missed once-a-year offering ripples through a student's path to graduation. myCAP even allows a Fall-only course in Spring without warning. |
| **Product** | A web planner that builds a valid term-by-term pathway from a student's history and the BS CS requirements, recalculates it when something changes, and explains the graduation impact. A deterministic engine makes every scheduling decision. |
| **Stakeholders** | Students (primary), academic advisors (validators), program coordinator (data), instructor (acquirer), development team |
| **Current scope** | BS Computer Science, CSUSB 2026-27 catalog; public program data; synthetic student records |
| **Non-goals** | SIS, PAWS, or registration integration; real student records; autonomous advising or enrollment; every program and catalog year |
| **Status** | Week 5. SRS v0.1 drafted and in team review. Working prototype `v0.1.0` on real catalog data. CH-02, CH-03, and CH-04 proposed. |

**This is a planning aid, not an official degree audit or advising decision.**

## Team

| Team member | Current responsibilities | GitHub |
|---|---|---|
| Dakoda Stemen | Team lead; requirements owner; prototype | `DakodaStemen` |
| Yao Guo | *TBD at team meeting* | |
| Lusine Hayrapetyan | *TBD* | |
| Fabian Torres | *TBD* | |

Lanes and backups: [agile engineering plan §2](docs/03-planning-risk/agile-engineering-plan.md#2-team-organization).

## Current milestone

| Milestone | Status | Responsible | Due | Blockers / decisions |
|---|---|---|---|---|
| **SRS v0.1: Requirements Baseline** (graded, Week 5) | Draft, in team review | Dakoda Stemen + team | Week 5 | Team must accept or reject [CH-02](docs/01-product-requirements/srs-change-proposal-CH-02.md), [CH-03](docs/01-product-requirements/srs-change-proposal-CH-03.md), and [CH-04](docs/01-product-requirements/srs-change-proposal-CH-04.md), and decide the open conflicts in CH-02 §C and CH-04 §C-1 (real transcripts). The instructor and team members must be added to this repo. |

## Engineering Dossier Index

| Artifact | Version | Owner | Status | Authoritative location | Last updated |
|---|---|---|---|---|---|
| Project Confirmation Card | 0.1 | Dakoda Stemen | Confirmed | *Add link (not yet in repo or Drive index)* | |
| Software Requirements Specification | 0.1 | Dakoda Stemen | In review | [Google Doc: SRS v0.1](https://docs.google.com/document/d/1h-cgCt8wF0NcHRoyRzOdYJiq81ip6GJhvYBi4g2LHtY/edit) (snapshot to `docs/01-product-requirements/` when baselined) | 2026-09-27 |
| Evidence Register | 0.1 | Dakoda Stemen | Drafting | SRS §5.2, plus proposed updates in [CH-02 §A](docs/01-product-requirements/srs-change-proposal-CH-02.md#a-evidence-register-updates-srs-52) | 2026-09-28 |
| SRS change proposal CH-02 | 0.1 | Dakoda Stemen | In review | [srs-change-proposal-CH-02.md](docs/01-product-requirements/srs-change-proposal-CH-02.md) | 2026-09-28 |
| SRS change proposal CH-03 (summer/winter, labs, catch-up) | 0.1 | Dakoda Stemen | In review | [srs-change-proposal-CH-03.md](docs/01-product-requirements/srs-change-proposal-CH-03.md) | 2026-09-28 |
| SRS change proposal CH-04 (history, risk, transcript upload) | 0.1 | Dakoda Stemen | In review | [srs-change-proposal-CH-04.md](docs/01-product-requirements/srs-change-proposal-CH-04.md) | 2026-09-28 |
| Product context and design system | 0.1 | Dakoda Stemen | Drafting | [PRODUCT.md](PRODUCT.md), [DESIGN.md](DESIGN.md) | 2026-09-29 |
| Requirement attribute register | 0.1 | Dakoda Stemen | Active | [requirements-register.md](docs/01-product-requirements/requirements-register.md) | 2026-09-29 |
| Traceability (verification side) | generated | CI | Active | [traceability.md](docs/01-product-requirements/traceability.md) | per commit |
| Technical spec (design input, EV-08) | 0.1 | Dakoda Stemen | Baselined | [ADPP_TechnicalSpec_v0.1_2026-09-28.docx](docs/01-product-requirements/ADPP_TechnicalSpec_v0.1_2026-09-28.docx) | 2026-09-28 |
| References | 0.1 | Dakoda Stemen | Drafting | [references.md](docs/01-product-requirements/references.md) | 2026-09-29 |
| Team research: offering and roadmap findings (EV-09) | 1.0 | Team | Confirmed | Team Drive: *Course Offering & Roadmap Data – Team Findings* | 2026-09-24 |
| System models, architecture views, ADRs | 0.1 | *TBD* | In review | [design.md](docs/02-models-architecture/design.md) | 2026-09-29 |
| UML diagram set (Mermaid and PlantUML) | 0.1 | *TBD* | In review | [uml-diagrams.md](docs/02-models-architecture/uml-diagrams.md) | 2026-09-29 |
| Agile Engineering Plan (incl. Definition of Done) | 0.1 | *TBD (ScrumMaster)* | Drafting | [agile-engineering-plan.md](docs/03-planning-risk/agile-engineering-plan.md) | 2026-09-29 |
| Risk register | 0.1 | *TBD (ScrumMaster)* | Active | [risk-register.md](docs/03-planning-risk/risk-register.md) | 2026-09-29 |
| Backlog | live | Product Owner | Active | GitHub Issues, label `backlog` | live |
| Weekly stand-ups and retrospectives | — | ScrumMaster | Not started | `docs/03-planning-risk/standups/` (created at the first stand-up) | |
| Verification strategy (STP elements) | 0.1 | *TBD (quality lane)* | Drafting | [verification-strategy.md](docs/04-quality-security-testing/verification-strategy.md) | 2026-09-29 |
| Quality gates and CM plan (SQAP elements) | 0.1 | *TBD (quality lane)* | Drafting | [quality-and-cm-plan.md](docs/04-quality-security-testing/quality-and-cm-plan.md) | 2026-09-29 |
| Threat and misuse analysis; ethics | 0.1 | *TBD* | Drafting | [threat-analysis.md](docs/04-quality-security-testing/threat-analysis.md) | 2026-09-29 |
| CI evidence | live | CI | Active | GitHub Actions: `.github/workflows/ci.yml` | per commit |
| Evaluation results (EV-07) | 0.1 | *TBD* | Provisional | [backend/results/summary.md](backend/results/summary.md) | 2026-09-28 |
| AI Engineering Log (AI provenance) | 0.1 | Dakoda Stemen | Active | [ai-engineering-log.md](docs/05-ai-provenance/ai-engineering-log.md) | 2026-09-29 |
| Release notes | 0.1.0 | Dakoda Stemen | Active | [CHANGELOG.md](CHANGELOG.md), git tag `v0.1.0` | 2026-09-29 |

Status labels follow the course list: Not started, Drafting, In review, Baselined, Revision required, Revised, Superseded.

**Process in brief:**

- Branch, then a PR using the template checklist. CI must be green and a non-author must review.
- Requirement changes go into the SRS first, as CH-nn in Appendix A.
- Significant AI help is logged in the AI Engineering Log.
- Methods follow Sommerville 10e (Ch 3–8, 13, 22–25) as tailored in each document.

## Quick start

Requires [uv](https://docs.astral.sh/uv/), Python 3.12+, and Node.js 22.12+ (or 20.19+).

```sh
./dev.sh    # installs deps if needed, starts API :8000 + UI :5173; Ctrl+C stops both
```

Open http://localhost:5173. Things to try:

- Click any course (term grid, bottleneck table, or graph) to load it into the what-if form, then **Run what-if**.
- **Keep this plan** stacks changes in *Plan history*; **Undo last** / **Reset to baseline** walk them back.
- Change the base **Unit cap** or **Student** in the header to replan from scratch.
- **Upload a transcript** (PDF, text, or CSV; or use the synthetic sample) to plan from a record with past terms. It is parsed in memory and never saved.
- Add **Summer** or **Winter** terms as what-ifs; when a setback delays graduation, the catch-up suggestion shows the fewest intersessions that win the time back.
- The **Prerequisite map** view of the plan shows every dependency on the same timeline.

Tests: `cd backend && uv run pytest -q` (207 tests: engine, fuzz and term sweeps, API, security, transcript, ingest, in-browser bridge, traceability) and `cd frontend && npm run test:e2e` (Playwright drives the real app; first run may need `npx playwright install chromium`). `npm run test:e2e:static` runs the walkthrough against the GitHub Pages build.

## Setup and run

```sh
# backend (Python 3.12+, uv)
cd backend
uv sync
uv run pytest                                # engine, fuzz, API, security, transcript, scripts, ingest, and traceability tests
uv run ruff check .
uv run python scripts/trace.py               # regenerate traceability.md after changing tests or register
uv run python scripts/ingest.py              # rebuild planner/catalog.json from cached sources (--refresh re-downloads)
uv run python scripts/ingest_all.py          # read every catalog subject into data/all_courses.json
uv run python scripts/outliers.py            # screen that dataset into results/outliers.json
uv run python scripts/results.py             # regenerate results/
uv run python scripts/pages_bundle.py        # zip the engine for the in-browser (GitHub Pages) build
uv run uvicorn planner.api:app --port 8000   # OpenAPI contract at /openapi.json

# frontend
cd frontend
npm install
npm run dev                                  # http://localhost:5173 (proxies /api -> :8000)
npm run test:e2e                             # Playwright end-to-end tests (starts both servers; stop ./dev.sh first)
npm run build:pages                          # static build: the API runs in the browser under Pyodide, no backend
```

## GitHub Pages demo

`.github/workflows/pages.yml` publishes the app as a static site on every push to `main`. There is no server: the same FastAPI app runs in a Web Worker under [Pyodide](https://pyodide.org) (`backend/planner/browser.py`, `frontend/src/backend.ts`), so plans and what-ifs come from the same tested engine.

- The first visit downloads about 10 MB (the Python runtime from the jsDelivr CDN, plus a 1 MB bundle of the engine); later visits use the browser cache.
- PDF transcripts are not supported there (pdfplumber has no Pyodide build). Text and CSV transcripts and the sample work, and are parsed in memory.
- Repository setting: Settings > Pages > Source = GitHub Actions.

## Data

- **Program data:** public CSUSB pages, fetched by `backend/scripts/ingest.py`. It checks robots.txt, waits 2 s between requests, and keeps byte-exact raw copies in `backend/data/raw/`. Sources:
  - catalog course pages (CSE, MATH, PHYS);
  - the BS CS program page;
  - the General Education page;
  - all 12 current CSE-department roadmap PDFs (BS CS for sequence; all 12 for term offerings).
- **Output:** `backend/planner/catalog.json`, with:
  - 67 courses (57 real, 10 GE/free-elective slots) and 76 AND/OR prerequisite edges (grade minimums, corequisites, standing);
  - GE requirements as named slots filled by real catalog courses (89 major + 27 GE + 4 free = 120 units);
  - offerings with a confidence level (20 courses have an `Unknown` offering: 17 on no roadmap, flagged, and 3 entry-level placement assumptions);
  - 12 logged catalog/roadmap discrepancies.
- **Test data:**
  - `planner/students.json`: 6 synthetic students, each with a term-by-term history.
  - `data/sample_transcript.txt`: a synthetic unofficial transcript for the upload demo.
  - `data/all_courses.json`: every subject in the catalog (84 subjects, 4,042 courses), used for tie-out tests and outlier screening; the planner itself uses `catalog.json`.

## Repository layout

The course's recommended `src/`, `tests/`, and `prototype/` are adapted as backend/frontend packages; the dossier folders follow the course layout.

```text
README.md                         Dossier Index (this file)
CHANGELOG.md                      release notes
docs/01-product-requirements/     register, traceability, CH-02 to CH-04, references, tech spec
docs/02-models-architecture/      design.md: models, 4+1 views, ADRs, interface spec; uml-diagrams.md: the five UML views
docs/03-planning-risk/            agile engineering plan, risk register
docs/04-quality-security-testing/ verification strategy, quality and CM plan, threat analysis
docs/05-ai-provenance/            AI Engineering Log
backend/planner/                  models, graph, engine, transcript, api, browser (Pyodide bridge), catalog.json, students.json
backend/scripts/                  ingest, ingest_all, outliers, results, trace, pages_bundle
backend/tests/                    requirement-tagged tests
backend/data/, backend/results/   raw sources and datasets; evaluation outputs
frontend/src/                     React client (App, SVG prerequisite map, logo, in-browser API worker)
frontend/e2e/                     Playwright end-to-end tests
PRODUCT.md, DESIGN.md             product context and design system
dev.sh                            starts API and UI together
csusb-logo.svg                    logo asset
.github/                          CI, PR template, issue forms (change request, bug, backlog)
```
