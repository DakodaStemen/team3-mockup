# Verification Strategy

This carries the useful parts of a traditional Software Test Plan (STP), per the course dossier guidance. It serves as the validation plan (Sommerville Fig 23.2) and is structured by the three testing stages of Ch 8. It also covers SRS §9 prototypes (PR-01..03) and §11 verification methods. Requirement IDs refer to [SRS v0.1 and register](../01-product-requirements/requirements-register.md). The requirement → test mapping is generated in [traceability.md](../01-product-requirements/traceability.md).

## 1. Approach

Verification and validation combines **inspection** and **testing** (Sommerville §8, Fig 8.2):

| Activity | Applies to | How |
|---|---|---|
| Inspection | Every pull request: code, docs, data changes | PR review with the checklist in [quality-and-cm-plan.md §1.4](quality-and-cm-plan.md#14-inspection-checklist) |
| Development testing | Units, components, system | `pytest` (backend) and `tsc` (frontend), run in CI on every push/PR |
| Release testing | A tagged release candidate | Requirements-based and scenario tests, run by a team member who did not author the features (§4) |
| User testing | Release candidates | Alpha (team), usability sessions (NFR-05), acceptance by the instructor (§5) |

## 2. Development testing

| Stage | Scope | Where |
|---|---|---|
| Unit | Grades, prerequisite groups, requisite-text parser, calibration math | `tests/test_engine.py`, `tests/test_ingest.py`, `tests/test_guardrail.py` |
| Component | Engine as a whole (plan / scenario / validator); guardrail with a fake LLM; ingestion pipeline rebuilt from cache | same files |
| System | REST API end to end (`TestClient`); 282-run scenario sweep with validity checks | `test_guardrail.py::test_api_end_to_end`, `scripts/results.py` |

Every automated test follows **setup → call → assert** (Sommerville §8.1.1) and is tagged with the requirement(s) it verifies:

```python
@pytest.mark.req("FR-10", "NFR-11")
def test_fail_only_touches_descendants(): ...
```

**Test-first policy (TDD, §8.2).** A new or changed requirement gets its tagged, failing test before the implementation. A bug fix gets a regression test that fails before the fix. CI fails if any `Implemented` or `Partial` requirement verified by Test has no tagged test, or if `traceability.md` is stale (`tests/test_traceability.py`).

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

The UI ↔ API contract (design.md §6 (IF-02)) is covered by:
- `test_api_end_to_end`: the happy path.
- `test_api_rejects_invalid_requests`: 400 and 404.
- `tsc` in CI: the UI's types match the documented shapes.

## 4. Release testing (§8.3)

Performed on a release-candidate tag by a team member who **did not author** the features under test.

1. **Requirements-based testing.** For every row of [traceability.md](../01-product-requirements/traceability.md): automated tests pass, and non-`Test` requirements are checked by their method (Inspection / Analysis / Demonstration). Record the outcome in the release PR.
2. **Scenario testing.** Walk the spec's demo stories in the UI:
   - Alex: fail CSE 2020 in Spring 2027 → explanation shown; invalidated courses highlighted; Keep/Discard works.
   - Morgan: fail CSE 5700 (Fall-only) → "delayed by 2 term(s)… once a year".
   - Sam: plan starts in Fall and PHYS 2510 waits for Spring, with a warning.
   - Discrepancy banner lists all ingested discrepancies.
   - Plain-language question with Ollama **stopped** → escalated, logged in the audit panel. With Ollama **running** → accepted and recalculated.
3. **Performance testing.** NFR-04 (≥ 95% of requests within 2 s, provisional per AS-08): automated test plus the recalculation-time distribution in `results/summary.md` (median ~1 ms).
4. **Accessibility inspection.** NFR-06: complete every task by keyboard alone, and confirm no status is conveyed by color alone. Currently *Unverified*; the DAG view is known to rely on color.

## 5. User testing (§8.4)

| Type | Who | Pass criterion |
|---|---|---|
| Alpha | Team members outside their own area | No blocking defects open |
| Usability (NFR-05, SRS PR-01) | ≥ 5 CS students not on the team, unaided | ≥ 80% apply a what-if and correctly state the new graduation term within 5 min |
| Acceptance | Course instructor | The spec's three demo goals: end-to-end pipeline, all 8 capabilities, visible guardrails |

## 6. Test recording and defect handling

- **Automated runs:** GitHub Actions logs per commit. The evaluation outputs are versioned in `backend/results/`.
- **Defects:** a GitHub issue using the *Bug report* form. Each fix references the issue and adds a regression test.
- **Release test record:** a checklist in the release PR, covering §4.1–4.4 with pass/fail and the tester's name.

## 6.1 Prototype validation (SRS §9)

| ID | Status | Evidence |
|---|---|---|
| PR-01 usability wireframe | Planned (sprint 2) | Session notes → `docs/01-product-requirements/` (EV-05) |
| PR-02 scheduler feasibility | **Partly done**: validity and speed shown (EV-07); still needs the exhaustive-optimum comparison on small cases | `backend/results/summary.md` |
| PR-03 advisor rule walkthrough | Planned; several rules now answered from the catalog (CH-02 §B) | EV-04 notes |

## 7. Release entry and exit criteria

- **Entry:** CI green on `main`, and the release candidate is tagged.
- **Exit:**
  - Every Implemented/Partial Test requirement passes.
  - Every Inspection/Analysis/Demonstration item has a recorded outcome.
  - There are no open *severity: high* bugs.
  - CHANGELOG is updated.
