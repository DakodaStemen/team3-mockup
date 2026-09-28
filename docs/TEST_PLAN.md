# Test Plan (Validation Plan)

This is the project's validation plan (Sommerville Fig 23.2), structured by the three testing stages of Ch 8. Requirement IDs refer to [SRS.md](SRS.md). The requirement → test mapping is generated in [TRACEABILITY.md](TRACEABILITY.md).

## 1. Approach

Verification and validation combines **inspection** and **testing** (Sommerville §8, Fig 8.2):

| Activity | Applies to | How |
|---|---|---|
| Inspection | Every pull request: code, docs, data changes | PR review with the checklist in [QUALITY_AND_CM.md §1.4](QUALITY_AND_CM.md#14-inspection-checklist) |
| Development testing | Units, components, system | `pytest` (backend) and `tsc` (frontend), run in CI on every push/PR |
| Release testing | A tagged release candidate | Requirements-based and scenario tests, run by a team member who did not author the features (§4) |
| User testing | Release candidates | Alpha (team), usability sessions (NFR-11), acceptance by the instructor (§5) |

## 2. Development testing

| Stage | Scope | Where |
|---|---|---|
| Unit | Grades, prerequisite groups, requisite-text parser, calibration math | `tests/test_engine.py`, `tests/test_ingest.py`, `tests/test_guardrail.py` |
| Component | Engine as a whole (plan / scenario / validator); guardrail with a fake LLM; ingestion pipeline rebuilt from cache | same files |
| System | REST API end to end (`TestClient`); 282-run scenario sweep with validity checks | `test_guardrail.py::test_api_end_to_end`, `scripts/results.py` |

Every automated test follows **setup → call → assert** (Sommerville §8.1.1) and is tagged with the requirement(s) it verifies:

```python
@pytest.mark.req("FR-4", "NFR-2")
def test_fail_only_touches_descendants(): ...
```

**Test-first policy (TDD, §8.2).** A new or changed requirement gets its tagged, failing test before the implementation. A bug fix gets a regression test that fails before the fix. CI fails if any FR has no test (`tests/test_traceability.py`).

### 2.1 Equivalence partitions and boundaries (§8.1.2)

Test cases are chosen from each partition, **on its boundaries** and at a midpoint.

| Input | Partitions | Boundary / representative cases | Tests |
|---|---|---|---|
| Grade vs minimum | meets; exactly meets; just below (+/-); non-grade (W, NC); F | `C` vs `C` ✓; `C` vs `C-` ✓; `C-` vs `C` ✗; `W` ✗; `F` ✗ | `test_grades`, `test_grade_minimum_forces_retake` |
| Prerequisite shape | single AND; OR group; corequisite same term; entry-level assumption | CSE 2020 (C-min AND); MATH 2210 (OR); PHYS 2500L (coreq) | `test_plans_valid_and_complete`, `test_ingest.py` |
| Offering × season | Fall/Spring/Both/Unknown × Fall/Spring/Summer | Spring-only in Fall waits; Fall-only capstone; Summer takes only Both | `test_spring_only_waits`, `test_failing_fall_only_capstone_costs_a_year`, `test_validator_catches_mycap_style_errors` |
| Standing | below / at threshold | CSE 4880 needs 90; a Fail drops a student below it | `test_fail_only_touches_descendants` |
| Scenario position | first / middle / last term; course not in term; term not in plan | 400 on invalid | `test_other_scenarios_stay_valid`, `test_api_rejects_invalid_requests` |
| Unit load (guardrail) | < 3; 3–21; > 21 | 2 ✗, 3 ✓, 21 ✓, 22 ✗ | `test_unit_load_bounds` |
| Calibrated confidence | < 0.60; 0.60–0.90; ≥ 0.90 | 0.59, 0.60, 0.89, 0.90 | `test_threshold_boundaries` |
| LLM availability | up; erroring; breaker open | fake LLM raises 3× then succeeds | `test_circuit_breaker_opens_after_repeated_failures` |
| Query intent | scenario; ambiguous; off-topic; prompt injection | `data/queries.json` (45 labeled) | `calibrate.py` (needs Ollama) |

## 3. Interface testing

The UI ↔ API contract (SRS Appendix A) is covered by:
- `test_api_end_to_end`: the happy path.
- `test_api_rejects_invalid_requests`: 400 and 404.
- `tsc` in CI: the UI's types match the documented shapes.

## 4. Release testing (§8.3)

Performed on a release-candidate tag by a team member who **did not author** the features under test.

1. **Requirements-based testing.** For every row of [TRACEABILITY.md](TRACEABILITY.md): automated tests pass, and non-`Test` requirements are checked by their method (Inspection / Analysis / Demonstration). Record the outcome in the release PR.
2. **Scenario testing.** Walk the spec's demo stories in the UI:
   - Alex: fail CSE 2020 in Spring 2027 → explanation shown; invalidated courses highlighted; Keep/Discard works.
   - Morgan: fail CSE 5700 (Fall-only) → "delayed by 2 term(s)… once a year".
   - Sam: plan starts in Fall and PHYS 2510 waits for Spring, with a warning.
   - Discrepancy banner lists all ingested discrepancies.
   - Plain-language question with Ollama **stopped** → escalated, logged in the audit panel. With Ollama **running** → accepted and recalculated.
3. **Performance testing.** NFR-1 (plan < 200 ms). The recalculation-time distribution comes from `results/summary.md`.

## 5. User testing (§8.4)

| Type | Who | Pass criterion |
|---|---|---|
| Alpha | Team members outside their own area | No blocking defects open |
| Usability (NFR-11) | 3 CSUSB students not on the team, unaided | Each runs a what-if and reads its explanation in ≤ 2 min |
| Acceptance | Course instructor | The spec's three demo goals: end-to-end pipeline, all 8 capabilities, visible guardrails |

## 6. Test recording and defect handling

- **Automated runs:** GitHub Actions logs per commit. The evaluation outputs are versioned in `backend/results/`.
- **Defects:** a GitHub issue using the *Bug report* form. Each fix references the issue and adds a regression test.
- **Release test record:** a checklist in the release PR, covering §4.1–4.3 with pass/fail and the tester's name.

## 7. Release entry and exit criteria

- **Entry:** CI green on `main`, and the release candidate is tagged.
- **Exit:**
  - Every FR `Test` passes.
  - Every Inspection/Analysis/Demonstration item has a recorded outcome.
  - There are no open *severity: high* bugs.
  - CHANGELOG is updated.
