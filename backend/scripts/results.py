"""Produce evaluation results in backend/results/ (spec: Measurement and evaluation).

  pathway_quality.json   engine plans vs the official CSUSB roadmaps (precision/recall@term, displacement)
  roadmap_audit.json     the official roadmaps checked against catalog rules
  scenario_runs.csv      every what-if in the sweep: ripple size, graduation delta, recalc vs full-replan time
  bottlenecks.json       priority score vs betweenness centrality vs measured delay when failed
  summary.md             human-readable roll-up

    uv run python scripts/results.py
"""
import csv
import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).parent.parent))
from planner.engine import apply_scenario, make_plan, timeline, validate_plan  # noqa: E402
from planner.graph import load_catalog, load_students  # noqa: E402
from planner.models import Plan, ScenarioEvent, StudentProfile, TermPlan  # noqa: E402

OUT = Path(__file__).parent.parent / "results"
CAT = load_catalog()
STUDENTS = load_students()
EXPECTED = {"alex": "freshman", "taylor": "transfer"}  # synthetic profile -> official roadmap it should match


def token(cid: str) -> str:
    """Compare plans and roadmaps at the level the roadmap specifies (slots, not specific electives)."""
    c = CAT.courses[cid]
    if c.placeholder:
        return re.sub(r" \d+$", "", cid)
    for g in CAT.program["groups"]:
        if cid in g.get("from", []):
            return "CSE ELECTIVE" if "choose_units" in g else "AI CHOICE"
    return cid


def roadmap_tokens(rm: dict) -> list[list[str]]:
    kind = {"ELECTIVE": "CSE ELECTIVE", "CHOICE": "AI CHOICE"}
    return [[s["course"] if "course" in s else kind.get(s["kind"], s["kind"]) for s in t["slots"]] for t in rm["terms"]]


def pr(pred: Counter, gold: Counter) -> tuple[float, float]:
    hit = sum((pred & gold).values())
    return hit / max(sum(pred.values()), 1), hit / max(sum(gold.values()), 1)


def pathway_quality() -> list[dict]:
    rows = []
    for sid, rm_key in EXPECTED.items():
        gold = roadmap_tokens(CAT.roadmaps[rm_key])
        for cap in sorted({STUDENTS[sid].unit_load_preference, 15, 18}):
            plan = make_plan(STUDENTS[sid], cap)
            pred = [[token(c) for c in t.courses] for t in plan.terms]
            per_term, cumulative = [], []
            cp, cg = Counter(), Counter()
            for k in range(max(len(pred), len(gold))):
                p, g = Counter(pred[k] if k < len(pred) else []), Counter(gold[k] if k < len(gold) else [])
                cp, cg = cp + p, cg + g
                per_term.append(pr(p, g))
                cumulative.append(pr(cp, cg))
            gold_idx = {c: k for k, t in enumerate(gold) for c in t if " " in c and c[:4].isupper() and c[-1].isdigit()}
            pred_idx = {c: k for k, t in enumerate(plan.terms) for c in t.courses}
            shared = [c for c in gold_idx if c in pred_idx]
            disp = [pred_idx[c] - gold_idx[c] for c in shared]
            rows.append({
                "student": sid, "roadmap": rm_key, "unit_cap": cap,
                "terms_plan": len(plan.terms), "terms_roadmap": len(gold),
                "precision_at_term": [round(p, 3) for p, _ in per_term], "recall_at_term": [round(r, 3) for _, r in per_term],
                "cumulative_recall_at_term": [round(r, 3) for _, r in cumulative],
                "mean_precision_at_term": round(statistics.mean(p for p, _ in per_term), 3),
                "mean_recall_at_term": round(statistics.mean(r for _, r in per_term), 3),
                "exact_term_match": round(sum(d == 0 for d in disp) / len(disp), 3),
                "mean_abs_displacement_terms": round(statistics.mean(map(abs, disp)), 3),
                "mean_displacement_terms": round(statistics.mean(disp), 3),
                "courses_compared": len(shared),
                "validator_problems": validate_plan(plan, STUDENTS[sid], CAT),
            })
    return rows


