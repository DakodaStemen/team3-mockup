# Project Plan

Sections follow Sommerville §23.2.1. The process is Scrum (Ch 3.3) with a plan-driven outline: Sommerville recommends "a sensible mixture of plan-based and agile development" for a fixed-length course project.

## 1. Introduction

**Objective:** deliver the Adaptive Degree Pathway Planner prototype defined in [SRS.md](SRS.md). It must show three things:
- The end-to-end pipeline works.
- All 8 required capabilities are present.
- The guardrails are visible and defensible.

**Constraints:**

| Constraint | Value |
|---|---|
| Duration | 10-week course (CSE 6550); 5 two-week sprints |
| Team | 5 people |
| Budget | $0: open-source tools, self-hosted LLM, GitHub Free (private repo) |
| Data | Public CSUSB catalog and roadmaps only; synthetic students (NFR-6) |
| Starting point | v0.3: working mock, real data ingested, SE documentation baseline (this document set) |

## 2. Project organization

Scrum roles (Sommerville Fig 3.8). Names are assigned at team kickoff.

| Role | Responsibility | Person |
|---|---|---|
| Product Owner | Owns and prioritizes the backlog; accepts increments; chairs the change control board (CCB) | TBD |
| ScrumMaster | Runs the process (planning, review, retro); removes blockers; owns the risk register | TBD |
| Development team (all 5) | Build, test, review, document | All |

**Component ownership.** Every area has an owner and a backup, so no single person is a bottleneck (RISKS R-8):

| Area | Paths | Owner | Backup |
|---|---|---|---|
| Planning engine and graph | `backend/planner/engine.py`, `graph.py` | TBD | TBD |
| Data ingestion and datasets | `backend/scripts/ingest.py`, `backend/data/` | TBD | TBD |
| Guardrail, LLM, calibration | `backend/planner/guardrail.py`, `scripts/calibrate.py` | TBD | TBD |
| API and frontend | `backend/planner/api.py`, `frontend/` | TBD | TBD |
| QA, release, docs | `docs/`, `scripts/results.py`, `.github/` | TBD | TBD |

The QA owner runs release testing for features they did not write (TEST_PLAN §4).

## 3. Risk analysis

See [RISKS.md](RISKS.md). The ScrumMaster reviews it at every sprint review.

## 4. Hardware and software resources

| Resource | Need | Notes |
|---|---|---|
| Developer machines | 5 laptops; ≥ 16 GB RAM on at least one for Ollama `llama3.1` 8B (~4.7 GB) | Other machines work without the LLM (NFR-4) |
| Software | Python ≥ 3.12 + uv; Node ≥ 20; Git; Ollama (optional) | Versions pinned in `uv.lock` and `package-lock.json` |
| Hosting | GitHub private repo, Issues, Projects, Actions | Free plan: ~2,000 Actions minutes/month on private repos |

## 5. Work breakdown

The product backlog lives in **GitHub Issues** (label `backlog`). Each issue is a user story or task with acceptance criteria and the SRS IDs it touches. Sprint goals:

| Sprint | Weeks | Goal (increment) | Key backlog items | Milestone / deliverable |
|---|---|---|---|---|
| 1 | 1–2 | Team onboarding; requirements review | Assign roles and owners; SRS review (TEST_PLAN §1); run calibration on one machine | **M1:** SRS v1.0 approved (the change-control baseline) |
| 2 | 3–4 | Plan quality | Spread GE slots like the roadmap; raise roadmap-match metrics | **M2:** results v2 showing better P@term |
| 3 | 5–6 | Guardrail maturity | Calibrated thresholds (NFR-5); intake `MalformedRecordCheck` using `labeled_records.json` | **M3:** calibration report with ECE |
| 4 | 7–8 | UX and usability | UI polish; usability sessions (NFR-11) | **M4:** release candidate `v0.9.0`; release test record |
| 5 | 9–10 | Hardening and delivery | Fix release-test findings; final results; demo script | **M5:** `v1.0.0`; final presentation |

Each item's inputs and outputs are recorded on its issue. The **Definition of Done** for any item:
- CI green: ruff, pytest, traceability, tsc.
- Reviewed by a non-author.
- Docs and CHANGELOG updated.
- Any SRS change went through a CR.

## 6. Project schedule

Two-week sprints. Each sprint has these ceremonies:
- **Sprint planning** (day 1): choose items by priority and velocity.
- **Daily scrum:** async, in the team channel.
- **Sprint review** (last day): demo the increment to the Product Owner; review risks.
- **Retrospective:** process changes, recorded in the sprint's GitHub milestone description.

Milestones M1–M5 above are the progress checkpoints (Sommerville §23.2.2).

## 7. Monitoring and reporting

| Mechanism | Frequency | Measure |
|---|---|---|
| Sprint burndown | Daily | Remaining backlog points (GitHub Project) |
| Velocity | Per sprint | Points completed; used to plan the next sprint |
| CI health | Every push | ruff, pytest (incl. traceability), frontend build |
| Quality metrics | Per sprint | Open bugs by severity; traceability gaps (target 0); `results/summary.md` metrics |
| Risk review | Per sprint | RISKS.md probabilities, effects, indicators |

If there are serious problems (a milestone at risk), the team initiates risk mitigation and re-plans with the Product Owner (Sommerville Fig 23.3).

## Supplementary plans (Sommerville Fig 23.2)

| Plan | Where |
|---|---|
| Configuration management plan | [QUALITY_AND_CM.md §2](QUALITY_AND_CM.md#2-configuration-management-plan) |
| Quality plan | [QUALITY_AND_CM.md §1](QUALITY_AND_CM.md#1-quality-plan) |
| Validation plan | [TEST_PLAN.md](TEST_PLAN.md) |
| Deployment plan | Local only (DESIGN §3, physical view). No production deployment in scope. |
| Maintenance plan | SRS §8 (system evolution); DESIGN ADRs |
