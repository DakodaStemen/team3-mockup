# Agile Engineering Plan

> [Docs index](../README.md) · [Agile plan](agile-engineering-plan.md) · [Risk register](risk-register.md)

This plan carries the useful parts of a traditional SPMP, per the course dossier guidance ("relevant SPMP elements may appear in the Agile Engineering Plan"). Sections follow Sommerville §23.2.1. The process is Scrum (Ch 3.3), combined with plan-driven milestones, the "sensible mixture" Sommerville recommends for fixed-length projects.

## 1. Objectives and constraints

**Objective:** deliver the Adaptive Degree Pathway Planner defined in SRS v0.1 (see the [requirements register](../01-product-requirements/requirements-register.md) for status).

**Constraints:**

| Constraint | Value | Source |
|---|---|---|
| Duration | Remaining course weeks (currently Week 5 of the course plan) | SRS LIM-01 |
| Team | 5 people | SRS LIM-01 |
| Budget | $0: open-source tools, GitHub public repo | Team decision |
| Data | Synthetic students; public CSUSB program data | COM-03; CH-02 C-2 |
| Starting point | v0.1.0: working prototype on real program data (what-ifs, Summer/Winter catch-up, transcript upload), test suite, dossier structure | [CHANGELOG](../../CHANGELOG.md) |

## 2. Team organization

Names are assigned at the team meeting. Current responsibilities are also listed in the README team table.

| Role | Responsibility | Person |
|---|---|---|
| Product Owner | Prioritizes the backlog; accepts increments; chairs the change control board (CCB) | TBD |
| ScrumMaster | Runs sprint events and stand-ups; owns the risk register | TBD |
| Requirements owner | SRS versions and change log | Dakoda Stemen (per SRS v0.1) |
| Development team (all 5) | Build, test, review, document | All |

**Lanes (SRS §10 allocation).** Each lane has an owner and a backup (risk R-8).

| Lane | Paths | Owner | Backup |
|---|---|---|---|
| Planning engine (audit, graph, scheduler, scenarios) | `backend/planner/engine.py`, `graph.py` | TBD | TBD |
| Data (ingestion, datasets, data rules) | `backend/scripts/ingest.py`, `backend/data/` | TBD | TBD |
| API and web client | `backend/planner/api.py`, `frontend/` | TBD | TBD |
| Quality, release, dossier | `docs/`, `scripts/results.py`, `.github/` | TBD | TBD |

The quality lane runs release testing on work it did not author ([verification strategy §4](../04-quality-security-testing/verification-strategy.md#4-release-testing-83)).

## 3. Risk analysis

See the [risk register](risk-register.md). The ScrumMaster reviews it at each sprint review.

## 4. Resources

| Resource | Need | Notes |
|---|---|---|
| Laptops | One per team member | Any laptop that runs Python and Node |
| Software | Python ≥ 3.12 + uv, Node ≥ 20, Git | Pinned in `uv.lock` and `package-lock.json` |
| Hosting | Private GitHub repo: Issues, Projects, Actions | Free-plan Actions minutes are sufficient |

## 5. Backlog and increments

The **product backlog** is GitHub Issues (label `backlog`, *Backlog item* form). It is seeded from the register rows marked `Not implemented` or `Partial`, from CH-02, and from the SRS open questions. Increments follow the SRS §10 release plan and the course module flow:

| Sprint | Course weeks | Goal | Milestone / deliverable |
|---|---|---|---|
| 1 | 5–6 | SRS v0.1 baseline; team review of CH-02; system models | **SRS v0.1** baselined (snapshot `ADPP_SRS_v0.1_<date>.pdf` in `docs/01-product-requirements/`); models reviewed |
| 2 | 7–8 | MVP gaps: FR-01 group status, FR-16 graduation-by-term, FR-18 advisor view, NFR-06 accessibility; PR-01 usability wireframe test (FR-12 and FR-13 are done) | Increment demo; EV-04/EV-05 interviews |
| 3 | 9–10 | Later-release features: FR-17 third alternative, sign-in and persistence (NFR-01, DR-06); release testing | **Release candidate**; SRS v1.0; final review and oral defense |

**Definition of Done** (course dossier "quality gates"):

- CI green: ruff, pytest (including the traceability check), frontend lint and build, and the Playwright e2e job.
- Every changed requirement is updated in the SRS first, and the register and change log agree.
- Reviewed by a non-author using the PR checklist.
- CHANGELOG updated.
- Significant AI assistance recorded in the [AI Engineering Log](../05-ai-provenance/ai-engineering-log.md).

## 6. Schedule and ceremonies

Two-week sprints:

- **Planning** (day 1): choose backlog items by priority and velocity.
- **Weekly stand-up:** course requirement. Reports artifact *status*, not content; recorded in `docs/03-planning-risk/standups/` once they begin.
- **Sprint review:** demo the increment; review risks.
- **Retrospective:** process changes, recorded alongside the stand-ups.

## 7. Monitoring and reporting

| Mechanism | Frequency | Measure |
|---|---|---|
| Burndown | Continuous | Remaining backlog points (GitHub Project) |
| Velocity | Per sprint | Points completed |
| CI | Every push | ruff, pytest, traceability, build |
| Quality metrics | Per sprint | Open bugs by severity; register rows moving to Implemented; `backend/results/summary.md` |
| Risk review | Per sprint | Risk register probabilities and indicators |

For a serious slip, initiate risk mitigation and re-plan with the Product Owner (Sommerville Fig 23.3).

## 8. Supplementary plans (Sommerville Fig 23.2)

| Plan | Where |
|---|---|
| Configuration management | [quality-and-cm-plan.md §2](../04-quality-security-testing/quality-and-cm-plan.md#2-configuration-management-plan) |
| Quality (SQAP elements) | [quality-and-cm-plan.md §1](../04-quality-security-testing/quality-and-cm-plan.md#1-quality-plan) |
| Validation (STP elements) | [verification-strategy.md](../04-quality-security-testing/verification-strategy.md) |
| Deployment | Local only ([design.md §3](../02-models-architecture/design.md#3-architectural-views-41-sommerville-62), physical view) |
| Maintenance / evolution | ADRs in [design.md](../02-models-architecture/design.md) plus the register's Not-implemented rows |