def roadmap_audit() -> dict:
    """Treat each official roadmap as a plan and check it against the (authoritative) catalog."""
    out = {}
    for key, rm in CAT.roadmaps.items():
        if key == "transfer":
            profile = STUDENTS["taylor"]
        else:
            profile = StudentProfile(id="roadmap", name="roadmap")
        year, terms = 2026, []
        for t in rm["terms"]:
            label = f"{t['season']} {year if t['season'] == 'Fall' else year + 1}"
            year += t["season"] == "Spring"
            terms.append(TermPlan(term_label=label, courses=[s["course"] for s in t["slots"] if "course" in s],
                                  total_units=sum(s["units"] for s in t["slots"])))
        plan = Plan(student_id=profile.id, unit_cap=99, terms=terms)
        out[key] = validate_plan(plan, profile, CAT, complete=False)
    return out


def scenario_sweep() -> list[dict]:
    rows = []
    for sid, s in STUDENTS.items():
        t0 = time.perf_counter()
        plan = make_plan(s)
        full_ms = (time.perf_counter() - t0) * 1000
        events = [ScenarioEvent(event_type=kind, course_id=c, term_label=t.term_label)
                  for t in plan.terms for c in t.courses if not CAT.courses[c].placeholder for kind in ("Fail", "Withdraw")]
        first = plan.terms[0].term_label
        spring = next((t.term_label for t in plan.terms if t.term_label.startswith("Spring")), None)
        if spring:
            events.append(ScenarioEvent(event_type="Add Summer", term_label=f"Summer {spring.split()[1]}"))
        events += [ScenarioEvent(event_type="Change Unit Load", term_label=first, unit_load=u) for u in (9, 12, 18)]
        events += [ScenarioEvent(event_type="Pass", course_id=c, term_label=t.term_label)
                   for t in plan.terms[1:3] for c in t.courses if not CAT.courses[c].placeholder]
        before = timeline(plan)
        for ev in events:
            t0 = time.perf_counter()
            r = apply_scenario(s, plan, ev)
            ms = (time.perf_counter() - t0) * 1000
            rows.append({
                "student": sid, "event_type": ev.event_type, "course_id": ev.course_id or "", "term": ev.term_label,
                "unit_load": ev.unit_load or "", "invalidated": len(r["invalidated"]), "delta_terms": r["delta_terms"],
                "grad_before": before["graduation_term"], "grad_after": r["timeline"]["graduation_term"],
                "recalc_ms": round(ms, 3), "full_plan_ms": round(full_ms, 3),
                "valid": not validate_plan(r["plan"], s, CAT, cap=max(plan.unit_cap, ev.unit_load or 0)),
                "explanation": r["explanation"],
            })
    return rows


def bottlenecks(runs: list[dict]) -> list[dict]:
    sub = CAT.g.subgraph(CAT.universe())
    between = nx.betweenness_centrality(sub)
    delay = defaultdict(list)
    for r in runs:
        if r["event_type"] == "Fail":
            delay[r["course_id"]].append(r["delta_terms"])
    rows = [{"course": c, "priority": CAT.priority[c], "out_degree": sub.out_degree(c), "depth": CAT.depth[c],
             "descendants": len(nx.descendants(sub, c)), "betweenness": round(between[c], 4),
             "mean_delay_when_failed": round(statistics.mean(delay[c]), 3) if delay[c] else None, "fail_runs": len(delay[c])}
            for c in sub if not CAT.courses[c].placeholder]
    return sorted(rows, key=lambda r: (-r["priority"], r["course"]))


