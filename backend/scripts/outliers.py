"""Outlier report over data/all_courses.json -> results/outliers.json (+ a summary on stdout).

    uv run python scripts/outliers.py
"""
import json
import re
from collections import Counter, defaultdict

from ingest import ROOT

data = json.loads((ROOT / "data" / "all_courses.json").read_text(encoding="utf8"))
courses = data["courses"]
found = defaultdict(list)


def flag(kind: str, cid: str, why: str = "") -> None:
    found[kind].append({"course": cid, "why": why})


graph = {}
for cid, c in courses.items():
    if not c["title"].strip() or len(c["title"]) > 120:
        flag("title", cid, c["title"][:60])
    if c["catalog_units"] == 0:
        flag("zero_units", cid, "catalog lists Units: 0 (thesis/continuation/prep courses)")
    elif c["catalog_units"] > 12:
        flag("high_units", cid, str(c["catalog_units"]))
    if c["variable_units"]:
        flag("variable_units", cid)
    if c["min_standing_units"] > 120:
        flag("standing", cid, str(c["min_standing_units"]))
    if not re.fullmatch(r"[A-Z]{2,4} \d{4}[A-Z]?", cid):
        flag("id_format", cid)
    deps = {a for g in c["_groups"] for a in g}
    graph[cid] = deps
    if cid in deps:  # the parser read "may be taken concurrently with <this course>" as a prerequisite
        flag("self_prereq", cid, c["prereq_text"][:80])
        deps.discard(cid)
    for d in sorted(deps - courses.keys()):
        flag("dangling_prereq", cid, d)
    if c["prereq_text"] and not deps and not c["notes"] and c["min_standing_units"] == 0:
        flag("unparsed_prereq", cid, c["prereq_text"][:80])

# Prerequisite cycles (Tarjan-free DFS: report each back edge once).
state, cycles = {}, []


def dfs(n: str, stack: list[str]) -> None:
    state[n] = 1
    for m in sorted(graph.get(n, ())):
        if m not in graph:
            continue
        if state.get(m) == 1:
            cycles.append(stack[stack.index(m):] + [m] if m in stack else [n, m])
        elif m not in state:
            dfs(m, [*stack, m])
    state[n] = 2


for n in sorted(graph):
    if n not in state:
        dfs(n, [n])
def concurrent(a: str, b: str) -> bool:
    """a lists b as a corequisite / 'may be taken concurrently': a mutual pair, not a real prerequisite loop."""
    t = (courses[a]["coreq_text"] + " " + courses[a]["prereq_text"]).lower()
    return b.lower().split()[-1] in t and ("concurrent" in t or "corequisite" in t or bool(courses[a]["coreq_text"]))


for cyc in cycles:
    kind = "corequisite_pair" if all(concurrent(a, b) for a, b in zip(cyc, cyc[1:], strict=False)) else "prereq_cycle"
    flag(kind, cyc[0], " -> ".join(cyc))

by_units = Counter(c["catalog_units"] for c in courses.values())
report = {"courses": len(courses), "subjects": len(data["subjects"]), "failed_subjects": data["failed"],
          "units_histogram": dict(sorted(by_units.items())), "outliers": {k: v for k, v in sorted(found.items())}}
(ROOT / "results" / "outliers.json").write_text(json.dumps(report, indent=1), encoding="utf8")
print(f"{len(courses)} courses / {len(data['subjects'])} subjects; failed: {len(data['failed'])}")
for k, v in sorted(found.items()):
    print(f"  {k}: {len(v)}  e.g. {v[0]['course']} {v[0]['why']}")
