import json
import time

import networkx as nx
import pytest

from planner.engine import alternatives, apply_scenario, grade_ok, make_plan, term_key, timeline, validate_plan
from planner.graph import DATA, Catalog, load_catalog, load_students
from planner.models import ScenarioEvent

CAT = load_catalog()
STUDENTS = load_students()


def check_valid(plan, profile, cap=None):
    assert validate_plan(plan, profile, CAT, cap) == []


@pytest.mark.req("FR-03", "FR-05", "FR-06", "FR-08", "NFR-07")
@pytest.mark.parametrize("sid", STUDENTS)
def test_plans_valid_and_complete(sid):
    check_valid(make_plan(STUDENTS[sid]), STUDENTS[sid])


@pytest.mark.req("FR-05")
def test_freshman_plan_meets_catalog_total():
    assert timeline(make_plan(STUDENTS["alex"]))["total_units"] == CAT.program["catalog_total_units"]


@pytest.mark.req("FR-02", "DR-04")
def test_grades():
    assert grade_ok("C", "C") and grade_ok("C", "C-") and not grade_ok("C-", "C")
    assert not grade_ok("W", "D-") and not grade_ok("F", "D-")


@pytest.mark.req("FR-01", "FR-02")
def test_grade_minimum_forces_retake():
    first = make_plan(STUDENTS["jordan"]).terms[0].courses
    assert "CSE 2010" in first  # D is below the C that CSE 2020 requires


@pytest.mark.req("FR-08")
def test_spring_only_waits():
    plan = make_plan(STUDENTS["sam"])  # starts in Fall, still needs PHYS 2510
    assert "PHYS 2510" not in plan.terms[0].courses
    assert "PHYS 2510" in plan.terms[1].courses and "PHYS 2510L" in plan.terms[1].courses


@pytest.mark.req("FR-04", "FR-10", "NFR-11")
def test_fail_only_touches_descendants():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027"))
    planned = {c for t in plan.terms for c in t.courses}
    ripple = (nx.descendants(CAT.g, "CSE 2020") | {"CSE 2020"}) & planned
    extra = set(r["invalidated"]) - ripple
    assert ripple <= set(r["invalidated"])
    assert all(CAT.courses[c].min_standing_units for c in extra)  # only standing-gated courses beyond the DAG ripple
    check_valid(r["plan"], alex)
    before = {c: t.term_label for t in plan.terms for c in t.courses}
    after = {c: t.term_label for t in r["plan"].terms for c in t.courses}
    assert all(after[c] == before[c] for c in before if c not in r["invalidated"])


@pytest.mark.req("FR-10", "FR-12")
def test_failing_fall_only_capstone_costs_a_year():
    morgan = STUDENTS["morgan"]
    r = apply_scenario(morgan, make_plan(morgan), ScenarioEvent(event_type="Fail", course_id="CSE 5700", term_label="Fall 2027"))
    assert r["delta_terms"] == 2 and "once a year" in r["explanation"]


@pytest.mark.req("FR-09", "FR-11", "NFR-07")
def test_other_scenarios_stay_valid():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    for ev in [
        ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"),
        ScenarioEvent(event_type="Change Unit Load", term_label="Fall 2027", unit_load=12),
        ScenarioEvent(event_type="Pass", course_id="CSE 2020", term_label="Spring 2027"),
        ScenarioEvent(event_type="Withdraw", course_id="MATH 2220", term_label="Spring 2027"),
    ]:
        r = apply_scenario(alex, plan, ev)
        check_valid(r["plan"], alex, cap=plan.unit_cap)
        assert r["explanation"].startswith("Graduation")


@pytest.mark.req("FR-17")
def test_alternatives_differ():
    alts = alternatives(STUDENTS["alex"])
    assert alts["fastest"]["timeline"]["term_count"] <= alts["balanced"]["timeline"]["term_count"]
    peak = {k: max(t.total_units for t in v["plan"].terms) for k, v in alts.items()}
    assert peak["fastest"] > 15 and peak["balanced"] <= 12


