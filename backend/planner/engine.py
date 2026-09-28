"""Deterministic planning engine. The only code that assigns courses to terms."""
import networkx as nx

from .graph import Catalog, load_catalog
from .models import Plan, ScenarioEvent, StudentProfile, TermPlan

GRADES = "FDCBA"
SUMMER_CAP = 8
SEASON_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}


def grade_ok(grade: str, minimum: str) -> bool:
    return GRADES.index(grade[0].upper()) >= GRADES.index(minimum[0].upper())


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


def baseline(profile: StudentProfile, cat: Catalog, credited: list[str] = ()) -> tuple[dict[str, str], set[str]]:
    """Return (satisfied course -> grade, courses still to schedule)."""
    required = {c.id for c in cat.courses.values() if set(c.requirement_groups) & set(profile.remaining_requirement_groups)}
    sat = {}
    for cid, grade in profile.completed_courses.items():
        mins = [d["edge"].grade_minimum for _, _, d in cat.g.out_edges(cid, data=True)]
        # A grade below what a downstream course requires means a retake (e.g. D in CSE 2010).
        if grade_ok(grade, "D") and all(grade_ok(grade, m) for m in mins):
            sat[cid] = grade
    sat |= {c: "A" for c in profile.in_progress_courses}  # assume in-progress courses pass
    sat |= {c: "A" for c in credited}
    return sat, required - set(sat)


def prereqs_met(cid: str, sat: dict[str, str], cat: Catalog) -> bool:
    edges = cat.prereqs(cid)
    ok = lambda e: e.from_course in sat and grade_ok(sat[e.from_course], e.grade_minimum)
    ors = [e for e in edges if e.condition == "OR"]
    return all(ok(e) for e in edges if e.condition == "AND") and (not ors or any(map(ok, ors)))


def offered(cid: str, label: str, cat: Catalog) -> bool:
    season, off = label.split()[0], cat.courses[cid].term_offered
    if season == "Summer":
        return off == "Both"
    return off in ("Both", "Unknown", season)


def place(terms: list[TermPlan], todo: set[str], start: int, cap: int, summers: list[str],
          sat: dict[str, str], first_label: str, cat: Catalog) -> list[TermPlan]:
    """Constrained greedy topological sort: fill terms[start:] (and new terms) with todo."""
    terms = [t.model_copy(deep=True) for t in terms]
    todo = set(todo)
    sat = dict(sat)
    for t in terms[:start]:
        sat |= {c: "A" for c in t.courses}  # planned courses assumed to meet grade minimums
    i = start
    while todo:
        if i - start > 30:
            raise ValueError(f"Cannot schedule {sorted(todo)}: prerequisites or offerings never satisfied.")
        if i == len(terms):
            label = next_label(terms[-1].term_label, summers) if terms else first_label
            terms.append(TermPlan(term_label=label))
        t = terms[i]
        t.warnings = []
        term_cap = SUMMER_CAP if t.term_label.startswith("Summer") else cap
        used = sum(cat.courses[c].catalog_units for c in t.courses)
        ready = sorted((c for c in todo if prereqs_met(c, sat, cat)), key=lambda c: (-cat.priority[c], c))
        for c in ready:
            units = cat.courses[c].catalog_units
            if not offered(c, t.term_label, cat):
                t.warnings.append(f"{c} is {cat.courses[c].term_offered}-only; waiting for next offering.")
            elif used + units <= term_cap:
                t.courses.append(c)
                used += units
                todo.discard(c)
        for c in t.courses:
            if cat.courses[c].term_offered == "Unknown":
                t.warnings.append(f"{c} term offering unknown; confirm with department.")
        sat |= {c: "A" for c in t.courses}
        i += 1
    while terms and not terms[-1].courses:
        terms.pop()
    for t in terms:
        t.total_units = sum(cat.courses[c].catalog_units for c in t.courses)
    return terms


def make_plan(profile: StudentProfile, unit_cap: int | None = None, cat: Catalog | None = None) -> Plan:
    cat = cat or load_catalog()
    cap = unit_cap or profile.unit_load_preference
    sat, todo = baseline(profile, cat)
    return Plan(student_id=profile.id, unit_cap=cap,
                terms=place([], todo, 0, cap, [], sat, profile.start_term, cat))


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
            new.credited.append(cid)
            invalid.discard(cid)
            start = idx
        else:
            start = idx + 1
        for t in terms[idx:]:
            t.courses = [c for c in t.courses if c not in invalid and c != cid]
    elif event.event_type == "Add Summer":
        if not event.term_label.startswith("Summer"):
            raise ValueError("Add Summer needs a term_label like 'Summer 2027'")
        new.summers.append(event.term_label)
        start = next((i for i, l in enumerate(labels) if term_key(l) > term_key(event.term_label)), len(terms))
        invalid = {c for t in terms[start:] for c in t.courses}
        del terms[start:]
    else:  # Change Unit Load
        if not event.unit_load:
            raise ValueError("Change Unit Load needs unit_load")
        if event.term_label not in labels:
            raise ValueError(f"{event.term_label} is not in the plan")
        new.unit_cap = event.unit_load
        start = labels.index(event.term_label)
        invalid = {c for t in terms[start:] for c in t.courses}
        del terms[start:]

    sat, _ = baseline(profile, cat, new.credited)
    new.terms = place(terms, invalid, start, new.unit_cap, new.summers, sat, profile.start_term, cat)
    before, after = timeline(plan, cat), timeline(new, cat)
    delta = _ordinal(after["graduation_term"]) - _ordinal(before["graduation_term"]) if new.terms and plan.terms else 0

    k = len(invalid - {cid})
    cause = {
        "Fail": f"{cid} must be retaken and gates {k} planned course(s)",
        "Withdraw": f"{cid} must be retaken and gates {k} planned course(s)",
        "Pass": f"credit for {cid} lets {k} downstream course(s) be re-sequenced",
        "Add Summer": f"{event.term_label} adds up to {SUMMER_CAP} units of capacity",
        "Change Unit Load": f"the unit cap changed from {old_cap} to {new.unit_cap}",
    }[event.event_type]
    seasonal = sorted(c for c in invalid if cat.courses[c].term_offered in ("Fall", "Spring"))
    if delta > 0 and seasonal:
        cause += f"; {', '.join(seasonal)} only run{'s' if len(seasonal) == 1 else ''} once a year"
    if delta == 0:
        explanation = f"Graduation unchanged ({after['graduation_term']}): {cause}, but existing slack absorbs it."
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
