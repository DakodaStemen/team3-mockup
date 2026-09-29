# AI Engineering Log

> [Docs index](../README.md) · [AI Engineering Log](ai-engineering-log.md)

This is the AI Assistance and Provenance record required by course policy (SRS COM-02; Engineering Dossier area 5). Course rule: *AI-generated content is not automatically project evidence; the team must verify important outputs.* Entries are append-only. Correct a mistake by adding an entry, not by editing an old one.

## Summary record (SRS §13 form)

| Provenance item | Record |
|---|---|
| Tools and versions | Claude (Anthropic) `claude-opus-5-5`, in the Claude app (SRS draft) and in Claude Code CLI (repository work) |
| Dates and contributors | 2026-09-27 and 2026-09-28; used by Dakoda Stemen. Other members: add your own entries. |
| Assistance provided | SRS v0.1 draft; prototype code (engine, guardrail, API, UI); data ingestion; test suite; evaluation scripts; dossier documents in `docs/`; code and security reviews |
| Inputs and sensitive data | Project 3 brief; the team's technical spec; course pages and templates (Drive); Sommerville 10e (local PDF, for chapter structure); public CSUSB catalog and roadmap pages. **No student records, credentials, or restricted data** were provided (COM-03). Student profiles are synthetic and were written by the AI. |
| Human decisions | See each entry's *Decisions* field |
| Validation performed | Automated tests (49), independent review passes, comparison against team research (EV-09) and the official roadmaps. See each entry. |
| Known limitations | Listed per entry and under *Open items needing human verification* below |

**Responsibility statement.** The team owns, and must be able to explain and defend, every artifact in this repository, whether or not AI assistance was used.

## Entries

### AIL-01: SRS v0.1 draft (2026-09-27)

- **Tool:** Claude app.
- **Output:** the SRS v0.1 Google Doc, drafted in the course template.
- **Decisions:** the stack (LIM-05), roles, and MVP focus were made by the team before AI use.
- **Validation:** pending team review (all requirements are *Proposed*). Recorded in SRS §13.

### AIL-02: Prototype v0.1 (2026-09-28)

- **Tool:** Claude Code.
- **Output:** planning engine, guardrail (Instructor + Ollama), FastAPI service, React UI, tests. Tag `v0.1.0`.
- **Decisions (human):** private GitHub repo; build a working mock rather than a skeleton; self-hosted Ollama as the LLM.
- **Validation:** 15 automated tests; headless-browser screenshot of the UI.
- **Rejected or corrected:**
  - **The AI's hand-seeded course catalog was materially wrong.** For example, it had CSE 2130 as "Discrete Structures" (actually Machine Organization) and CSE 5700/5720 as capstones (actually Compilers and Database Systems). It was discarded and replaced by ingested data in AIL-03.
  - The DAG view initially crashed (single-root layout); fixed.
  - An AI scripted edit truncated `engine.py`; caught immediately and rewritten.

### AIL-03: Real data ingestion and evaluation (2026-09-28)

- **Output:** `scripts/ingest.py` (catalog, program, and roadmap parsing); engine support for OR groups, corequisites, +/- grades, and standing; datasets (synthetic students, 45 labeled queries, 80 labeled records); `scripts/results.py`. Tag `v0.2.0`.
- **Decisions (human):** ingest all data needed for tests and results.
- **Validation:**
  - The ingester's discrepancy log independently reproduces every BS CS finding in the team's research doc (EV-09).
  - Both official roadmaps pass the engine's validator.
  - 282/282 scenario runs are valid.
  - Parser tests use real catalog phrasing.
- **Defects found by tests and fixed:**
  - Subject codes weren't carried across "and" (`PHYS 2000 and 2000L`).
  - Recalculation ignored class standing (CSE 4880).
  - A false roadmap violation came from uncounted GE slot units.
- **Known limitations:** upper-division GE is assumed to need 60 units; summer cap 8; the elective default rule; `Unknown` offerings for non-roadmap courses. See the register and CH-02.

### AIL-04: SE process documentation (2026-09-28)

- **Output:** design (models, 4+1 views, ADRs), verification strategy, agile plan, risk register, quality/CM plan, threat analysis, CI, issue and PR templates, requirement-tagged tests with generated traceability.
- **Decisions (human):** follow Sommerville 10e for SE protocols and documentation; run a full audit using the available tools.
- **Validation:**
  - Automated code review: 9 findings, all fixed (e.g. the traceability tool missed tests with multi-line decorators; CRLF breaking the CI comparison; a timing-sensitive test).
  - Security review: no findings.
  - Audit against the course's Engineering Dossier pages and SRS template.
- **Rejected or corrected:** **the AI first wrote its own `docs/SRS.md`, which duplicated the team's SRS v0.1 with different, conflicting requirement IDs.** That violates the course's one-source-of-truth rule. It was retired:
  - The useful content became the [CH-02 change proposal](../01-product-requirements/srs-change-proposal-CH-02.md).
  - Tests were re-keyed to SRS v0.1 IDs.
  - Docs were moved into the course's `docs/01…05` structure.
