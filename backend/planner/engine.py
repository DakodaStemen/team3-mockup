"""Deterministic planning engine. The only code that assigns courses to terms."""
import re

import networkx as nx

from .graph import Catalog, load_catalog
from .models import UNIT_LOAD_RANGE, Plan, ScenarioEvent, StudentProfile, TermPlan

GRADE_POINTS = {"A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7, "C+": 2.3, "C": 2.0, "C-": 1.7,
                "D+": 1.3, "D": 1.0, "D-": 0.7, "F": 0.0}
# Unit limits from the Registrar (verified 2026-09-28, CH-03 EV-12; re-read 2026-09-29): fall/spring maximum 18 for
# undergraduates (more needs an approved overload); summer maximum 14 (7 per five-week session); winter intersession
# maximum 4 with no overload. Summer and winter are short, so the engine plans them lighter than their maximums: one
# summer session (7) and one winter course (4). The validator still accepts anything up to the maximum.
REGULAR_MAX = 18
SUMMER_MAX = 14
SUMMER_CAP = 7
WINTER_CAP = 4
OFF_TERM_CAPS = {"Summer": SUMMER_CAP, "Winter": WINTER_CAP}  # planning caps; opt-in, never planned by default
OFF_TERM_MAX = {"Summer": SUMMER_MAX, "Winter": WINTER_CAP}  # published ceilings
# Credit/pass grades carry no letter. Assumption to confirm with an advisor (CH-02 C-8): CSU credit means
# C or better, so CR/P/TR meet any minimum up to C. NC, W, and I never pass.
NO_LETTER_PASS = {"CR", "P", "TR", "CRT"}
NO_LETTER_EQUIV = "C"
SEASON_ORDER = {"Winter": 0, "Spring": 1, "Summer": 2, "Fall": 3}  # Winter YYYY is the January term
HORIZON = 30  # terms place() will try before declaring courses unplaceable
TERM_LABEL = re.compile(r"^(Winter|Spring|Summer|Fall) \d{4}$")


def grade_ok(grade: str, minimum: str) -> bool:
    """False for non-grades like W or NC; CR/P/TR count as NO_LETTER_EQUIV."""
    g = grade.upper()
    points = GRADE_POINTS[NO_LETTER_EQUIV] if g in NO_LETTER_PASS else GRADE_POINTS.get(g, -1)
    return points >= GRADE_POINTS[minimum.upper()]


def term_key(label: str) -> tuple[int, int]:
    season, year = label.split()
    return int(year), SEASON_ORDER[season]


def off_term_cap(label: str) -> int | None:
    """The intersession ceiling for a Summer or Winter term; None for a regular term."""
    return OFF_TERM_CAPS.get(label.split()[0])


def off_term_max(label: str) -> int | None:
    """The published ceiling for a Summer or Winter term (a plan may hold more than the engine plans); None if regular."""
    return OFF_TERM_MAX.get(label.split()[0])


def next_label(label: str, extra: list[str]) -> str:
    """The term after `label`; `extra` lists the Summer/Winter terms the student opted into."""
    season, year = label.split()
    y = int(year)
    if season == "Fall":
        return f"Winter {y + 1}" if f"Winter {y + 1}" in extra else f"Spring {y + 1}"
    if season == "Winter":
        return f"Spring {y}"
    if season == "Spring" and f"Summer {y}" in extra:
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
    if season in OFF_TERM_CAPS:  # intersessions: only courses that run every regular term are candidates
        return off == "Both"
    return off in ("Both", "Unknown", season)


