# Requirement attribute register

**The authoritative requirement text is the SRS**, not this file:
- **SRS v0.1** (Google Doc, team working copy): [TeamName_AdaptiveDegreePathwayPlanner_SRS_v0_1](https://docs.google.com/document/d/1h-cgCt8wF0NcHRoyRzOdYJiq81ip6GJhvYBi4g2LHtY/edit)
- **Proposed changes:** [srs-change-proposal-CH-02.md](srs-change-proposal-CH-02.md)

This register is the SRS §5.3 attribute register that the template allows. It holds each ID's one-line summary, verification method, baseline, and **implementation status**. `backend/scripts/trace.py` reads it to build [traceability.md](traceability.md), and CI fails when an `Implemented` or `Partial` requirement verified by Test has no tagged test.

Change a requirement's *text* in the SRS first, then update its summary here.

| ID | Summary | Source | Verify | Baseline | Implementation |
|---|---|---|---|---|---|
| FR-01 | Mark each requirement group satisfied, in progress, or remaining when a record loads | EV-01 | Test | SRS v0.1 | Partial: `Catalog.required()` and `baseline()` resolve remaining courses, and real GE courses (e.g. ENG 1070A) fill named GE slots; no per-group status output yet |
| FR-02 | Count a course toward a group or prerequisite only when Passed | EV-01; AS-02 | Test | SRS v0.1 | Partial: pass must meet the catalog grade minimum (C, C-); in-progress courses are assumed passed for *future-term* planning, which conflicts with AS-02 (CH-02 §C-3) |
| FR-03 | Place a course only after its prerequisites are passed or planned earlier | EV-01 | Test | SRS v0.1 | Implemented: corequisites may share the term (answers OQ-02, CH-02 §B) |
| FR-04 | On Not passed or Withdrawn, identify every directly or transitively dependent planned course | EV-01 | Test | SRS v0.1 | Implemented |
| FR-05 | Assign every remaining required course to a future term | EV-01 | Test | SRS v0.1 | Implemented: default electives sum to exactly 12 units; a chosen elective's supporting prerequisite (e.g. CSE 3350) is added automatically |
| FR-06 | Never exceed the term's target unit load | EV-01; AS-03 | Test | SRS v0.1 | Implemented |
| FR-07 | No Summer term unless summer enrollment is selected | EV-01 | Test | SRS v0.1 | Implemented: summer placements flagged *unconfirmed* (no published summer offerings) |
| FR-08 | Place a course only in a term its offering pattern includes | EV-01; AS-04 | Test | SRS v0.1 | Implemented: offerings from all 12 CSE-department roadmaps with confidence (high/low/unknown); low and unknown are warned (CH-02 §C-4, C-6) |
| FR-09 | Recalculate when a planned course is recorded Passed | EV-01 | Test | SRS v0.1 | Implemented |
| FR-10 | Reschedule a Not passed or Withdrawn course and its downstream courses | EV-01 | Test | SRS v0.1 | Implemented: also re-places courses whose class standing no longer holds |
| FR-11 | Recalculate when summer is turned on or a term's unit load changes | EV-01 | Test | SRS v0.1 | Implemented |
| FR-12 | Show previous and new graduation terms and each course whose term changed | EV-01 | Test; Demonstration | SRS v0.1 | Implemented: before/after graduation plus a `moved` list (course, from, to); the UI shows "was <term>" |
| FR-13 | Report an unplaceable course and its blocking constraint instead of a pathway | EV-01 | Test | SRS v0.1 | Implemented: 422 names each root blocking course and its constraint (missing prerequisite, standing, or offering), or a cap below a course's units |
| FR-14 | Flag a saved-pathway course planned in a term it is not offered | EV-01 | Test | SRS v0.1 | Implemented: `validate_plan()` and `POST /validate` |
| FR-15 | Scenario mode changes a copy; the saved pathway is unchanged until saved | EV-01 | Test | SRS v0.1 | Implemented |
| FR-16 | Answer whether graduation by a selected term is possible, with the earliest feasible term | EV-01 | Test | SRS v0.1 | Not implemented |
| FR-17 | Up to three valid alternatives, each labeled by how it differs | EV-01; OQ-05 | Test; Demonstration | SRS v0.1 | Partial: two alternatives (fastest 18u, balanced 12u) labeled by graduation term and peak load |
| FR-18 | Advisor view of a saved pathway with FR-13/FR-14 flags | EV-01; EV-04 | Demonstration | SRS v0.1 | Not implemented |
| FR-19 | Convert a plain-language what-if into one typed scenario; apply it only if validated and confidence ≥ 0.60 | EV-08 | Test | CH-02 (proposed) | Implemented |
| FR-20 | Record and display every catalog–roadmap disagreement; never resolve silently | EV-02; EV-09 | Test | CH-02 (proposed) | Implemented |
| FR-21 | Log every AI decision with input, parsed event, raw and calibrated confidence, thresholds, and outcome | EV-08 | Test | CH-02 (proposed) | Implemented |
| DR-01 | Program, course, prerequisite, student, and plan data with stable IDs and referential integrity | EV-01 | Test; Inspection | SRS v0.1 | Partial: every prerequisite endpoint resolves to a catalog course; no separate Offering or CourseAttempt entities |
| DR-02 | Prerequisites as Boolean AND/OR expressions | EV-02; OQ-02 | Test | SRS v0.1 | Implemented: groups ANDed, alternatives ORed, with grade minimum and corequisite flag |
| DR-03 | Reject a load containing a cycle, undefined course, or missing field, reporting each record | EV-01 | Test | SRS v0.1 | Partial: cycle edges are rejected and logged but the load continues (tech-spec ADR; CH-02 §C-1); missing fields fail validation |
| DR-04 | Record each attempt with course, term, and outcome | EV-01 | Test | SRS v0.1 | Partial: letter grades per course; W/NC/F are not passes; CR/P/TR count as C pending advisor confirmation (CH-02 C-8); no term per attempt |
| DR-05 | Load only datasets labeled synthetic | EV-01; EV-06 | Test; Inspection | SRS v0.1 | Not implemented: public catalog data is real, not synthetic (CH-02 §C-2) |
| DR-06 | Store program-data version and generation date with each saved pathway | EV-01 | Inspection | SRS v0.1 | Not implemented: no persistence yet |
| DR-07 | Rebuild program data reproducibly from cached public sources | EV-02 | Test | CH-02 (proposed) | Implemented |
| DR-08 | Catalog authoritative for units and prerequisites; roadmap for sequence and offerings; conflicts stored and flagged | EV-09; EV-10 | Test | CH-02 (proposed) | Implemented |
| DR-09 | GE requirements as slots filled by any listed catalog course at the area's minimum grade | EV-02 | Test | CH-02 (proposed) | Implemented |
| NFR-01 | A Student-role user cannot read another student's record, and denials are logged | EV-01; EV-06 | Test | SRS v0.1 | Not implemented: no sign-in (OQ-06) |
| NFR-02 | No real records, credentials, or keys in repo or logs, checked by secret scan and review | EV-06 | Inspection; Analysis | SRS v0.1 | Partial: synthetic students only; no automated secret scan yet |
| NFR-03 | Validate every API request; reject malformed or out-of-range input without changing stored data | EV-06 | Test | SRS v0.1 | Implemented: Pydantic 422; stateless API |
| NFR-04 | ≥ 95% of generation and recalculation requests within 2 s (provisional, AS-08) | EV-01; AS-08 | Test | SRS v0.1 | Implemented: measured median ~1 ms |
| NFR-05 | ≥ 80% of ≥ 5 students apply a what-if and state the new graduation term within 5 min (provisional) | EV-05; AS-08 | Test | SRS v0.1 | Not implemented: usability study planned (PR-01) |
| NFR-06 | Keyboard operable; status never conveyed by color alone | EV-06 | Test; Inspection | SRS v0.1 | Unverified: native controls and text labels, but the DAG view uses color only |
| NFR-07 | Every pathway in a ≥ 30-case scenario suite passes the independent validator | EV-01 | Test; Analysis | SRS v0.1 | Implemented: 280-run sweep in `results/`, plus tests |
| NFR-08 | Identical inputs give an identical pathway | EV-01 | Test | SRS v0.1 | Implemented |
| NFR-09 | Groups, prerequisites, offerings, and unit limits defined in data files | EV-01 | Inspection; Demonstration | SRS v0.1 | Partial: `catalog.json`; summer cap and guardrail thresholds are still code constants |
| NFR-10 | Every pathway screen states it is a planning aid, not an official audit or advising decision | EV-01 | Inspection | SRS v0.1 | Implemented |
| NFR-11 | After Not passed or Withdrawn, 100% of courses outside the affected set keep their term | EV-08 | Test | CH-02 (proposed) | Implemented |
| NFR-12 | If the LLM is unavailable, deterministic functions stay available; NL requests escalate; breaker opens after 3 failures for 60 s | EV-08 | Test | CH-02 (proposed) | Implemented |
| NFR-13 | Thresholds count as calibrated only when ECE ≤ 0.02 on ≥ 40 labeled queries | EV-08 | Analysis | CH-02 (proposed) | Partial: method and 45-query set exist; not yet run (needs Ollama) |
| COM-01 | Maintain the SRS per course-tailored ISO/IEC/IEEE 29148 practice | REF-02 | Inspection | SRS v0.1 | Active |
| COM-02 | Document AI assistance, human review, validation, and responsibility | Course policy | Inspection | SRS v0.1 | Active: [AI Engineering Log](../05-ai-provenance/ai-engineering-log.md) |
| COM-03 | No real student or restricted data in repo, drives, or AI tools | EV-06 | Inspection | SRS v0.1 | Active |
| COM-04 | Ingest only public pages allowed by robots.txt, ≥ 2 s apart, with an identifying user agent | EV-08 | Inspection | CH-02 (proposed) | Implemented |
| COM-05 | CI gate: lint, tests, and traceability must pass before merge | EV-06 | Test | CH-02 (proposed) | Implemented |