- **Known limitations:** EV-04 (advisor) and EV-05 (students) are still planned. No stakeholder has validated any requirement yet.

### AIL-05: Correction to reported bottleneck correlation (2026-09-28)

- **What was wrong:** AIL-03's results used a hand-written Spearman correlation that did not average tied ranks. Many courses have betweenness 0, so the reported values (priority 0.54, betweenness 0.04) were wrong.
- **Fix:** replaced with `statistics.correlation(..., method="ranked")`, found by the over-engineering audit.
- **Corrected values:** see the Bottlenecks section of `backend/results/summary.md`, which `scripts/results.py` regenerates; numbers are not restated here so they cannot drift. The priority score still ranks highest, but the gap is smaller than first reported, and the summary explains why that comparison is a consistency check rather than validation (delay is measured by the same engine; betweenness is 0 for courses with no prerequisites).
- **Lesson:** hand-rolled statistics need a check against a reference implementation.

### AIL-06: Data gap fixes (2026-09-28)

- **Decisions (human):** Dakoda asked whether the data was of proper quality and complete, then approved fixing all the gaps.
- **Output:**
  - Term offerings from all 12 CSE roadmaps, with a confidence level.
  - GE modeled as named catalog areas that real courses fill (C- minimum).
  - CSE 3350 as a supporting prerequisite, making CSE 4030 and 5300 electable.
  - Summer placements flagged unconfirmed.
  - Default electives fill exactly 12 units.
- **Validation:**
  - The derived Fall-only/Spring-only lists match the team's independent research (EV-09) for all 16 BS CS courses. A test pins this.
  - 55 tests pass; 280/280 scenario runs are valid; both roadmaps pass the catalog audit.
- **Defects found and fixed:**
  - Before the fix, the planner put Spring-only CSE 5500 in a Fall term.
  - The first elective fill overshot to 14 units and chose Computer Engineering design courses for a CS student. Fixed with an exact-sum search that prefers the roadmap's 3-unit slot size.
  - The results scorer compared renamed GE slots incorrectly. Fixed.
- **Known limitations:**
  - The GE slot mapping (which 5 lower-division areas) is inferred from the roadmap slot count and program exemptions. Verify with an advisor.
  - 17 courses have no public offering data.
  - Summer has no data at all.

## Open items needing human verification

1. **Team review of CH-02.** Accept or reject each proposed requirement, and decide conflicts C-1 through C-6.
2. **Assumptions stated by the AI, not by evidence:** UD GE = 60 units; summer cap 8; full-time = 12 units; the elective default rule; the BS CS GE slot mapping (CH-02 C-7).
3. **References marked "not opened" or "not verified"** in [references.md](../01-product-requirements/references.md), especially the legal basis for scraping (CollegeSource v. AcademyOne).
4. **Synthetic student profiles** (`backend/planner/students.json`): confirm they are realistic with an advisor (EV-04).
5. **Guardrail thresholds 0.90 / 0.60:** unvalidated until the calibration run (NFR-13).

### AIL-07: Review fixes and demo-ready UI (2026-09-28)

- **Decisions (human):** Dakoda wrote the fix plan (*ADPP Mockup: Fix Plan and Demo Prep*), then asked for every finding to be fixed and the UI made ready to explore.
- **Output:**
  - The Pass-ordering fix and the independent DAG-order test.
  - Out-of-fold calibration metrics.
  - Unit-load bounds on every path; credit grades (CR/P/TR) count as C.
  - `moved` diff (FR-12) and per-course blocking reasons (FR-13).
  - `/health`, the UI rework, `dev.sh`, and Playwright e2e tests.
- **Deviations from the plan, with reasons:**
  - The unit-load bound lives in the engine, not on `ScenarioEvent`: a model bound would turn an out-of-range LLM answer into a parse failure that trips the circuit breaker.
  - The entry-course count in the summary is computed from the graph: 6 real courses, not 16. The 16 included 10 GE slots.
  - A passed course's units were double-counted toward standing after the Fix 1 patch. Fixed; only within-term order changed.
- **Validation:** 74 backend tests, 8 e2e tests, and 280/280 valid scenario runs. The new regression tests failed on the old code.
- **Needs a human decision:** CH-02 C-8 (credit-grade equivalence) and C-9 (the rationale for incremental recalculation).

### AIL-08: Parallel bug, outlier, and security sweep (2026-09-28)