def unplaceable(todo: set[str], sat: dict[str, str], earned: int, cat: Catalog, cap: int) -> str:
    """FR-13: name the courses that block the rest, and the constraint that blocks each one."""
    roots, waiting = [], 0
    for c in sorted(todo):
        groups: dict[int, list[str]] = {}
        for e in cat.prereqs(c):
            groups.setdefault(e.group, []).append(e.from_course)
        missing = [alts for alts in groups.values() if not any(a in sat for a in alts)]
        if any(a in todo for alts in missing for a in alts):
            waiting += 1  # blocked by another unplaced course, reported through that one
        elif missing:
            roots.append(f"{c} needs {' or '.join(missing[0])}, which is neither completed nor plannable")
        elif earned < cat.courses[c].min_standing_units:
            roots.append(f"{c} needs {cat.courses[c].min_standing_units} units of standing")
        else:  # offered() allows every course in some regular term, so it simply ran out of terms
            roots.append(f"{c} did not fit within {HORIZON} terms at a {cap}-unit cap")
    more = f"; {waiting} more course(s) wait on these" if waiting else ""
    return f"Cannot schedule {len(todo)} course(s): {'; '.join(roots) or 'prerequisite cycle'}{more}."


def _cap_at(label: str, caps: list[tuple[tuple[int, int], int]]) -> int | None:
    """Cap in force at a term: the last regular term's cap at or before it (caps sorted by term)."""
    prior = [c for k, c in caps if k <= term_key(label)]
    return prior[-1] if prior else None


def _bundle(c: str, t: TermPlan, todo: set[str], sat: dict[str, str], earned: int, cat: Catalog) -> list[str] | None:
    """c plus its lab when both can go in term t; None when c must wait (a lab only goes in with its lecture)."""
    if any(lab == c and lec in todo for lec, lab in cat.lab_for.items()) or not offered(c, t.term_label, cat):
        return None
    lab = cat.lab_for.get(c)
    if lab not in todo:
        return [c]
    ok = (offered(lab, t.term_label, cat) and earned >= cat.courses[lab].min_standing_units
          and prereqs_met(lab, sat, set(t.courses) | {c}, cat))
    return [c, lab] if ok else None  # the lecture waits for a term its lab can join


