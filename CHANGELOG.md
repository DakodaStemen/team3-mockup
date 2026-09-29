# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Versioning: SemVer (docs/QUALITY_AND_CM.md §2.4).

## [Unreleased]
### Added
- All-subject catalog: `scripts/ingest_all.py` reads every subject in the catalog A-Z (84 subjects, 4,042 courses) into `data/all_courses.json`; `scripts/outliers.py` screens it (units, dangling prerequisites, corequisite pairs vs real loops) into `results/outliers.json`.
- Exhaustive term sweep (`tests/test_term_sweep.py`, 3,715 Fail/Withdraw/Pass scenarios, with and without each Summer/Winter opted in) and tie-out tests between the full dataset and the planner catalog.
### Changed
- Unit limits re-read from the Registrar: fall/spring maximum 18 (above needs an approved overload, now flagged), summer 14 and winter 4. Summer and winter are short terms, so the engine now plans a summer to 7 units (one session) and winter to 4; the validator still accepts up to the published maximum.
- Plan view is quieter: the "if failed" badge shows only for delays of two or more terms (shown as `+2`), "Protect these" lists the top three, the legend is trimmed to what needs explaining, and the duplicate unit-cap stat is gone. Every value is still in the bottleneck table.
### Fixed
- A course whose catalog text mentions itself ("may be taken concurrently with COMM 3101") was parsed as its own prerequisite; it is now a note.
- Not fixable here: 95 dangling prerequisites and one ESPE loop are in the published catalog itself.

## [0.7.0] - 2026-09-28
### Added
- Past terms: each student's history (every attempt by term, including D/F/W and retakes) shows before the plan, marked Completed or In progress with grades (DR-04). The map shows them as columns.
- Transcript upload: PDF, text, or CSV unofficial transcripts become a temporary profile with history, transfer credit, and in-progress courses; unreadable lines and courses outside the catalog are reported; nothing is stored (CH-04 FR-26). A synthetic sample transcript is one click away.
- Measured bottlenecks: for every planned course, the delay if it's failed and the summer/winter catch-up, shown as a "Protect these" strip, per-course badges, and bottleneck-table columns (FR-25).
- Major electives in CSUSB green; general education in violet with a "Gen Ed" tag; Fall-only and Spring-only courses carry an amber calendar badge (and a dot on the map).
- Layout: one Plan section with a Terms / Prerequisite map switch; terms in academic-year rows; scheduling notes folded; alternatives and undo beside the stats; sticky what-if sidebar.
- Seeded fuzz test over every event type, student, and the sample transcript.
### Fixed
- A passed lab (or lecture) could be split from its partner when later terms were rebuilt; a failed lab after a passed lecture now retakes the lab alone.
- Transcript titles ending in a Roman numeral ("Calculus I") were read as an Incomplete grade.
- Summer cap is the Registrar's 14 units (was an assumed 8).

## [0.6.0] - 2026-09-28
### Added
- Winter intersession: an `Add Winter` what-if places a January term between Fall and Spring, capped at the Registrar's 4 units, with every placement flagged unconfirmed (CH-03 FR-22). Summer cap corrected from an assumed 8 to the published 14.
- Catch-up search: when a what-if delays graduation, the engine proposes the fewest opt-in Summer/Winter terms that win the time back, returned as `recovery` and previewable in the UI. The alternatives gain "with summer & winter" (FR-24). On current data it fully recovers 128 of 160 delayed Fail/Withdraw runs.
- UI redesign modeled on csusb.edu: two-tone CSUSB logo (also the tab icon), blue title banner, sticky section nav, gray sidebar boxes; light by default with a remembered dark toggle.
- Prerequisite map rebuilt as SVG on the plan's timeline: one column per term, long edges routed through lanes, ghosts where moved courses were, hover to trace a chain. Replaces reagraph.
- `PRODUCT.md` and `DESIGN.md`.
### Fixed
- A lab could be scheduled a term after its lecture (PHYS 2500L after PHYS 2500). Labs now always share their lecture's term, move with it, and the validator flags a split (FR-23).

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
### Security
- `ingest.py` fetches only HTTPS CSUSB hosts, follows at most 5 redirects and checks each hop, caps downloads at 20 MB, reads robots.txt with our User-Agent and a timeout, and writes cache files atomically.
- CI runs with read-only `permissions`, pins third-party actions to commit SHAs, and runs `npm audit` plus lint.
### Fixed (tooling)
- Ingest parsers fail with a clear "source layout changed" message instead of an `AttributeError`/`IndexError` when a page changes shape.
- `results.py` tolerates empty samples and constant data (n/a instead of a crash). `calibrate.py` requires at least 4 examples of each class and says so, instead of a scikit-learn error.
- `dev.sh` checks the Node version and busy ports, reinstalls when the lockfile changes, and shuts both servers down cleanly.
- `numpy` is declared as a direct dependency.

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
