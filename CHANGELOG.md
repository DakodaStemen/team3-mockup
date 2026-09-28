# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Versioning: SemVer (docs/QUALITY_AND_CM.md §2.4).

## [0.5.0] - 2026-09-28
### Fixed
- A Pass event could schedule a course in the same term as its own prerequisite, and the validator missed it because it shared the engine's assumption. The Pass course now stays in its term, and a DAG-based test checks order independently.
- Calibration metrics are reported from out-of-fold predictions (Platt scaling by default; ECE with 5 bins).
- CR/P/TR grades count as C instead of failing (CH-02 C-8, pending advisor confirmation).
- Unit loads outside 3–21 are rejected on every path (`/plan`, `/scenario`, plain language). A cap below a course's units gets one clear message.
- A prerequisite with no catalog alternative is logged instead of returning a 500.
- Pass explanations no longer claim courses were re-sequenced, and only moved courses are marked affected.
### Added
- Scenario results include `moved` (course, from, to) (FR-12). Unplaceable plans name each blocking course and its constraint (FR-13).
- `GET /health` reports whether the LLM parser is reachable.
- UI: click-to-load courses, plan history with undo/reset, base unit-cap picker, AI parser status, a moved-course list, a department-confirmation panel, bottleneck table, faded off-plan DAG nodes, phone layout.
- `./dev.sh` one-command start; Playwright end-to-end tests (`npm run test:e2e`), also run in CI.
### Changed
- The results summary labels the bottleneck correlation a consistency check, not validation.

## [0.4.0] - 2026-09-28
### Added
- Term offerings from all 12 CSE-department roadmaps, with confidence (high/low/unknown) and per-term warnings.
- General Education modeled from the catalog GE page. Named area slots are filled by real courses at the C- minimum. The major total now reconciles: 89 + 27 GE + 4 free = 120.
- Supporting prerequisites: choosing CSE 4030 or 5300 schedules CSE 3350. CSE 5208 and 5408 are electable.
- Summer placements flagged as unconfirmed.
### Fixed
- Spring-only CSE 5500 was planned in Fall (no offering data).
- Default electives overshot to 14 units; they now total exactly 12 and prefer the roadmap's 3-unit slots.
- Pathway-quality scorer compares GE slots by roadmap slot kind.

## [0.3.0] - 2026-09-28
### Added
- Engineering Dossier structure per CSE 6550 (README is the Dossier Index; `docs/01`–`05` folders).
- Requirement attribute register keyed to the team SRS v0.1; the SRS change proposal CH-02; references; AI Engineering Log.
- Design (models, 4+1 views, ADRs, interface spec), verification strategy, agile engineering plan, risk register, quality/CM plan, and threat analysis, following Sommerville 10e.
- Requirement-tagged tests (`@pytest.mark.req`, strict markers) and a generated traceability matrix enforced in CI.
- `POST /validate` (FR-14). `POST /plan` now returns 422 naming unplaceable courses (FR-13, partial). Planning-aid notice in the UI (NFR-10). Affected courses labeled in text, not only color.
- CI workflow; change-request, bug, and backlog issue forms; PR template with the inspection checklist; ruff lint standard.
### Removed
- `docs/PLAN.md` (superseded) and a draft `docs/SRS.md` that duplicated SRS v0.1 with conflicting IDs (see AI Engineering Log AIL-04).

## [0.2.0] - 2026-09-28
### Added
- Real CSUSB 2026-27 catalog, BS CS requirements, and freshman/transfer roadmap ingestion with automatic discrepancy detection.
- Engine support for OR prerequisite groups, corequisites, +/- grade minimums, class standing, and requirement groups.
- Standing-aware recalculation; `validate_plan()`.
- Datasets (students, labeled queries, labeled records) and `scripts/results.py` evaluation.

## [0.1.0] - 2026-09-28
### Added
- Initial mock: deterministic planning engine, Instructor+Ollama guardrail, FastAPI, React UI on hand-seeded data.
