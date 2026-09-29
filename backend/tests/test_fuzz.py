"""Seeded random what-if chains across every student and every event type, checking invariants after each step.

This is the engine's safety net for combinations no hand-written test names: Summer and Winter terms stacked on
failures and passes, unit-load changes mid-plan, labs, credited courses, recovery, and measured risk.
"""
import random
from pathlib import Path

import pytest

from planner.engine import _off_term_options, apply_scenario, course_risk, make_plan, off_term_cap, recover, term_key, terms_later, validate_plan
from planner.graph import load_catalog, load_students
from planner.models import Plan, ScenarioEvent, StudentProfile, TermPlan
from planner.transcript import parse

CAT = load_catalog()
PROFILES = dict(load_students())
PROFILES["transcript"] = parse((Path(__file__).parent.parent / "data" / "sample_transcript.txt").read_text(encoding="utf8"))[0]


def random_event(rng: random.Random, plan: Plan) -> ScenarioEvent:
    kind = rng.choice(["Fail", "Withdraw", "Pass", "Add Summer", "Add Winter", "Change Unit Load"])
    if kind in ("Add Summer", "Add Winter"):
        options = [e for e in _off_term_options(plan, plan.terms[0].term_label) if e.event_type == kind]
        if options:
            return rng.choice(options)
        kind = "Fail"
    if kind == "Change Unit Load":
        t = rng.choice([t for t in plan.terms if not off_term_cap(t.term_label)])
        return ScenarioEvent(event_type=kind, term_label=t.term_label, unit_load=rng.choice([6, 9, 12, 15, 18, 21]))
    t = rng.choice([t for t in plan.terms if t.courses])
    return ScenarioEvent(event_type=kind, course_id=rng.choice(t.courses), term_label=t.term_label)


def check(plan: Plan, profile: StudentProfile, cap: int):
    labels = [t.term_label for t in plan.terms]
    assert labels == sorted(labels, key=term_key) and len(set(labels)) == len(labels), labels
    assert validate_plan(plan, profile, CAT, cap) == []
    for t in plan.terms:
        season = t.term_label.split()[0]
        if limit := off_term_cap(t.term_label):
            assert t.term_label in (plan.summers if season == "Summer" else plan.winters), f"{t.term_label} not opted in"
            assert t.total_units <= limit, f"{t.term_label}: {t.total_units} > {limit}"
            assert all(CAT.courses[c].term_offered == "Both" for c in t.courses), t.courses
    where = {c: t.term_label for t in plan.terms for c in t.courses}
    for lec, lab in CAT.lab_for.items():
        if lec in where and lab in where and lec not in plan.credited and lab not in plan.credited:
            assert where[lec] == where[lab], f"{lab} in {where[lab]}, {lec} in {where[lec]}"
    for c, term in plan.credited.items():
        if c in where:
            assert where[c] == term, f"passed {c} moved from {term} to {where[c]}"


@pytest.mark.req("FR-03", "FR-07", "FR-09", "FR-10", "FR-11", "FR-22", "FR-23", "FR-24", "NFR-11")
@pytest.mark.parametrize("sid", PROFILES)
@pytest.mark.parametrize("seed", range(6))
def test_random_what_if_chains_keep_every_invariant(sid, seed):
    rng = random.Random(f"{sid}-{seed}")
    profile = PROFILES[sid]
    plan = make_plan(profile, None, CAT)
    cap = plan.unit_cap
    check(plan, profile, cap)
    for _ in range(4):
        before = plan
        ev = random_event(rng, plan)
        try:
            r = apply_scenario(profile, plan, ev, CAT)
        except ValueError as e:  # e.g. a 6-unit cap can't hold a 4+1 lecture and lab together: refused, clearly
            assert str(e).endswith((".", ")")) and len(str(e)) < 400, e
            continue
        plan = r["plan"]
        cap = max(cap, ev.unit_load or 0)
        check(plan, profile, cap)
        assert r["delta_terms"] == terms_later(before.terms[-1].term_label, plan.terms[-1].term_label)
        was = {c: t.term_label for t in before.terms for c in t.courses}
        now = {c: t.term_label for t in plan.terms for c in t.courses}
        assert all(was[m["course"]] == m["from"] and now[m["course"]] == m["to"] for m in r["moved"])
        if r["delta_terms"] > 0 and ev.event_type in ("Fail", "Withdraw"):
            rec = recover(profile, plan, before.terms[-1].term_label, ev.term_label, CAT)
            if rec:
                check(rec["plan"], profile, cap)
                assert term_key(rec["plan"].terms[-1].term_label) < term_key(plan.terms[-1].term_label)
                assert all(term_key(a) > term_key(ev.term_label) for a in rec["adds"])


@pytest.mark.req("FR-25")
@pytest.mark.parametrize("sid", PROFILES)
def test_measured_risk_matches_a_real_failure(sid):
    profile = PROFILES[sid]
    plan = make_plan(profile, None, CAT)
    risk = course_risk(profile, plan, CAT)
    assert all(not CAT.courses[c].placeholder for c in risk)
    for c, r in list(risk.items())[:6]:  # spot-check against a direct replan
        direct = apply_scenario(profile, plan, ScenarioEvent(event_type="Fail", course_id=c, term_label=r["term"]), CAT)
        assert direct["delta_terms"] == r["delay"]
        assert bool(r["catch_up"]) <= (r["delay"] > 0) and r["after_catch_up"] <= r["delay"]


@pytest.mark.req("DR-04")
@pytest.mark.parametrize("sid", [s for s, p in PROFILES.items() if p.history])
def test_each_history_is_a_catalog_valid_sequence(sid):
    """Laid out as a plan for a student with no credit, the history itself must satisfy prerequisites and labs."""
    p = PROFILES[sid]
    transfer = {c: g for c, g in p.completed_courses.items() if not any(c in h.grades for h in p.history)}
    blank = StudentProfile(id="blank", name="blank", completed_courses=transfer, start_term=p.history[0].term_label)
    plan = Plan(student_id="blank", unit_cap=99, summers=[h.term_label for h in p.history if h.term_label.startswith("Summer")],
                winters=[h.term_label for h in p.history if h.term_label.startswith("Winter")],
                terms=[TermPlan(term_label=h.term_label, courses=[c for c in h.grades if c in CAT.courses]) for h in p.history])
    problems = [x for x in validate_plan(plan, blank, CAT, 99, complete=False) if "offerings" not in x]
    # A retaken course appears in two terms; that is history, not a planning error.
    assert [x for x in problems if "more than once" not in x] == []