def place(terms: list[TermPlan], todo: set[str], start: int, cap: int, extra: list[str],
          sat: dict[str, str], first_label: str, cat: Catalog, earned: int = 0,
          caps: list[tuple[tuple[int, int], int]] = ()) -> list[TermPlan]:
    """Constrained greedy topological sort: fill terms[start:] (and new terms) with todo."""
    terms = [t.model_copy(deep=True) for t in terms]
    todo = set(todo)
    sat = dict(sat)
    for t in terms[:start]:
        sat |= {c: "A" for c in t.courses}  # planned courses assumed to meet grade minimums
        earned += sum(map(cat.units, t.courses))
    if too_big := [c for c in todo if cat.units(c) > cap]:
        c = max(too_big, key=cat.units)
        raise ValueError(f"A {cap}-unit cap can't fit {c} ({cat.units(c)} units); use a cap of at least {cat.units(c)}.")
    i = start
    while todo:
        if i - start > HORIZON:
            raise ValueError(unplaceable(todo, sat, earned, cat, cap))
        if i == len(terms):
            label = next_label(terms[-1].term_label, extra) if terms else first_label
            terms.append(TermPlan(term_label=label, unit_cap=_cap_at(label, caps)))
        t = terms[i]
        warnings = {}
        # A term keeps the cap it was planned under; terms from a Change Unit Load on arrive unstamped.
        term_cap = t.unit_cap or cap
        term_cap = t.unit_cap = min(off, term_cap) if (off := off_term_cap(t.term_label)) else term_cap
        used = sum(map(cat.units, t.courses))
        added = True
        while added:  # repeat so a corequisite placed this term can unlock its partner
            added = False
            ready = sorted((c for c in todo if earned >= cat.courses[c].min_standing_units
                            and prereqs_met(c, sat, set(t.courses), cat)), key=lambda c: (-cat.priority[c], c))
            for c in ready:
                if c not in todo:
                    continue
                if not offered(c, t.term_label, cat):
                    warnings[f"{c} is {cat.courses[c].term_offered}-only; waiting for next offering."] = 1
                if (b := _bundle(c, t, todo, sat, earned, cat)) and used + sum(map(cat.units, b)) <= term_cap:
                    t.courses += b
                    used += sum(map(cat.units, b))
                    todo -= set(b)
                    added = True
                    # Pull corequisite partners into the same term before lower-priority courses.
                    for d in sorted(cat.g.successors(c)):
                        if (d in todo and cat.g.edges[c, d]["edge"].concurrent_ok
                                and earned >= cat.courses[d].min_standing_units
                                and prereqs_met(d, sat, set(t.courses), cat) and (bd := _bundle(d, t, todo, sat, earned, cat))
                                and used + sum(map(cat.units, bd)) <= term_cap):
                            t.courses += bd
                            used += sum(map(cat.units, bd))
                            todo -= set(bd)
        if term_cap > REGULAR_MAX and not off_term_cap(t.term_label):
            warnings[f"A {term_cap}-unit load is above the Registrar's {REGULAR_MAX}-unit maximum; it needs an approved overload."] = 1
        for c in t.courses:
            if off_term_cap(t.term_label):
                season = t.term_label.split()[0].lower()
                warnings[f"{c}: {season} offerings are not published; confirm it runs in {t.term_label}."] = 1
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
    labels = [t.term_label for t in plan.terms]
    problems += [f"{lbl} is not a term label like 'Fall 2027'" for lbl in labels if not TERM_LABEL.match(lbl)]
    ok = [lbl for lbl in labels if TERM_LABEL.match(lbl)]
    if ok != sorted(ok, key=term_key) or len(set(ok)) != len(ok):
        problems.append(f"terms are out of order or repeated: {', '.join(labels)}")
    counts: dict[str, int] = {}
    for c in (c for t in plan.terms for c in t.courses):
        counts[c] = counts.get(c, 0) + 1
    problems += [f"{c} is planned more than once" for c, n in sorted(counts.items()) if n > 1]
    problems += [f"credited course {c} is not in the catalog" for c in sorted(plan.credited) if c not in cat.courses]
    where = {c: t.term_label for t in plan.terms for c in t.courses}
    problems += [f"{lab} must be taken in the same term as {lec} ({where[lec]}), not {where[lab]}"
                 for lec, lab in sorted(cat.lab_for.items()) if lec in where and lab in where and where[lec] != where[lab]
                 and lec not in plan.credited and lab not in plan.credited]  # a passed half may be retaken alone
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
        limit = t.unit_cap or cap or plan.unit_cap
        limit = min(off, limit) if (off := off_term_max(t.term_label)) else limit
        if units > limit:
            problems.append(f"{t.term_label}: {units} units exceeds cap {limit}")
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
    # The preferred load plus whatever Summer/Winter terms finish soonest (FR-24).
    base = make_plan(profile, None, cat)
    if base.terms and (r := recover(profile, base, base.terms[0].term_label, base.terms[0].term_label, cat)):
        out["with summer & winter"] = {"plan": r["plan"], "timeline": r["timeline"], "adds": r["adds"]}
    return out


def moves(before: Plan, after: Plan) -> list[dict]:
    """Courses planned in both, in a different term: {course, from, to}."""
    was = {c: t.term_label for t in before.terms for c in t.courses}
    return [{"course": c, "from": was[c], "to": t.term_label}
            for t in after.terms for c in t.courses if c in was and was[c] != t.term_label]


def terms_later(before: str, after: str) -> int:
    """How many regular terms later `after` finishes than `before` (negative: earlier)."""
    return _ordinal(after) - _ordinal(before)


def _ordinal(label: str) -> int:
    """Regular-term index; a Summer finish counts as the preceding Spring, a Winter finish as the preceding Fall."""
    season, year = label.split()
    return 2 * int(year) + {"Winter": -1, "Spring": 0, "Summer": 0, "Fall": 1}[season]


