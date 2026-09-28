# SRS change proposal CH-02 (for SRS v0.2)

| Field | Entry |
|---|---|
| Change ID | CH-02 (continues SRS v0.1 Appendix A) |
| Requested by | Dakoda Stemen (AI-assisted draft; see [AI Engineering Log](../05-ai-provenance/ai-engineering-log.md)) |
| Date | 2026-09-28 |
| Affected baseline | SRS v0.1: [TeamName_AdaptiveDegreePathwayPlanner_SRS_v0_1](https://docs.google.com/document/d/1h-cgCt8wF0NcHRoyRzOdYJiq81ip6GJhvYBi4g2LHtY/edit) |
| Status | **Proposed.** Pending team review. The CCB decision is recorded in SRS Appendix A. |

**Why this change.** A working prototype and real CSUSB data now exist in this repository. That produced new evidence, answers to some open questions, and features beyond the v0.1 baseline. Per the course dossier rules ("one source of truth"), those findings are proposed here as SRS changes instead of living in a second requirements document.

Nothing below is approved until the team accepts it. Each item keeps stable IDs, following the numbering in the SRS.

## A. Evidence register updates (SRS §5.2)

| ID | Evidence record | Date and owner | Contribution | Proposed status |
|---|---|---|---|---|
| EV-02 | Published CSUSB 2026-27 catalog (CSE, MATH, PHYS course pages; BS CS program page) and BS CS freshman and transfer roadmaps. Ingested by `backend/scripts/ingest.py`; raw copies in `backend/data/raw/`. | 2026-09-28; Dakoda Stemen | Real units, prerequisites, grade minimums, corequisites, standing, requirement groups, and term offerings (roadmap courses only) | Planned → **Confirmed** |
| EV-07 | Scheduler feasibility spike: `backend/scripts/results.py` → `backend/results/summary.md` | 2026-09-28; Dakoda Stemen | Greedy scheduler: 282/282 valid scenario runs, ~1 ms per plan. Graduation term matches both roadmaps; ~0.5 exact-term match per course. Not yet compared to an exhaustive optimum (PR-02 criterion). | Planned → **Provisional** |
| EV-08 *(new)* | Adaptive Degree Pathway Planner Technical Spec v0.1 ([docx](ADPP_TechnicalSpec_v0.1_2026-09-28.docx)) | 2026-09-28; Dakoda Stemen | Architecture, AI-grounding ADR, guardrail design, measurement plan, prior art | **Confirmed** (team-authored design input, not stakeholder evidence) |
| EV-09 *(new)* | "Course Offering & Roadmap Data – Team Findings" and "Data Schema Ideas" (team Drive) | 2026-09-24/25; team | Once-a-year courses, catalog/roadmap conflicts, source-of-truth split, grouped prerequisites | **Confirmed** |
| EV-10 *(new)* | Automated catalog-vs-roadmap discrepancy log (`catalog.json` → `discrepancies`) | 2026-09-28; Dakoda Stemen | 11 conflicts reproduced from source, including every EV-09 finding for BS CS | **Confirmed** |

## B. Open questions answered by EV-02

| OQ | Proposed answer | Evidence | Remaining uncertainty |
|---|---|---|---|
| OQ-01 minimum grade | **Per prerequisite, as stated in the catalog.** Examples: CSE 2010 "C or better" for CSE 2020; MATH 2210 "C- or better" for MATH 2220/2310. Where the catalog states none, any passing grade (D- or better) is assumed. | EV-02 | Confirm the default with an advisor (EV-04) |
| OQ-02 corequisites | **Yes.** The catalog has "Semester Corequisite" and "pre- or co-requisite" (e.g. PHYS 2500L with PHYS 2500; MATH 2220 for MATH 2310). Modeled as a prerequisite satisfiable in the same term. | EV-02 | None for BS CS |
| OQ-04 unit load | Still open. Roadmap semesters run 14–18 units; there is no catalog rule. Prototype defaults: profile preference; summer cap 8. | EV-02 | Academic regulations (EV-03) |
| OQ-07 elective fill | Proposed default: already-completed first, then fewest prerequisites, then known offering, then course number. Student choices override. | Prototype | Advisor review |

## C. Conflicts between SRS v0.1 and current evidence or implementation (need a team decision)

| # | Conflict | Options | Recommendation |
|---|---|---|---|
| C-1 | **DR-03** says reject the whole load on a prerequisite cycle. The tech spec (EV-08) and the implementation reject only the cyclic *edge*, log it, and continue. | (a) Keep DR-03 and change the code. (b) Revise DR-03 to "reject the offending record, report it, and continue." | (b): one bad edge shouldn't block planning for a whole program, and it's still reported for advisor review |
| C-2 | **DR-05 / LIM-02** say only synthetic data. The catalog and roadmaps are real *public* data (not restricted), while student records remain synthetic. | Revise LIM-02 and DR-05 to "student data shall be synthetic; program data may be public institutional data." | Revise. EV-06 restricts protected student data, not public catalogs. |
| C-3 | **FR-02 / AS-02** say in-progress courses do not satisfy prerequisites. The planner assumes they pass when planning *later* terms (otherwise no future plan is possible mid-term). | Clarify FR-02: an in-progress course counts as satisfied **only for terms after its current term**, and a Not passed outcome triggers FR-10. | Clarify |
| C-4 | **FR-08** is silent on courses with no offering data (most electives). | Add: "Where a course's offering pattern is Unknown, the software shall allow it in any Fall or Spring term and flag it." Consider EV-09's confidence levels. | Add |
| C-5 | **Non-goals (§1.3)** list natural-language questions as a stretch goal. The tech spec (EV-08) and prototype implement them behind a guardrail. | (a) Keep as stretch and baseline FR-19 as Low priority. (b) Promote. | (a): baseline FR-19/FR-21 as Low priority so the guardrail design is traceable |
| C-6 | Roadmap-vs-roadmap offering disagreements (CSE 4100, 4310, 4880, 5250) | Use the most restrictive (current prototype) or show a low-confidence warning (EV-09) | Keep most restrictive for planning, add a confidence flag to the UI |

## D. Proposed new requirements (EARS form, SRS §5.1)

| ID | Requirement | Source | Priority | Risk | Verify |
|---|---|---|---|---|---|
| FR-19 | When the student submits a plain-language what-if question, the software shall convert it into exactly one typed scenario event. It shall apply the event only if deterministic validation passes and calibrated confidence is at least 0.60. | EV-08 | Low | High | Test |
| FR-20 | When program data is loaded, the software shall record each unit, prerequisite, term-offering, and program-total disagreement between catalog and roadmap, and display it to the user without resolving it. | EV-09; EV-10 | Medium | Medium | Test |
| FR-21 | When the software makes an AI-assisted classification, it shall append one audit record containing the input, parsed event, raw and calibrated confidence, thresholds, and outcome. | EV-08 | Low | Low | Test |
| DR-07 | The software shall rebuild its program data identically from the cached public source files without network access. | EV-02 | Medium | Low | Test |
| DR-08 | Where catalog and roadmap values disagree, the software shall use the catalog value for units and prerequisites, and the roadmap value for recommended sequence and term offering. | EV-09 | High | Medium | Test |
| NFR-11 | When a course is recorded as Not passed or Withdrawn, 100% of planned courses outside its downstream set and standing-gated set shall keep their planned term. | EV-08 | Medium | Low | Test |
| NFR-12 | If the language-model service is unavailable, the software shall keep every non-AI function available and escalate AI requests. After 3 consecutive failures it shall stop calling the service for 60 s. | EV-08 | Low | Low | Test |
| NFR-13 | The software shall treat its confidence thresholds as calibrated only when expected calibration error is at most 0.02 on at least 40 labeled queries. | EV-08 | Low | Medium | Analysis |
| COM-04 | The team shall collect program data only from public pages permitted by robots.txt, at least 2 s apart, with an identifying user agent. | EV-08 | High | Low | Inspection |
| COM-05 | The team shall merge to `main` only when lint, automated tests, and the traceability check pass. | EV-06 | Medium | Low | Test |

Numerical values in NFR-12 and NFR-13 come from the tech spec (EV-08), not stakeholder evidence. Mark them provisional under AS-08.

## E. Supporting material for SRS sections

- **§3 IF-02 API contract:** implemented; see [design.md §6](../02-models-architecture/design.md#6-interface-specification-if-02). FastAPI also serves an OpenAPI document at `/openapi.json`, which satisfies "contract to be documented as OpenAPI".
- **§2.2 Context diagram:** the context model in [design.md §2.1](../02-models-architecture/design.md#21-context-model).
- **§11.2 verification column:** the tests now exist; see the generated [traceability.md](traceability.md).

## F. Impact analysis

- **Scope:** adds 3 FR, 2 DR, 3 NFR, and 2 COM, all already implemented and tested. Priorities are Low or Medium except DR-08 and COM-04.
- **Design:** none; this documents existing design (ADR-1, ADR-2).
- **Schedule:** none; the work is already done.
- **Risk:** reduces R-9 (data accuracy) through FR-20, DR-08, and DR-07.
- **Tests:** already tagged; see [traceability.md](traceability.md).
