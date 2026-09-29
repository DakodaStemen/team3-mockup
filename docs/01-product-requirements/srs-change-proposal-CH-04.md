# SRS change proposal CH-04 (for SRS v0.2)

> [Docs index](../README.md) · [Register](requirements-register.md) · [Traceability](traceability.md) · [Change proposals](srs-change-proposal-CH-02.md) · [References](references.md)

| Field | Entry |
|---|---|
| Change ID | CH-04 (after [CH-03](srs-change-proposal-CH-03.md)) |
| Requested by | Dakoda Stemen (team request 2026-09-28; AI-assisted draft, see [AI Engineering Log](../05-ai-provenance/ai-engineering-log.md)) |
| Date | 2026-09-28 |
| Affected baseline | SRS v0.1: [TeamName_AdaptiveDegreePathwayPlanner_SRS_v0_1](https://docs.google.com/document/d/1h-cgCt8wF0NcHRoyRzOdYJiq81ip6GJhvYBi4g2LHtY/edit) |
| Status | **Proposed.** Implemented in the prototype; pending team review. **§C-1 needs a decision before any demo with a real transcript.** |

**Why this change.** Students with earlier terms saw only a list of grades, not their past semesters. Bottlenecks were a static score, not what a failure would actually cost. And a student could not start from their own record.

## A. Proposed requirements (EARS form, SRS §5.1)

| ID | Requirement | Source | Priority | Risk | Verify |
|---|---|---|---|---|---|
| DR-04 (revised) | The software shall record each course attempt with its term and grade, including attempts that did not pass, and shall plan from the latest grade. | EV-01 | High | Low | Test |
| FR-25 | For each planned course, the software shall measure the graduation delay if the course is failed in its planned term, and the Summer or Winter terms that would recover it, and shall display the courses whose failure delays graduation. | Team request | Medium | Low | Test |
| FR-26 | When a student uploads an unofficial transcript (PDF, text, or CSV), the software shall build a temporary profile with term history, transfer credit, and in-progress courses, shall list every course and line it could not use, and shall not store the file or profile beyond the running session. | Team request | Medium | **High** | Test |

The UI also shows past terms in the plan (marked "Completed", with grades and retakes), colors major electives apart from required courses and GE, and adds a "Protect these" strip. These are presentation, covered by FR-12 and the design system (DESIGN.md).

## B. Evidence

- **Sample data:** each synthetic student now has a term-by-term history generated with the engine's own placement, so prerequisites, labs, offerings, and standing hold (test `test_each_history_is_a_catalog_valid_sequence`).
- **Transcript format:** no real CSUSB unofficial transcript was available. The parser targets the common registrar layout (term header, then `SUBJ NNNN Title Attempted Earned Grade Points`) and a CSV export, verified against a synthetic sample (`backend/data/sample_transcript.txt`). **Test against a real (redacted) myCoyote unofficial transcript before relying on it.**

## C. Conflicts and decisions

1. **Real student records.** SRS v0.1 lists "real student records" as a non-goal and DR-05 says to load only synthetic data. FR-26 lets a real record in. Mitigations in the prototype: the file never touches disk, the profile lives in process memory (newest 200) and is gone on restart, nothing from it is logged, and the UI says "not saved". Decision needed: accept FR-26 and amend DR-05, or keep upload to synthetic demo transcripts only.
2. **FERPA.** A deployed version handling real transcripts would fall under FERPA and campus data policy. Out of scope for the prototype; record it as a constraint for any deployment (risk register).
3. **Parser accuracy.** Unrecognized courses (not in the B.S. CS catalog, or quarter-era numbers) are listed and not counted. A course the parser misreads could still mislead; the report asks the student to check every term.

## D. Impact analysis

- **API:** `POST /risk`, `POST /transcript`, `GET /transcript/sample`; `StudentProfile.history` added (optional, backward compatible). All endpoints accept an uploaded profile's id.
- **Engine:** a passed lab or lecture now keeps its partner in its term when later terms are rebuilt; a lab failed after its lecture passed is retaken alone. A seeded fuzz test (`test_fuzz.py`) chains every event type across all students and the sample transcript and checks validity, opt-in intersessions, caps, lab pairing, credited terms, delay arithmetic, and recovery. It found that bug.
- **Risk:** R-9 unchanged; a new privacy risk (§C-1, §C-2).
- **Tests:** tagged FR-25, FR-26, DR-04; see [traceability.md](traceability.md).