def _pinned(terms: list[TermPlan], credited: dict[str, str], cat: Catalog) -> set[str]:
    """Passed courses, plus the lab or lecture sharing a term with one: a pinned half keeps its partner (FR-23)."""
    keep = set(credited)
    for t in terms:
        for lec, lab in cat.lab_for.items():
            if lec in t.courses and lab in t.courses and (lec in credited or lab in credited):
                keep |= {lec, lab}
    return keep


def _rebuild_from(terms: list[TermPlan], start: int, credited: set[str] | dict[str, str]) -> set[str]:
    """Clear terms[start:] for re-placement, but keep each pinned course in the term it was passed in."""
    last = max((i for i in range(start, len(terms)) if any(c in credited for c in terms[i].courses)), default=start - 1)
    invalid = {c for t in terms[start:] for c in t.courses if c not in credited}
    for t in terms[start:last + 1]:
        t.courses = [c for c in t.courses if c in credited]
    del terms[last + 1:]
    return invalid


def apply_scenario(profile: StudentProfile, plan: Plan, event: ScenarioEvent, cat: Catalog | None = None) -> dict:
    """Recalculate only the part of the plan the event invalidates."""
    cat = cat or load_catalog()
    new = plan.model_copy(deep=True)
    terms = new.terms
    labels = [t.term_label for t in terms]
    cid = event.course_id
    old_cap = plan.unit_cap
    # Caps already in force by term, so re-created terms keep them instead of taking the latest cap.
    caps = [(term_key(t.term_label), t.unit_cap) for t in terms if t.unit_cap and not off_term_cap(t.term_label)]

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
        # A lab and its lecture move together: a lab pushed out takes its lecture (and what that gates) with it.
        # A lecture already recorded passed stays put; its lab is retaken on its own.
        paired = {lec for lec, lab in cat.lab_for.items() if lab in invalid and lec != cid and lec not in new.credited}
        invalid |= {x for lec in paired for x in nx.descendants(cat.g, lec) | {lec}} & planned_after
        if event.event_type == "Pass":
            # The course stays in the term it was passed in; only later terms can use it.
            new.credited[cid] = event.term_label
            invalid = {c for c in invalid if c != cid and c not in terms[idx].courses and c not in new.credited}
        else:  # a retake revokes any Pass of the course or of anything that depended on it
            for c in invalid:
                new.credited.pop(c, None)
        start = idx + 1
        for t in terms[idx:]:
            t.courses = [c for c in t.courses if c not in invalid and (c != cid or event.event_type == "Pass")]
    elif event.event_type in ("Add Summer", "Add Winter"):
        season = event.event_type.split()[1]
        opted = new.summers if season == "Summer" else new.winters
        if not TERM_LABEL.match(event.term_label) or not event.term_label.startswith(season):
            raise ValueError(f"{event.event_type} needs a term_label like '{season} 2027'")
        if event.term_label in opted:
            raise ValueError(f"{event.term_label} is already in the plan")
        if terms and term_key(event.term_label) < term_key(terms[0].term_label):
            raise ValueError(f"{event.term_label} is before the plan starts ({terms[0].term_label})")
        opted.append(event.term_label)
        start = next((i for i, lbl in enumerate(labels) if term_key(lbl) > term_key(event.term_label)), len(terms))
        invalid = _rebuild_from(terms, start, _pinned(terms, new.credited, cat))
        if len(terms) > start:  # passed courses pinned later terms in place, so insert the summer explicitly
            terms.insert(start, TermPlan(term_label=event.term_label, unit_cap=_cap_at(event.term_label, caps)))
    else:  # Change Unit Load
        lo, hi = UNIT_LOAD_RANGE
        if not event.unit_load or not lo <= event.unit_load <= hi:
            raise ValueError(f"Change Unit Load needs unit_load between {lo} and {hi}")
        if event.term_label not in labels:
            raise ValueError(f"{event.term_label} is not in the plan")
        new.unit_cap = event.unit_load
        start = labels.index(event.term_label)
        invalid = _rebuild_from(terms, start, _pinned(terms, new.credited, cat))
        for t in terms[start:]:
            t.unit_cap = None  # pinned passed-course terms take the new cap
        caps = [(k, c) for k, c in caps if k < term_key(event.term_label)] + [(term_key(event.term_label), event.unit_load)]

    planned = {c for t in terms for c in t.courses}
    sat, _, earned = baseline(profile, cat, [c for c in new.credited if c not in planned])  # kept courses count via place()
    # Losing units can also break class-standing gates (e.g. senior standing) on kept later courses.
    run = earned
    for i, t in enumerate(terms):
        if i >= start:
            lost = {c for c in t.courses if run < cat.courses[c].min_standing_units}
            lost |= {d for c in lost for d in nx.descendants(cat.g, c)} & {c for u in terms[i:] for c in u.courses}
            invalid |= lost
            for c in lost:  # a pass that needed standing the new plan no longer reaches is revoked
                new.credited.pop(c, None)
            for u in terms[i:]:
                u.courses = [c for c in u.courses if c not in lost]
        run += sum(map(cat.units, t.courses))
    new.terms = place(terms, invalid, start, new.unit_cap, new.summers + new.winters, sat, profile.start_term, cat, earned, caps)
    before, after = timeline(plan, cat), timeline(new, cat)
    delta = _ordinal(after["graduation_term"]) - _ordinal(before["graduation_term"]) if new.terms and plan.terms else 0

    k = len(invalid - {cid})
    moved = moves(plan, new)
    if event.event_type == "Pass":
        invalid = {m["course"] for m in moved}  # re-checked courses that stayed put were never invalid
    cause = {
        "Fail": f"{cid} must be retaken and gates {k} planned course(s)",
        "Withdraw": f"{cid} must be retaken and gates {k} planned course(s)",
        "Pass": f"{cid} passed in {event.term_label}; later terms re-checked, "
                + (f"{len(moved)} course(s) moved" if moved else "no course moved"),
        "Add Summer": f"{event.term_label} adds up to {SUMMER_CAP} units of capacity",
        "Add Winter": f"{event.term_label} adds up to {WINTER_CAP} units of capacity",
        "Change Unit Load": f"the unit cap changed from {old_cap} to {new.unit_cap}",
    }[event.event_type]
    seasonal = sorted(c for c in invalid if cat.courses[c].term_offered in ("Fall", "Spring"))
    if delta > 0 and seasonal:
        cause += f"; {', '.join(seasonal)} only run{'s' if len(seasonal) == 1 else ''} once a year"
    if delta == 0:
        slack = "" if event.event_type == "Pass" else ", but existing slack absorbs it"
        explanation = f"Graduation unchanged ({after['graduation_term']}): {cause}{slack}."
    elif delta < 0 and event.event_type in ("Fail", "Withdraw"):
        explanation = (f"Graduation moved up by {-delta} term(s) ({before['graduation_term']} → {after['graduation_term']}): "
                       f"{cause}, and re-placing them filled slack the earlier plan left.")
    else:
        verb = f"delayed by {delta}" if delta > 0 else f"moved up by {-delta}"
        explanation = f"Graduation {verb} term(s) ({before['graduation_term']} → {after['graduation_term']}) because {cause}."
    return {
        "plan": new,
        "timeline": after,
        "invalidated": sorted(invalid),
        "delta_terms": delta,
        "moved": moved,
        "explanation": explanation,
    }