def spearman(a: list[float], b: list[float]) -> float:
    rank = lambda v: {i: r for r, i in enumerate(sorted(range(len(v)), key=v.__getitem__))}
    ra, rb = rank(a), rank(b)
    return statistics.correlation([ra[i] for i in range(len(a))], [rb[i] for i in range(len(b))])


def main():
    OUT.mkdir(exist_ok=True)
    quality, audit, runs = pathway_quality(), roadmap_audit(), scenario_sweep()
    bn = bottlenecks(runs)
    (OUT / "pathway_quality.json").write_text(json.dumps(quality, indent=1))
    (OUT / "roadmap_audit.json").write_text(json.dumps(audit, indent=1))
    (OUT / "bottlenecks.json").write_text(json.dumps(bn, indent=1))
    with (OUT / "scenario_runs.csv").open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(runs[0]))
        w.writeheader()
        w.writerows(runs)

    fails = [r for r in runs if r["event_type"] == "Fail"]
    measured = [r for r in bn if r["mean_delay_when_failed"] is not None]
    rho_p = spearman([r["priority"] for r in measured], [r["mean_delay_when_failed"] for r in measured])
    rho_b = spearman([r["betweenness"] for r in measured], [r["mean_delay_when_failed"] for r in measured])
    rho_d = spearman([r["descendants"] for r in measured], [r["mean_delay_when_failed"] for r in measured])
    speed = [r["full_plan_ms"] / r["recalc_ms"] for r in runs if r["recalc_ms"]]
    L = ["# Results", "", f"Data: {CAT.program['name']} ({CAT.program['code']}), CSUSB 2026-27 catalog + roadmaps. "
         f"{len(CAT.courses)} courses, {CAT.g.number_of_edges()} prerequisite edges, {len(CAT.discrepancies)} discrepancies.", "",
         "## Pathway quality vs official roadmaps", "",
         "| student | roadmap | cap | terms (plan/roadmap) | mean P@term | mean R@term | exact-term match | mean abs displacement | valid |",
         "|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {q['student']} | {q['roadmap']} | {q['unit_cap']} | {q['terms_plan']}/{q['terms_roadmap']} | {q['mean_precision_at_term']} | "
          f"{q['mean_recall_at_term']} | {q['exact_term_match']} | {q['mean_abs_displacement_terms']} | {not q['validator_problems']} |"
          for q in quality]
    L += ["", "## Official roadmaps checked against the catalog", ""]
    for k, probs in audit.items():
        L += [f"- **{k}**: {len(probs)} violation(s)"] + [f"  - {p}" for p in probs]
    L += ["", "## Scenario sweep", "",
          f"- {len(runs)} what-if runs across {len(STUDENTS)} students; **{sum(r['valid'] for r in runs)}/{len(runs)} produced valid plans**.",
          f"- Fail/withdraw delay distribution (terms): {dict(sorted(Counter(r['delta_terms'] for r in fails).items()))}",
          f"- Mean ripple size on Fail: {statistics.mean(r['invalidated'] for r in fails):.1f} courses",
          f"- Recalc time: median {statistics.median(r['recalc_ms'] for r in runs):.2f} ms "
          f"(full plan from scratch: median {statistics.median(r['full_plan_ms'] for r in runs):.2f} ms, "
          f"median ratio {statistics.median(speed):.1f}x)", "",
          "## Bottlenecks", "",
          f"Spearman correlation with measured delay-when-failed ({len(measured)} courses): priority score {rho_p:.2f}, "
          f"descendant count {rho_d:.2f}, betweenness centrality {rho_b:.2f}.", "",
          "| course | priority | descendants | betweenness | mean delay when failed |", "|---|---|---|---|---|"]
    L += [f"| {r['course']} | {r['priority']} | {r['descendants']} | {r['betweenness']} | {r['mean_delay_when_failed']} |" for r in bn[:12]]
    L += ["", "## Discrepancies (catalog vs roadmap)", ""] + [f"- {d}" for d in CAT.discrepancies]
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