@pytest.mark.req("DR-03", "FR-20")
def test_cycle_edge_rejected_and_logged():
    raw = json.loads((DATA / "catalog.json").read_text(encoding="utf8"))
    raw["edges"].append({"from_course": "CSE 5720", "to_course": "CSE 2010"})
    cat = Catalog(raw)
    assert nx.is_directed_acyclic_graph(cat.g)
    assert any("CSE 5720 -> CSE 2010" in d for d in cat.discrepancies)


@pytest.mark.req("FR-20", "DR-08")
def test_spec_audit_discrepancies_reproduced_from_source():
    text = "\n".join(CAT.discrepancies)
    for needle in ["CSE 4010 units: roadmap says 3, catalog says 4", "CSE 4550 units: roadmap says 4, catalog says 3",
                   "roadmap says 125, catalog says 120", "CSE 4600 prerequisites"]:
        assert needle in text
    assert CAT.courses["CSE 5700"].term_offered == "Fall" and CAT.courses["PHYS 2510"].term_offered == "Spring"


@pytest.mark.req("FR-14")
def test_validator_catches_mycap_style_errors():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    bad = plan.model_copy(deep=True)
    bad.terms[1].courses.append("CSE 5700")  # Fall-only course dropped into Spring, prerequisites unmet
    problems = validate_plan(bad, alex, CAT, cap=99)
    assert any("Fall-only" in p for p in problems) and any("prerequisites" in p for p in problems)