- **Decisions (human):** Dakoda asked for a full sweep for outliers, bugs, and security flaws, fixed in parallel.
- **Method:** four AI agents with disjoint file ownership. Engine: fuzzing across students, chained events, caps, and random profiles. API: security review. Frontend: Playwright-driven review. Scripts/deps/CI/docs: review plus pip-audit and npm audit. The coordinating agent reviewed each diff, fixed two gaps itself (Content-Length parsing, CI server reuse), regenerated the matrix and results, and ran every suite.
- **Output:** per-term unit caps; credit revocation on retakes; strict API input models; LLM output validated like typed input; audit, calibration, and breaker hardening; stale-response and stale-form fixes in the UI; WCAG AA contrast; hardened ingest and CI.
- **Validation:** 135 backend tests, 16 e2e tests, 280/280 valid scenario runs, fuzz harness with 0 over-cap or validator problems. New regression tests failed before their fixes.
- **Known limitations:** no authentication, and `/audit` is readable by any client; audit log has no retention policy (fine for synthetic students, not for real records); body-size limit relies on Content-Length; circuit breaker is per process.

### AIL-09: UI redesign, winter terms, lab pairing, and catch-up search (2026-09-28)

- **Decisions (human):** Dakoda asked for a better DAG and UI, then pinned "modern and minimal, matching the CSUSB site", supplied the CSUSB logo, and asked for light-by-default with a dark toggle. Dakoda identified missing summer/winter logic, the lab scheduled after its lecture, and asked for summer/winter to be used to catch up after setbacks.
- **Method:** AI built the UI with the Impeccable design skill (direction roll, then the user's pinned theme), a separate finish-review agent (two fix rounds), and a documenter agent for DESIGN.md. Engine changes were made directly and verified with new requirement-tagged tests and the results sweep.
- **Output:** CH-03 (FR-22, FR-23, FR-24); `Add Winter`; `Catalog.lab_for`; `recover()`; SVG prerequisite map; csusb.edu-style layout.
- **Validation:** 154 backend tests, 19 e2e tests, 285/285 valid scenario runs; 128/128 recovered plans valid.
- **Known limitations:** which courses run in summer/winter is an assumption, not evidence (CH-03 §C-1). The caps were first assumed (summer 8) and then corrected to the Registrar's published limits (summer 14, winter 4) after a research agent verified them. `recover()` is greedy with pair lookahead. Figtree substitutes for the licensed Proxima Nova and loads from Google Fonts. The CSUSB logo is used at the team's request in a planning aid that says it is not official.

### AIL-10: Layout, history, measured risk, transcript upload, fuzzing (2026-09-28)

- **Decisions (human):** Dakoda asked for a tidier layout, past terms for students with history, bottlenecks surfaced and used, electives in a distinct color, a transcript upload with parsing, and the math "fully wired in including edge cases".
- **Method:** layout via the Impeccable layout playbook. A research agent verified CSUSB session limits and public schedule sources. Synthetic histories generated with the engine's own placement. The parser was built against a synthetic transcript. A seeded fuzz test chains random events across all profiles.
- **Output:** CH-04 (DR-04 revised, FR-25, FR-26); `course_risk()`, `/risk`; `planner/transcript.py`, `/transcript`; `StudentProfile.history`; lab/lecture pinning on rebuild.
- **Validation:** 221 backend tests (fuzz: 54 random chains, all invariants hold), 22 e2e tests. The fuzz test found the lab-pinning bug; a parser test found the "Calculus I" grade bug. Both are fixed.
- **Known limitations:** the parser has never seen a real CSUSB unofficial transcript. Uploading a real record conflicts with SRS non-goals and DR-05 until the team decides (CH-04 §C-1). Risk is measured by failing one course at a time, not combinations.

### AIL-11: Documentation and diagram audit (2026-09-29)

- **Decisions (human):** Dakoda asked for all documentation and diagrams to be checked against the current code, and supplied the team roster.
- **Method:** AI read `engine.py`, `api.py`, `models.py`, `graph.py`, `guardrail.py`, the CI workflow, and the UI's state handling, then compared each claim in the docs and diagrams with them. It ran the backend tests and recounted the catalog.
- **Output:** the UML set (`uml-diagrams.md`); `design.md` brought up to date (ADR-12..15, API table, sequence and class diagrams, component specs); README, PRODUCT, threat analysis, risk register (R-15, R-16), verification strategy, quality and CM plan, agile plan, CH-02 note, and the team table corrected.
- **Validation:** 234 backend tests passed before the removal below. The diagrams have not been rendered; the Mermaid and PlantUML syntax is unchecked.
- **LLM removal (human decision):** Dakoda asked for the demo build to run without the LLM. AI removed the guardrail module, `/query`, `/audit`, calibration, the UI's question box, AI status chip, and audit tab, the four LLM requirements, and the related docs on branch `feat/remove-llm`. After it: 199 backend tests and 21 e2e tests pass, lint and build are clean. Earlier log entries are left as written because they record what happened. The pre-removal state is tagged `with-llm`.
- **Known limitations:** the AI's first UML draft was wrong in several places (event names, a `validate_plan` call that `apply_scenario` never makes, HTTP status codes); the audit corrected them. Unreleased CHANGELOG items (all-subject catalog) are described from the CHANGELOG and file contents, not from a code read.