def _off_term_options(plan: Plan, after: str) -> list[ScenarioEvent]:
    """Intersessions the plan could still add from `after` on: a Summer after each Spring, a Winter after each Fall."""
    out = []
    for t in plan.terms[:-1]:  # nothing to catch up after the last term
        season, year = t.term_label.split()
        label = {"Spring": f"Summer {year}", "Fall": f"Winter {int(year) + 1}"}.get(season)
        if label and term_key(label) > term_key(after) and label not in plan.summers + plan.winters:
            out.append(ScenarioEvent(event_type=f"Add {label.split()[0]}", term_label=label))
    return out


def recover(profile: StudentProfile, plan: Plan, target: str, after: str, cat: Catalog | None = None,
            max_adds: int = 4) -> dict | None:
    """Search opt-in Summer/Winter terms that pull graduation back toward `target` (FR-24).

    Greedy: each round adds the single intersession that finishes earliest (ties: fewer terms, then earlier
    label). When no single one helps, it tries every pair, since a retake in Summer can only pay off once a
    Winter opens room for what it unlocks. Returns None when nothing gets closer.
    ponytail: greedy with pair lookahead, not an exhaustive search; ~20 candidates keep it under ~0.5 s.
    """
    cat = cat or load_catalog()
    goal, best, adds = _ordinal(target), plan, []

    def score(p: Plan) -> tuple:
        return _ordinal(p.terms[-1].term_label), term_key(p.terms[-1].term_label), len(p.terms)

    def run(p: Plan, events: list[ScenarioEvent]) -> Plan | None:
        try:
            for ev in events:
                p = apply_scenario(profile, p, ev, cat)["plan"]
            return p
        except ValueError:
            return None

    while len(adds) < max_adds and score(best)[0] > goal:
        options = _off_term_options(best, after)
        tries = [(p, [e]) for e in options if (p := run(best, [e]))]
        if not tries or min(score(p) for p, _ in tries) >= score(best):
            pairs = [[a, b] for i, a in enumerate(options) for b in options[i + 1:]] if len(adds) + 2 <= max_adds else []
            tries = [(p, evs) for evs in pairs if (p := run(best, evs))]
        tries = [(p, evs) for p, evs in tries if score(p) < score(best)]
        if not tries:
            break
        best, evs = min(tries, key=lambda x: (score(x[0]), [term_key(e.term_label) for e in x[1]]))
        adds += evs
    if not adds:
        return None
    labels = sorted((e.term_label for e in adds), key=term_key)
    grad, before = best.terms[-1].term_label, plan.terms[-1].term_label
    if term_key(grad) <= term_key(target):
        status = "back on time"
    elif _ordinal(grad) <= goal:
        status = f"the same academic year as {target}, one intersession later"
    else:
        status = f"{_ordinal(before) - _ordinal(grad)} of {_ordinal(before) - goal} lost term(s) recovered"
    units = sum(t.total_units for t in best.terms if t.term_label in labels)
    return {
        "adds": labels,
        "plan": best,
        "timeline": timeline(best, cat),
        "explanation": f"Adding {' and '.join(labels)} ({units} units) finishes in {grad}: {status}. "
                       "Intersession offerings are unconfirmed; check with the department.",
    }


