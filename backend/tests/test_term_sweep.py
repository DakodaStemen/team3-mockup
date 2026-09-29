"""Exhaustive term sweep: every student x every course x every event, with Summer and Winter opted in.

Where test_fuzz samples, this enumerates. Every resulting plan must keep the fuzz invariants, and every placed course
must be offered in the season it lands in, so the intersession terms and the offering data tie together exactly.
"""
import pytest

from planner.engine import _off_term_options, apply_scenario, make_plan
from planner.models import ScenarioEvent
from tests.test_fuzz import CAT, PROFILES, check


def season_ok(plan):
    for t in plan.terms:
        season = t.term_label.split()[0]
        for c in t.courses:
            off = CAT.courses[c].term_offered
            assert off in ("Both", "Unknown", season) or (t.term_label in plan.credited.values() and plan.credited.get(c) == t.term_label), \
                f"{c} ({off}-only) placed in {t.term_label}"


def run(profile, plan, ev, cap):
    try:
        r = apply_scenario(profile, plan, ev, CAT)
    except ValueError as e:
        assert str(e).endswith((".", ")")), e  # refused with a clear message, never a crash
        return None
    check(r["plan"], profile, cap)
    season_ok(r["plan"])
    return r["plan"]


@pytest.mark.req("FR-22", "FR-23", "FR-24")
@pytest.mark.parametrize("sid", PROFILES)
def test_every_event_on_every_course_ties_out(sid):
    profile = PROFILES[sid]
    base = make_plan(profile, None, CAT)
    cap = base.unit_cap
    check(base, profile, cap)
    season_ok(base)
    opts = [e for e in _off_term_options(base, base.terms[0].term_label)]
    for label in [None, *opts]:  # plain plan, then each single Summer/Winter opted in
        plan = base if label is None else run(profile, base, label, cap)
        if plan is None:
            continue
        for t in plan.terms:
            for c in t.courses:
                for kind in ("Fail", "Withdraw", "Pass"):
                    run(profile, plan, ScenarioEvent(event_type=kind, course_id=c, term_label=t.term_label), cap)
