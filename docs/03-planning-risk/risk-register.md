# Risk Register

> [Docs index](../README.md) · [Agile plan](agile-engineering-plan.md) · [Risk register](risk-register.md)

Risk management follows Sommerville §22.1: **identify → analyze → plan → monitor**.

**Probability bands:** very low, low, moderate, high, very high.

**Effect bands:**

- **Catastrophic:** threatens the project.
- **Serious:** major delay.
- **Tolerable:** within contingency.
- **Insignificant.**

**Strategy types (§22.1.3):**

- **Avoid:** lower the probability.
- **Minimize:** lower the impact.
- **Contingency:** a plan for when it happens.

The ScrumMaster reviews this register at each sprint review. Change a row whenever its probability or effect changes.

## Register

| ID | Risk | Type | Prob. | Effect | Strategy | Response |
|---|---|---|---|---|---|---|
| R-1 | A real student's records (PII) enter the repo or pipeline | Organizational / legal | Low | Catastrophic | Avoid | COM-03: synthetic profiles only. Ingestion restricted to public pages. Committing transcripts is out of scope; the UI upload (FR-26) is memory-only and its use with real records is undecided (R-15). Every PR is inspected for PII (checklist). |
| R-2 | CSUSB changes the catalog/roadmap page format and ingestion breaks | Technology | Moderate | Serious | Minimize | Raw sources committed. `ingest.py` rebuilds from cache (DR-07 test). Parser tests use real phrasings. Contingency: freeze on the cached 2026-27 data. |
| R-6 | Scope creep beyond the spec's 8 capabilities | Requirements | High | Serious | Avoid | Product Owner and CCB gate changes. SRS v0.1 baseline (Week 5). The register's *Not implemented* rows and the CH-nn proposals. |
| R-7 | Development time underestimated | Estimation | High | Serious | Minimize | A working mock exists before sprint 1. Timeboxed sprints. Defer lower-priority items rather than slip milestones. |
| R-8 | A key team member is unavailable at a critical time | People | Moderate | Serious | Minimize | Owner + backup per area ([agile plan §2](agile-engineering-plan.md#2-team-organization)). Mandatory non-author reviews spread knowledge. Docs are kept current. |
| R-9 | Parsed catalog data is wrong (misread prerequisite), so plans are wrong | Requirements / technology | Moderate | Serious | Minimize | Discrepancy log for advisor review (FR-20). Roadmap audit in results. Parser tests. Validator (FR-14). |
| R-10 | Greedy plans diverge from advisor expectations | Technology | High | Tolerable | Minimize | Measured against the official roadmaps (`results/`). Sprint 2 targets GE spreading. MILP upgrade documented (ADR-04). |
| R-11 | Requirements change from the instructor late in the course | Requirements | Moderate | Serious | Minimize | Traceability matrix for impact analysis (Sommerville Fig 22.5: "derive traceability information to assess requirements change impact"). |
| R-12 | Tooling problems (CI minutes and timeouts, Windows/Linux differences) | Tools | Moderate | Tolerable | Minimize | The prerequisite map is plain SVG (the WebGL library was removed in v0.6) and the term list carries all information. CI runs on Linux; the e2e job has a 20-minute limit and 60 s per test in CI. UTF-8/pathlib everywhere. |
| R-13 | Requirement text drifts between the SRS (Google Doc) and the repo register or tests | Requirements | Moderate | Serious | Avoid | Course "one source of truth": the SRS is authoritative, and the register holds only attributes and status. Change the SRS first (quality-and-cm-plan §2.3). CI fails when tagged tests reference unknown IDs. |
| R-14 | AI-generated content is presented as stakeholder evidence or accepted without review | Organizational (course policy) | High | Serious | Avoid | The [AI Engineering Log](../05-ai-provenance/ai-engineering-log.md) records every significant AI output and its validation. SRS items stay *Proposed* until team review. EV- records distinguish team design inputs from stakeholder evidence. |
| R-15 | A real student transcript is uploaded to the app (FERPA, SRS non-goal, DR-05) | Organizational / legal | Moderate | Serious | Avoid / minimize | Parsed in memory only, never on disk and never logged, capped at 200 profiles and cleared on restart (ADR-15). The team decides CH-04 §C-1 before any demo with a real record. The parser has only seen a synthetic sample. |
| R-16 | Summer and Winter placements are suggested for courses that may not run then | Requirements / data | High | Serious | Minimize | Opt-in only, only courses offered in both regular terms, every placement flagged unconfirmed and listed in "To confirm" (CH-03 §C-1, EV-11). Needs department offering data. |

## Monitoring indicators (Sommerville Fig 22.6)

| Type | Watch for |
|---|---|
| Estimation | Sprint goals missed; backlog not burning down |
| People | Missed standups; reviews waiting > 2 days; one person authoring most commits in an area |
| Requirements | Many CRs per sprint; instructor feedback contradicting the SRS |
| Technology | Ingestion diffs with no catalog change; new unexplained discrepancies |
| Tools | CI failures unrelated to code; e2e timeouts |
| Organizational / legal | Any file resembling a transcript or student ID in a PR |
