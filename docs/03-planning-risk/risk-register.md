# Risk Register

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
| R-1 | A real student's records (PII) enter the repo or pipeline | Organizational / legal | Low | Catastrophic | Avoid | COM-03: synthetic profiles only. Ingestion restricted to public pages. Transcript upload is out of scope. Every PR is inspected for PII (checklist). |
| R-2 | CSUSB changes the catalog/roadmap page format and ingestion breaks | Technology | Moderate | Serious | Minimize | Raw sources committed. `ingest.py` rebuilds from cache (DR-07 test). Parser tests use real phrasings. Contingency: freeze on the cached 2026-27 data. |
| R-3 | No team machine can run the local LLM, so calibration never runs | Tools | High | Serious | Minimize / contingency | Deterministic features never depend on the LLM (NFR-12). Calibrate on one capable machine. Contingency: a rule-based parser behind the same Pydantic schema. |
| R-4 | LLM misparses or hallucinates a scenario and the student acts on it | Technology | High | Serious | Avoid | Typed output, deterministic validation, and thresholds (FR-19). Audit log (FR-21). Every result is a preview the student must *Keep* (FR-15). |
| R-5 | Prompt injection through the query box | Technology (security) | Moderate | Serious | Avoid | The LLM has no tools and no write path; its output is only a typed event, validated before use. There's an injection case in `queries.json`. See [threat-analysis.md](../04-quality-security-testing/threat-analysis.md). |
| R-6 | Scope creep beyond the spec's 8 capabilities | Requirements | High | Serious | Avoid | Product Owner and CCB gate changes. SRS v0.1 baseline (Week 5). "Deferred" list in the README. |
| R-7 | Development time underestimated | Estimation | High | Serious | Minimize | A working mock exists before sprint 1. Timeboxed sprints. Defer lower-priority items rather than slip milestones. |
| R-8 | A key team member is unavailable at a critical time | People | Moderate | Serious | Minimize | Owner + backup per area (PROJECT_PLAN §2). Mandatory non-author reviews spread knowledge. Docs are kept current. |
| R-9 | Parsed catalog data is wrong (misread prerequisite), so plans are wrong | Requirements / technology | Moderate | Serious | Minimize | Discrepancy log for advisor review (FR-20). Roadmap audit in results. Parser tests. Validator (FR-14). |
| R-10 | Greedy plans diverge from advisor expectations | Technology | High | Tolerable | Minimize | Measured against the official roadmaps (`results/`). Sprint 2 targets GE spreading. MILP upgrade documented (ADR-04). |
| R-11 | Requirements change from the instructor late in the course | Requirements | Moderate | Serious | Minimize | Traceability matrix for impact analysis (Sommerville Fig 22.5: "derive traceability information to assess requirements change impact"). |
| R-12 | Tooling problems (WebGL graph, CI minutes, Windows/Linux differences) | Tools | Moderate | Tolerable | Minimize | The graph is non-essential (the term list carries all information). CI runs on Linux. UTF-8/pathlib everywhere. |
| R-13 | Requirement text drifts between the SRS (Google Doc) and the repo register or tests | Requirements | Moderate | Serious | Avoid | Course "one source of truth": the SRS is authoritative, and the register holds only attributes and status. Change the SRS first (quality-and-cm-plan §2.3). CI fails when tagged tests reference unknown IDs. |
| R-14 | AI-generated content is presented as stakeholder evidence or accepted without review | Organizational (course policy) | High | Serious | Avoid | The [AI Engineering Log](../05-ai-provenance/ai-engineering-log.md) records every significant AI output and its validation. SRS items stay *Proposed* until team review. EV- records distinguish team design inputs from stakeholder evidence. |

## Monitoring indicators (Sommerville Fig 22.6)

| Type | Watch for |
|---|---|
| Estimation | Sprint goals missed; backlog not burning down |
| People | Missed standups; reviews waiting > 2 days; one person authoring most commits in an area |
| Requirements | Many CRs per sprint; instructor feedback contradicting the SRS |
| Technology | Ingestion diffs with no catalog change; new unexplained discrepancies; escalation rate rising |
| Tools | CI failures unrelated to code; LLM timeouts in `audit.jsonl` |
| Organizational / legal | Any file resembling a transcript or student ID in a PR |