@pytest.mark.req("FR-15")
def test_what_if_does_not_modify_submitted_plan():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    snapshot = plan.model_dump()
    apply_scenario(alex, plan, ScenarioEvent(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027"))
    assert plan.model_dump() == snapshot


@pytest.mark.req("NFR-04")
def test_generation_and_recalculation_within_2s():
    """SRS NFR-04 (provisional 2 s). Best of 3 per student, so a noisy CI runner can't fail it."""
    def best(fn, *args):
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            fn(*args)
            times.append(time.perf_counter() - t0)
        return min(times)

    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    fail = ScenarioEvent(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027")
    assert max(best(make_plan, STUDENTS[sid]) for sid in STUDENTS) < 2.0
    assert best(apply_scenario, alex, plan, fail) < 2.0


@pytest.mark.req("NFR-08")
def test_identical_inputs_give_identical_pathway():
    for sid in STUDENTS:
        assert make_plan(STUDENTS[sid]).model_dump() == make_plan(STUDENTS[sid]).model_dump()


@pytest.mark.req("FR-07")
def test_no_summer_unless_selected():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    assert not any(t.term_label.startswith("Summer") for t in plan.terms)
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"))
    summer = [t for t in r["plan"].terms if t.term_label.startswith("Summer")]
    assert [t.term_label for t in summer] == ["Summer 2027"]
    assert all(CAT.courses[c].term_offered == "Both" for t in summer for c in t.courses)


@pytest.mark.req("DR-01")
def test_every_prerequisite_endpoint_is_a_catalog_course():
    assert all(u in CAT.courses and v in CAT.courses for u, v in CAT.g.edges)
    assert all(g_course in CAT.courses for g in CAT.program["groups"] for g_course in g.get("all", []) + g.get("from", []))


@pytest.mark.req("FR-08", "DR-08")
def test_once_a_year_offerings_match_team_research():
    """EV-09 (team findings across all 12 CSE roadmaps) vs what ingest.py derived independently."""
    fall = ["CSE 3350", "CSE 4050", "CSE 4400", "CSE 5160", "CSE 5208", "CSE 5210", "CSE 5410", "CSE 5700", "CSE 5720"]
    spring = ["CSE 4200", "CSE 4410", "CSE 4500", "CSE 5408", "CSE 5500", "PHYS 2510", "PHYS 2510L"]
    assert {c: CAT.courses[c].term_offered for c in fall + spring} == {**dict.fromkeys(fall, "Fall"), **dict.fromkeys(spring, "Spring")}
    assert CAT.courses["CSE 4100"].term_offered == "Spring" and CAT.courses["CSE 4100"].offering_confidence == "low"


@pytest.mark.req("FR-08")
def test_conflicting_or_unknown_offerings_are_warned():
    plan = make_plan(STUDENTS["alex"])
    warnings = " ".join(w for t in plan.terms for w in t.warnings)
    placed = {c for t in plan.terms for c in t.courses}
    for c in placed:
        if CAT.courses[c].term_offered == "Unknown":
            assert f"{c} term offering unknown" in warnings
        elif CAT.courses[c].offering_confidence == "low":
            assert f"{c}: roadmaps disagree" in warnings


@pytest.mark.req("FR-07")
def test_summer_placements_are_flagged_unconfirmed():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"))
    summer = next(t for t in r["plan"].terms if t.term_label == "Summer 2027")
    assert summer.courses and all(any(w.startswith(f"{c}: summer offerings are not published") for w in summer.warnings)
                                  for c in summer.courses)


@pytest.mark.req("FR-01", "FR-02", "DR-09")
def test_real_ge_course_fills_its_slot_with_grade_minimum():
    from planner.engine import baseline
    base = STUDENTS["alex"].model_copy(update={"start_term": "Spring 2027"})
    sat, todo, _ = baseline(base.model_copy(update={"completed_courses": {"ENG 1070A": "B"}}), CAT)
    assert "GE 1A" in sat and "GE 1A" not in todo
    sat, todo, _ = baseline(base.model_copy(update={"completed_courses": {"ENG 1070A": "D"}}), CAT)  # GE needs C-
    assert "GE 1A" in todo


@pytest.mark.req("FR-05")
def test_elective_choice_pulls_in_supporting_prerequisite():
    riley = STUDENTS["riley"].model_copy(update={"choices": {"CSE Elective": ["CSE 4030", "CSE 5300"]}})
    plan = make_plan(riley)
    order = [c for t in plan.terms for c in t.courses]
    assert "CSE 3350" in order and order.index("CSE 3350") < order.index("CSE 4030")
    check_valid(plan, riley)


@pytest.mark.req("FR-05")
def test_default_electives_meet_units_exactly():
    group = next(g for g in CAT.program["groups"] if "choose_units" in g)
    picks = CAT.required(STUDENTS["alex"], set()) & set(group["from"])
    assert sum(CAT.units(c) for c in picks) == group["choose_units"]


@pytest.mark.req("FR-03", "FR-09")
@pytest.mark.parametrize("sid", STUDENTS)
def test_pass_never_pulls_dependents_into_same_term(sid):
    """Regression: a Pass event used to credit the course before the plan began."""
    profile = STUDENTS[sid]
    plan = make_plan(profile)
    term_of = lambda p: {c: i for i, t in enumerate(p.terms) for c in t.courses}  # noqa: E731
    for t in plan.terms:
        for cid in [c for c in t.courses if not CAT.courses[c].placeholder]:
            r = apply_scenario(profile, plan, ScenarioEvent(event_type="Pass", course_id=cid, term_label=t.term_label))
            where = term_of(r["plan"])
            assert where.get(cid) is not None, f"{cid} vanished from its term"
            for d in nx.descendants(CAT.g, cid) & where.keys():
                edge = CAT.g.edges.get((cid, d), {}).get("edge")
                same_term_ok = edge is not None and edge.concurrent_ok
                assert where[d] > where[cid] or (same_term_ok and where[d] == where[cid]), f"{d} scheduled with/before {cid}"
            check_valid(r["plan"], profile, cap=plan.unit_cap)


@pytest.mark.req("DR-01", "FR-13", "FR-20")
def test_prerequisite_outside_catalog_is_logged_not_crashed():
    raw = json.loads((DATA / "catalog.json").read_text(encoding="utf8"))
    raw["edges"].append({"from_course": "MATH 9999", "to_course": "CSE 2020", "group": 9})
    cat = Catalog(raw)
    with pytest.raises(ValueError, match="CSE 2020 needs MATH 9999"):  # API turns this into 422, not a 500
        make_plan(STUDENTS["alex"], cat=cat)
    assert sum("MATH 9999" in d and "CSE 2020" in d for d in cat.discrepancies) == 1


@pytest.mark.req("FR-09", "FR-12")
def test_pass_explanation_does_not_claim_moves():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Pass", course_id="CSE 2010", term_label="Fall 2026"))
    assert r["delta_terms"] == 0
    assert r["explanation"] == "Graduation unchanged (Spring 2030): CSE 2010 passed in Fall 2026; later terms re-checked, no course moved."


@pytest.mark.req("FR-01", "FR-02", "DR-04")
def test_credit_grades_count_as_c():
    assert grade_ok("CR", "C") and grade_ok("P", "D-") and grade_ok("TR", "C-")
    assert not grade_ok("CR", "C+") and not grade_ok("NC", "D-")
    profile = STUDENTS["jordan"].model_copy(update={"completed_courses": {**STUDENTS["jordan"].completed_courses, "CSE 2010": "CR"}})
    plan = make_plan(profile)
    assert "CSE 2010" not in {c for t in plan.terms for c in t.courses}  # CR meets CSE 2020's C minimum; no retake
    check_valid(plan, profile)


@pytest.mark.req("FR-06", "FR-13")
def test_cap_below_a_course_is_one_clear_message():
    with pytest.raises(ValueError, match=r"^A 3-unit cap can't fit .* use a cap of at least 4\.$"):
        make_plan(STUDENTS["alex"], unit_cap=3)


@pytest.mark.req("FR-12")
def test_moved_lists_every_course_whose_term_changed():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Fail", course_id="CSE 2020", term_label="Spring 2027"))
    before = {c: t.term_label for t in plan.terms for c in t.courses}
    after = {c: t.term_label for t in r["plan"].terms for c in t.courses}
    assert {m["course"]: (m["from"], m["to"]) for m in r["moved"]} == {
        c: (before[c], after[c]) for c in before if c in after and before[c] != after[c]}
    assert {"course": "CSE 2020", "from": "Spring 2027", "to": "Fall 2027"} in r["moved"]


@pytest.mark.req("FR-09")
def test_pass_records_term_and_marks_nothing_affected():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Pass", course_id="CSE 2010", term_label="Fall 2026"))
    assert r["plan"].credited == {"CSE 2010": "Fall 2026"}
    assert r["invalidated"] == [] and r["moved"] == []


def _order_ok(plan):
    """Independent oracle: every planned prerequisite sits in an earlier term (or the same term if concurrent)."""
    where = {c: i for i, t in enumerate(plan.terms) for c in t.courses}
    for u, v, d in CAT.g.edges(data=True):
        if u in where and v in where and len([e for e in CAT.prereqs(v) if e.group == d["edge"].group]) == 1:
            assert where[u] < where[v] or (d["edge"].concurrent_ok and where[u] == where[v]), f"{v} not after {u}"


@pytest.mark.req("FR-03", "FR-09", "FR-11")
@pytest.mark.parametrize("second", [
    ScenarioEvent(event_type="Change Unit Load", term_label="Fall 2027", unit_load=21),
    ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"),
])
def test_passed_course_stays_put_when_its_term_is_rebuilt(second):
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Pass", course_id="CSE 3100", term_label="Fall 2027"))
    r = apply_scenario(alex, r["plan"], second)
    assert "CSE 3100" in next(t for t in r["plan"].terms if t.term_label == "Fall 2027").courses
    _order_ok(r["plan"])
    check_valid(r["plan"], alex, cap=21)


@pytest.mark.req("FR-03", "FR-10")
def test_failing_a_passed_course_revokes_the_credit():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Pass", course_id="CSE 2010", term_label="Fall 2026"))
    r = apply_scenario(alex, r["plan"], ScenarioEvent(event_type="Fail", course_id="CSE 2010", term_label="Fall 2026"))
    assert "CSE 2010" not in r["plan"].credited
    _order_ok(r["plan"])
    check_valid(r["plan"], alex)


@pytest.mark.req("FR-13")
def test_long_plan_blames_the_horizon_not_offerings():
    with pytest.raises(ValueError, match="30 terms at a 4-unit cap") as e:
        make_plan(STUDENTS["alex"], unit_cap=4)
    assert "never offered" not in str(e.value)


@pytest.mark.req("FR-07", "FR-11")
@pytest.mark.parametrize("label,msg", [("Summer 2026", "before the plan starts"), ("Summer 2020", "before the plan starts"),
                                       ("Summer 20x7", "like 'Summer 2027'"), ("Summer", "like 'Summer 2027'")])
def test_add_summer_rejects_bad_terms(label, msg):
    alex = STUDENTS["alex"]
    with pytest.raises(ValueError, match=msg):
        apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Add Summer", term_label=label))


@pytest.mark.req("FR-11")
def test_add_summer_twice_is_rejected():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"))
    with pytest.raises(ValueError, match="already"):
        apply_scenario(alex, r["plan"], ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"))


@pytest.mark.req("FR-10")
def test_retake_that_shortens_the_plan_says_why():
    jordan = STUDENTS["jordan"]
    plan = apply_scenario(jordan, make_plan(jordan), ScenarioEvent(event_type="Fail", course_id="CSE 4400", term_label="Fall 2029"))["plan"]
    r = apply_scenario(jordan, plan, ScenarioEvent(event_type="Withdraw", course_id="CSE 2010", term_label="Fall 2027"))
    assert r["delta_terms"] < 0 and "re-placing" in r["explanation"] and "because" not in r["explanation"]


@pytest.mark.req("FR-14")
def test_validator_flags_duplicates_bad_labels_and_order():
    alex = STUDENTS["alex"]
    plan = make_plan(alex).model_copy(deep=True)
    plan.terms[1].courses.append("MATH 2265")  # also in Fall 2026
    plan.terms[2].term_label, plan.terms[3].term_label = plan.terms[3].term_label, plan.terms[2].term_label
    plan.terms[4].term_label = "Autumn 2028"
    problems = "\n".join(validate_plan(plan, alex, CAT))
    assert "MATH 2265 is planned more than once" in problems
    assert "out of order" in problems and "Autumn 2028 is not a term label" in problems


@pytest.mark.req("FR-04", "FR-10")
def test_retaking_a_prerequisite_revokes_credit_downstream():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Pass", course_id="CSE 5000", term_label="Spring 2028"))
    r = apply_scenario(alex, r["plan"], ScenarioEvent(event_type="Withdraw", course_id="CSE 2020", term_label="Spring 2027"))
    assert "CSE 5000" not in r["plan"].credited  # its pass depended on the course being retaken
    _order_ok(r["plan"])
    check_valid(r["plan"], alex)


@pytest.mark.req("FR-14", "DR-01")
def test_validator_flags_credit_for_unknown_course():
    alex = STUDENTS["alex"]
    plan = make_plan(alex).model_copy(update={"credited": {"FOO 1": "Fall 2026"}})
    assert "credited course FOO 1 is not in the catalog" in validate_plan(plan, alex, CAT)


@pytest.mark.req("FR-06", "FR-07")
def test_summer_never_exceeds_a_lower_unit_cap():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Add Summer", term_label="Summer 2027"))
    r = apply_scenario(alex, r["plan"], ScenarioEvent(event_type="Change Unit Load", term_label="Spring 2027", unit_load=6))
    summer = next(t for t in r["plan"].terms if t.term_label == "Summer 2027")
    assert 0 < summer.total_units <= 6
    check_valid(r["plan"], alex, cap=16)


@pytest.mark.req("FR-10", "FR-11")
def test_passed_course_that_loses_standing_is_replaced():
    alex = STUDENTS["alex"]
    plan = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Withdraw", course_id="CSE 4400", term_label="Fall 2028"))["plan"]
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Pass", course_id="CSE 5500", term_label="Spring 2030"))
    r = apply_scenario(alex, r["plan"], ScenarioEvent(event_type="Change Unit Load", term_label="Fall 2028", unit_load=9))
    assert "CSE 5500" not in r["plan"].credited  # senior standing no longer holds in the term it was passed
    check_valid(r["plan"], alex, cap=16)


@pytest.mark.req("FR-09")
def test_pass_does_not_move_an_already_passed_dependent():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Pass", course_id="CSE 5720", term_label="Fall 2027"))
    r = apply_scenario(alex, r["plan"], ScenarioEvent(event_type="Change Unit Load", term_label="Fall 2028", unit_load=12))
    r = apply_scenario(alex, r["plan"], ScenarioEvent(event_type="Pass", course_id="CSE 2020", term_label="Spring 2027"))
    assert "CSE 5720" in next(t for t in r["plan"].terms if t.term_label == "Fall 2027").courses
    check_valid(r["plan"], alex, cap=16)


@pytest.mark.req("FR-06", "FR-11")
def test_each_term_keeps_the_cap_it_was_planned_under():
    sam = STUDENTS["sam"]  # 15-unit preference
    plan = make_plan(sam)
    raised = next(t.term_label for t in plan.terms[3:])
    plan = apply_scenario(sam, plan, ScenarioEvent(event_type="Change Unit Load", term_label=raised, unit_load=18))["plan"]
    for ev in [ScenarioEvent(event_type="Withdraw", course_id=c, term_label=t.term_label)
               for t in plan.terms for c in t.courses if term_key(t.term_label) < term_key(raised)][:12]:
        r = apply_scenario(sam, plan, ev)
        for t in r["plan"].terms:
            limit = 15 if term_key(t.term_label) < term_key(raised) else 18
            assert t.unit_cap == (min(14, limit) if t.term_label.startswith("Summer") else limit), t.term_label
            assert t.total_units <= t.unit_cap, f"{ev.course_id}: {t.term_label} {t.total_units} > {t.unit_cap}"
        check_valid(r["plan"], sam)  # no cap override: each term is checked against its own cap


@pytest.mark.req("FR-06", "FR-14")
def test_validator_checks_each_term_against_its_own_cap():
    alex = STUDENTS["alex"]
    r = apply_scenario(alex, make_plan(alex), ScenarioEvent(event_type="Change Unit Load", term_label="Fall 2027", unit_load=12))
    check_valid(r["plan"], alex)  # earlier 16-unit terms were planned under 16
    over = r["plan"].model_copy(deep=True)
    over.terms[0].unit_cap = 12  # hand-edited: Fall 2026 now exceeds its own cap
    assert any(p.startswith("Fall 2026:") and "exceeds cap 12" in p for p in validate_plan(over, alex, CAT))


@pytest.mark.req("FR-06", "FR-07", "FR-11")
def test_rebuilt_terms_inherit_the_cap_in_force_there():
    alex = STUDENTS["alex"]
    plan = make_plan(alex)
    plan = apply_scenario(alex, plan, ScenarioEvent(event_type="Change Unit Load", term_label="Spring 2028", unit_load=6))["plan"]
    later = plan.terms[-3].term_label
    plan = apply_scenario(alex, plan, ScenarioEvent(event_type="Change Unit Load", term_label=later, unit_load=18))["plan"]
    r = apply_scenario(alex, plan, ScenarioEvent(event_type="Add Summer", term_label="Summer 2028"))
    caps = {t.term_label: t.unit_cap for t in r["plan"].terms}
    assert caps["Summer 2028"] == 6 and caps["Fall 2028"] == 6 and caps[later] == 18
    check_valid(r["plan"], alex)
