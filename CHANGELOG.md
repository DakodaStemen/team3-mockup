# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Versioning: SemVer (docs/QUALITY_AND_CM.md §2.4).

## [0.3.0] - 2026-09-28
### Added
- SE documentation set per Sommerville 10e: SRS (Fig 4.17), DESIGN (models, 4+1 views, ADRs), TEST_PLAN, PROJECT_PLAN (Scrum), RISKS, QUALITY_AND_CM, SECURITY.
- Requirement IDs on every test (`@pytest.mark.req`) and a generated traceability matrix enforced in CI.
- CI workflow; change-request, bug, and backlog issue forms; PR template with inspection checklist.
- Boundary tests (confidence thresholds, unit-load limits), API error tests, audit-line completeness, what-if non-mutation, performance, and ingest-rebuild reproducibility.
- Project lint standard (`ruff` E, F, I, B).
### Removed
- `docs/PLAN.md`: initial build plan, superseded by PROJECT_PLAN.md.

## [0.2.0] - 2026-09-28
### Added
- Real CSUSB 2026-27 catalog, BS CS requirements, and freshman/transfer roadmap ingestion with automatic discrepancy detection.
- Engine support for OR prerequisite groups, corequisites, +/- grade minimums, class standing, and requirement groups.
- Standing-aware recalculation; `validate_plan()`.
- Datasets (students, labeled queries, labeled records) and `scripts/results.py` evaluation.

## [0.1.0] - 2026-09-28
### Added
- Initial mock: deterministic planning engine, Instructor+Ollama guardrail, FastAPI, React UI on hand-seeded data.
