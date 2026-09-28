"""Deterministic planning engine. The only code that assigns courses to terms."""
import networkx as nx

from .graph import Catalog, load_catalog
from .models import UNIT_LOAD_RANGE, Plan, ScenarioEvent, StudentProfile, TermPlan

GRADE_POINTS = {"A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7, "C+": 2.3, "C": 2.0, "C-": 1.7,
                "D+": 1.3, "D": 1.0, "D-": 0.7, "F": 0.0}
SUMMER_CAP = 8
SEASON_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}


def grade_ok(grade: str, minimum: str) -> bool:
    """False for non-grades like W or NC."""
    return GRADE_POINTS.get(grade.upper(), -1) >= GRADE_POINTS[minimum.upper()]


def term_key(label: str) -> tuple[int, int]:
    season, year = label.split()
    return int(year), SEASON_ORDER[season]


def next_label(label: str, summers: list[str]) -> str:
    season, year = label.split()
    y = int(year)
    if season == "Fall":
        return f"Spring {y + 1}"
    if season == "Spring" and f"Summer {y}" in summers:
        return f"Summer {y}"
    return f"Fall {y}"


def baseline(profile: StudentProfile, cat: Catalog, credited: list[str] = ()) -> tuple[dict[str, str], set[str], int]:
    """Return (satisfied course -> grade, courses still to schedule, units counted toward standing)."""
    sat = {c: "A" for c in cat.entry_assumed}  # entry-level placement assumptions
    earned = profile.transfer_units
    for cid, grade in profile.completed_courses.items():
        if cid not in cat.courses:
            # A real GE course (e.g. ENG 1070A) fills the first open GE slot that lists it.
            slot = next((s.id for s in cat.courses.values() if cid in s.satisfied_by and s.id not in sat
                         and s.id not in profile.completed_courses and grade_ok(grade, s.satisfied_by_min_grade)), None)
            if slot:
                sat[slot] = grade
                earned += cat.units(slot)
            continue
        mins = [d["edge"].grade_minimum for _, _, d in cat.g.out_edges(cid, data=True)]
        # A grade below what a downstream course requires means a retake (e.g. D in CSE 2010 for CSE 2020).
        if grade_ok(grade, "D-") and all(grade_ok(grade, m) for m in mins):
            sat[cid] = grade
            earned += cat.units(cid)
    for c in [*profile.in_progress_courses, *credited]:  # in-progress courses are assumed to pass
        sat[c] = "A"
        earned += cat.units(c)
    done = set(sat) - cat.entry_assumed
    return sat, cat.required(profile, done) - done, earned


def prereqs_met(cid: str, sat: dict[str, str], current: set[str], cat: Catalog) -> bool:
    """Every prerequisite group needs one satisfied alternative; corequisites may be in the current term."""
    groups: dict[int, bool] = {}
    for e in cat.prereqs(cid):
        ok = (e.from_course in sat and grade_ok(sat[e.from_course], e.grade_minimum)) or (
            e.concurrent_ok and e.from_course in current)
        groups[e.group] = groups.get(e.group, False) or ok
    return all(groups.values())


def offered(cid: str, label: str, cat: Catalog) -> bool:
    season, off = label.split()[0], cat.courses[cid].term_offered
    if season == "Summer":
        return off == "Both"
    return off in ("Both", "Unknown", season)


