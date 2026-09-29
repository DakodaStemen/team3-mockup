# SRS change proposal CH-03 (for SRS v0.2)

> [Docs index](../README.md) · [Register](requirements-register.md) · [Traceability](traceability.md) · [Change proposals](srs-change-proposal-CH-02.md) · [References](references.md)

| Field | Entry |
|---|---|
| Change ID | CH-03 (continues SRS v0.1 Appendix A, after [CH-02](srs-change-proposal-CH-02.md)) |
| Requested by | Dakoda Stemen (team request 2026-09-28; AI-assisted draft, see [AI Engineering Log](../05-ai-provenance/ai-engineering-log.md)) |
| Date | 2026-09-28 |
| Affected baseline | SRS v0.1: [TeamName_AdaptiveDegreePathwayPlanner_SRS_v0_1](https://docs.google.com/document/d/1h-cgCt8wF0NcHRoyRzOdYJiq81ip6GJhvYBi4g2LHtY/edit) |
| Status | **Proposed.** Implemented in the prototype behind the flags below; pending team review. The CCB decision is recorded in SRS Appendix A. |

**Why this change.** Summer and winter terms are how students catch up after a failed or withdrawn course, or carry a normal load plus one extra course. SRS v0.1 covers summer only as a yes/no (FR-07, FR-11) and has no winter term. It never uses either to recover a slipping graduation date. Separately, team review found a lab being scheduled a term after its lecture.

## A. Evidence

| ID | Evidence | Status |
|---|---|---|
| EV-02 | Catalog course pages: PHYS 2500L lists "Semester Corequisite: MATH 2220 and PHYS 2500"; PHYS 2510L lists "Semester Corequisite: PHYS 2510" | Verified in `backend/data/raw/courses_phys.html` |
| EV-11 | Summer and winter offering history for CSE, MATH, PHYS | **Partial.** Current Fall/Spring frequency is public (CSE advising PDF, MATH tentative-course PDFs, PHYS course-schedule page). Semester-era summer/winter sections exist only in the live class schedule, whose API robots.txt disallows; quarter-era PDFs (2011–2017) are on the Internet Archive (§C-1) |
| EV-12 | Session unit limits | **Verified** 2026-09-28: summer 14 units for the term (7 per session), winter intersession 4 units with no overload, fall/spring 18 for undergraduates. Sources: csusb.edu/registrar/registration/course-overload, csusb.edu/winter-intersession, csusb.edu/summer/frequently-asked-questions |

## B. Proposed requirements (EARS form, SRS §5.1)

| ID | Requirement | Source | Priority | Risk | Verify |
|---|---|---|---|---|---|
| FR-22 | Where the student selects a Winter intersession, the software shall schedule a term between Fall and the next Spring, cap it at the winter unit limit, place only courses offered in both regular terms, and flag every placement as unconfirmed. | Team request; EV-12 | High | Medium | Test |
| FR-23 | The software shall schedule a lab in the same term as its lecture. When either must move, the software shall move both. | EV-02; team review | High | Low | Test |
| FR-24 | When a what-if delays graduation, the software shall propose the fewest opt-in Summer or Winter terms after the setback that recover the date, or as much of it as possible, and shall show the result as a previewable plan. It shall also offer an alternative pathway using intersessions. | Team request | High | Medium | Test |

FR-07 and FR-11 extend to Winter unchanged: no Winter term unless selected, and adding one triggers recalculation.

## C. Open questions and conflicts (need a team decision)

1. **Offering data.** Public sources give current Fall/Spring frequency but not semester-era summer/winter history; a person can export it from the live class schedule by hand. Until then, the engine assumes a course offered in both Fall and Spring *may* run in Summer or Winter, and flags each placement "unconfirmed". Real schedules may differ. Decision needed: which public source to ingest (see research notes when complete), and whether a course with no summer/winter history should be excluded or only warned.
2. **Unit limits.** Resolved by EV-12: the engine's maximums are summer 14 and winter 4 (fall/spring 18). Because summer and winter are short, it plans summer to 7 (one session) and winter to 4, and flags any regular load above 18 as needing an approved overload (re-read 2026-09-29). Still open: move them into data (NFR-09), and decide whether the 3–21 regular-term range should stop at the Registrar's 18 without an approved overload.
3. **Winter exists.** Verified: a three-week Winter Intersession runs (2026–27: Dec 18 to Jan 11), and archived term codes show Winter 2022 and 2023. Fees may differ from regular terms, which the planner does not model.
4. **Recovery search.** FR-24 uses a greedy search with pair lookahead, not an exhaustive one (`recover()` in `engine.py`). It can miss a combination of three or more terms that only works together. Accept, or fund an exhaustive search with a time limit.
5. **"On time".** A Summer finish counts as the same academic year as the preceding Spring, following the existing `delta_terms` convention. The explanation text says so explicitly. Confirm this matches how the university reports graduation.

## D. Impact analysis

- **Scope:** adds FR-22, FR-23, FR-24; extends FR-07 and FR-11. All three are implemented and tested.
- **Design:** `SEASON_ORDER` gains Winter (Winter YYYY is January, before Spring YYYY). `Plan` gains `winters`. Labs pair through `Catalog.lab_for`. `recover()` chains ordinary what-if events, so it reuses every existing rule.
- **API:** `/scenario` adds `recovery` when graduation slips; `/plan` alternatives add `with summer & winter`. Both are additive.
- **Results:** the scenario sweep covers Add Winter and recovery. On the current data, opt-in terms fully recover 128 of 160 delayed Fail/Withdraw runs, and every recovered plan passes validation. These numbers rest on the unconfirmed assumptions in §C.
- **Risk:** R-9 (data accuracy) increases until EV-11 and EV-12 exist, because the planner suggests intersessions that may not run. Mitigated by the "unconfirmed" warnings and the "To confirm" list.
- **Tests:** tagged FR-22/23/24; see [traceability.md](traceability.md).