def course_risk(profile: StudentProfile, plan: Plan, cat: Catalog | None = None) -> dict[str, dict]:
    """Measured bottlenecks (FR-25): for each planned course, the graduation delay if it is failed in its planned
    term, and the opt-in Summer/Winter terms that would win the time back.

    `delay` is in regular terms. `catch_up` lists the intersessions; `after_catch_up` is the delay left once they
    are added (0 = back on time). Placeholder slots (GE, free elective) are skipped: any course can fill them.
    """
    cat = cat or load_catalog()
    if not plan.terms:
        return {}
    grad = plan.terms[-1].term_label
    out = {}
    for t in plan.terms:
        for c in t.courses:
            if c not in cat.courses or cat.courses[c].placeholder or c in plan.credited:
                continue
            try:
                r = apply_scenario(profile, plan, ScenarioEvent(event_type="Fail", course_id=c, term_label=t.term_label), cat)
            except ValueError:
                continue
            rec = recover(profile, r["plan"], grad, t.term_label, cat) if r["delta_terms"] > 0 else None
            out[c] = {"term": t.term_label, "delay": r["delta_terms"], "catch_up": rec["adds"] if rec else [],
                      "after_catch_up": terms_later(grad, rec["timeline"]["graduation_term"]) if rec else r["delta_terms"]}
    return out