def place(terms: list[TermPlan], todo: set[str], start: int, cap: int, summers: list[str],
          sat: dict[str, str], first_label: str, cat: Catalog, earned: int = 0) -> list[TermPlan]:
    """Constrained greedy topological sort: fill terms[start:] (and new terms) with todo."""
    terms = [t.model_copy(deep=True) for t in terms]
    todo = set(todo)
    sat = dict(sat)
    for t in terms[:start]:
        sat |= {c: "A" for c in t.courses}  # planned courses assumed to meet grade minimums
        earned += sum(map(cat.units, t.courses))
    i = start
    while todo:
        if i - start > 30:
            raise ValueError(f"Cannot schedule {sorted(todo)}: prerequisites or offerings never satisfied.")
        if i == len(terms):
            label = next_label(terms[-1].term_label, summers) if terms else first_label
            terms.append(TermPlan(term_label=label))
        t = terms[i]
        warnings = {}
        term_cap = SUMMER_CAP if t.term_label.startswith("Summer") else cap
        used = sum(map(cat.units, t.courses))
        added = True
        while added:  # repeat so a corequisite placed this term can unlock its partner
            added = False
            ready = sorted((c for c in todo if earned >= cat.courses[c].min_standing_units
                            and prereqs_met(c, sat, set(t.courses), cat)), key=lambda c: (-cat.priority[c], c))
            for c in ready:
                units = cat.units(c)
                if not offered(c, t.term_label, cat):
                    warnings[f"{c} is {cat.courses[c].term_offered}-only; waiting for next offering."] = 1
                elif c in todo and used + units <= term_cap:
                    t.courses.append(c)
                    used += units
                    todo.discard(c)
                    added = True
                    # Pull corequisite partners (e.g. a lab) into the same term before lower-priority courses.
                    for d in sorted(cat.g.successors(c)):
                        if (d in todo and cat.g.edges[c, d]["edge"].concurrent_ok and offered(d, t.term_label, cat)
                                and earned >= cat.courses[d].min_standing_units
                                and prereqs_met(d, sat, set(t.courses), cat) and used + cat.units(d) <= term_cap):
                            t.courses.append(d)
                            used += cat.units(d)
                            todo.discard(d)
        for c in t.courses:
            if t.term_label.startswith("Summer"):
                warnings[f"{c}: summer offerings are not published; confirm it runs in {t.term_label}."] = 1
            elif cat.courses[c].term_offered == "Unknown":
                warnings[f"{c} term offering unknown (on no roadmap); confirm with department."] = 1
            elif cat.courses[c].offering_confidence == "low":
                warnings[f"{c}: roadmaps disagree on its offering; planned as {cat.courses[c].term_offered}-only."] = 1
        t.warnings = list(warnings)
        sat |= {c: "A" for c in t.courses}
        earned += used
        i += 1
    while terms and not terms[-1].courses:
        terms.pop()
    for t in terms:
        t.total_units = sum(map(cat.units, t.courses))
    return terms


def make_plan(profile: StudentProfile, unit_cap: int | None = None, cat: Catalog | None = None) -> Plan:
    cat = cat or load_catalog()
    cap = unit_cap or profile.unit_load_preference
    sat, todo, earned = baseline(profile, cat)
    return Plan(student_id=profile.id, unit_cap=cap,
                terms=place([], todo, 0, cap, [], sat, profile.start_term, cat, earned))


def validate_plan(plan: Plan, profile: StudentProfile, cat: Catalog | None = None,
                  cap: int | None = None, complete: bool = True) -> list[str]:
    """Check any plan (engine-made, hand-edited, or an official roadmap) against catalog rules."""
    cat = cat or load_catalog()
    planned = {c for t in plan.terms for c in t.courses}
    # A credited course still in the plan counts from its own term on, not from before the plan starts.
    sat, todo, earned = baseline(profile, cat, [c for c in plan.credited if c not in planned])
    seen, problems = set(sat), []
    for t in plan.terms:
        here = set(t.courses)
        for c in t.courses:
            if c not in cat.courses:
                problems.append(f"{t.term_label}: {c} is not in the catalog")
                continue
            if not offered(c, t.term_label, cat):
                problems.append(f"{t.term_label}: {c} is {cat.courses[c].term_offered}-only")
            if earned < cat.courses[c].min_standing_units:
                problems.append(f"{t.term_label}: {c} needs {cat.courses[c].min_standing_units} units, has {earned}")
            if not prereqs_met(c, {s: "A" for s in seen} | sat, here, cat):
                problems.append(f"{t.term_label}: {c} prerequisites not met")
        units = max(t.total_units, sum(map(cat.units, t.courses)))  # stated total covers unnamed slots
        if units > (cap or plan.unit_cap):
            problems.append(f"{t.term_label}: {units} units exceeds cap {cap or plan.unit_cap}")
        seen |= here
        earned += units
    if complete and (missing := todo - seen):
        problems.append(f"never scheduled: {', '.join(sorted(missing))}")
    return problems


def timeline(plan: Plan, cat: Catalog | None = None) -> dict:
    cat = cat or load_catalog()
    planned = [c for t in plan.terms for c in t.courses]
    return {
        "graduation_term": plan.terms[-1].term_label if plan.terms else None,
        "term_count": len(plan.terms),
        "total_units": sum(t.total_units for t in plan.terms),
        "critical_path": nx.dag_longest_path(cat.g.subgraph(planned)),
    }


def alternatives(profile: StudentProfile, cat: Catalog | None = None) -> dict:
    out = {}
    for name, cap in [("fastest", 18), ("balanced", 12)]:
        p = make_plan(profile, cap, cat)
        out[name] = {"plan": p, "timeline": timeline(p, cat)}
    return out


def _ordinal(label: str) -> int:
    """Regular-term index; a Summer finish counts as the preceding Spring."""
    year, season = term_key(label)
    return 2 * year + (1 if season == 2 else 0)


def apply_scenario(profile: StudentProfile, plan: Plan, event: ScenarioEvent, cat: Catalog | None = None) -> dict:
    """Recalculate only the part of the plan the event invalidates."""
    cat = cat or load_catalog()
    new = plan.model_copy(deep=True)
    terms = new.terms
    labels = [t.term_label for t in terms]
    cid = event.course_id
    old_cap = plan.unit_cap

    if event.event_type in ("Fail", "Withdraw", "Pass"):
        if cid not in cat.courses:
            raise ValueError(f"Unknown course {cid}")
        if event.term_label not in labels:
            raise ValueError(f"{event.term_label} is not in the plan")
        idx = labels.index(event.term_label)
        if cid not in terms[idx].courses:
            raise ValueError(f"{cid} is not planned in {event.term_label}")
        # Ripple effect = everything reachable from the course in the DAG; nothing else moves.
        planned_after = {c for t in terms[idx:] for c in t.courses}
        invalid = (nx.descendants(cat.g, cid) | {cid}) & planned_after
        if event.event_type == "Pass":
            # The course stays in the term it was passed in; only later terms can use it.
            new.credited.append(cid)
            invalid = {c for c in invalid if c != cid and c not in terms[idx].courses}
        start = idx + 1
        for t in terms[idx:]:
            t.courses = [c for c in t.courses if c not in invalid and (c != cid or event.event_type == "Pass")]
    elif event.event_type == "Add Summer":
        if not event.term_label.startswith("Summer"):
            raise ValueError("Add Summer needs a term_label like 'Summer 2027'")
        new.summers.append(event.term_label)
        start = next((i for i, lbl in enumerate(labels) if term_key(lbl) > term_key(event.term_label)), len(terms))
        invalid = {c for t in terms[start:] for c in t.courses}
        del terms[start:]
    else:  # Change Unit Load
        lo, hi = UNIT_LOAD_RANGE
        if not event.unit_load or not lo <= event.unit_load <= hi:
            raise ValueError(f"Change Unit Load needs unit_load between {lo} and {hi}")
        if event.term_label not in labels:
            raise ValueError(f"{event.term_label} is not in the plan")
        new.unit_cap = event.unit_load
        start = labels.index(event.term_label)
        invalid = {c for t in terms[start:] for c in t.courses}
        del terms[start:]

    planned = {c for t in terms for c in t.courses}
    sat, _, earned = baseline(profile, cat, [c for c in new.credited if c not in planned])  # kept courses count via place()
    # Losing units can also break class-standing gates (e.g. senior standing) on kept later courses.
    run = earned
    for i, t in enumerate(terms):
        if i >= start:
            lost = {c for c in t.courses if run < cat.courses[c].min_standing_units}
            lost |= {d for c in lost for d in nx.descendants(cat.g, c)} & {c for u in terms[i:] for c in u.courses}
            invalid |= lost
            for u in terms[i:]:
                u.courses = [c for c in u.courses if c not in lost]
        run += sum(map(cat.units, t.courses))
    new.terms = place(terms, invalid, start, new.unit_cap, new.summers, sat, profile.start_term, cat, earned)
    before, after = timeline(plan, cat), timeline(new, cat)
    delta = _ordinal(after["graduation_term"]) - _ordinal(before["graduation_term"]) if new.terms and plan.terms else 0

    k = len(invalid - {cid})
    was = {c: t.term_label for t in plan.terms for c in t.courses}
    moved = sum(1 for t in new.terms for c in t.courses if c in was and was[c] != t.term_label)
    cause = {
        "Fail": f"{cid} must be retaken and gates {k} planned course(s)",
        "Withdraw": f"{cid} must be retaken and gates {k} planned course(s)",
        "Pass": f"{cid} passed in {event.term_label}; later terms re-checked, "
                + (f"{moved} course(s) moved" if moved else "no course moved"),
        "Add Summer": f"{event.term_label} adds up to {SUMMER_CAP} units of capacity",
        "Change Unit Load": f"the unit cap changed from {old_cap} to {new.unit_cap}",
    }[event.event_type]
    seasonal = sorted(c for c in invalid if cat.courses[c].term_offered in ("Fall", "Spring"))
    if delta > 0 and seasonal:
        cause += f"; {', '.join(seasonal)} only run{'s' if len(seasonal) == 1 else ''} once a year"
    if delta == 0:
        slack = "" if event.event_type == "Pass" else ", but existing slack absorbs it"
        explanation = f"Graduation unchanged ({after['graduation_term']}): {cause}{slack}."
    else:
        verb = f"delayed by {delta}" if delta > 0 else f"moved up by {-delta}"
        explanation = f"Graduation {verb} term(s) ({before['graduation_term']} → {after['graduation_term']}) because {cause}."
    return {
        "plan": new,
        "timeline": after,
        "invalidated": sorted(invalid),
        "delta_terms": delta,
        "explanation": explanation,
    }
