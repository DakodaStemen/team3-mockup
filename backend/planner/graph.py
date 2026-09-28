"""Catalog loading, prerequisite DAG, requirement resolution, and bottleneck priority."""
import json
from functools import lru_cache
from pathlib import Path

import networkx as nx

from .models import Course, PrerequisiteEdge, StudentProfile

DATA = Path(__file__).parent


class Catalog:
    def __init__(self, raw: dict):
        self.courses = {c["id"]: Course(**c) for c in raw["courses"]}
        self.program: dict = raw.get("program", {"groups": [{"name": "All", "all": list(self.courses)}]})
        self.roadmaps: dict = raw.get("roadmaps", {})
        self.entry_assumed: set[str] = set(raw.get("entry_assumed", []))
        self.discrepancies: list[str] = list(raw.get("discrepancies", []))
        self.g = nx.DiGraph()
        self.g.add_nodes_from(self.courses)
        for e in map(PrerequisiteEdge.model_validate, raw["edges"]):
            # A cycle is a data error: block the edge, log it for advisor review.
            if e.to_course == e.from_course or (e.to_course in self.g and e.from_course in self.g
                                                and nx.has_path(self.g, e.to_course, e.from_course)):
                self.discrepancies.append(f"Rejected prerequisite {e.from_course} -> {e.to_course}: would create a cycle.")
                continue
            self.g.add_edge(e.from_course, e.to_course, edge=e)
        # Priority = direct dependents + longest downstream chain (spec: Planning engine),
        # +1 for once-a-year courses: missing the offering costs a full year.
        depth = {}
        for n in reversed(list(nx.topological_sort(self.g))):
            depth[n] = max((depth[s] + 1 for s in self.g.successors(n)), default=0)
        self.depth = depth
        self.priority = {n: self.g.out_degree(n) + depth[n]
                         + (n in self.courses and self.courses[n].term_offered in ("Fall", "Spring"))
                         for n in self.g}

    def prereqs(self, course_id: str) -> list[PrerequisiteEdge]:
        return [d["edge"] for _, _, d in self.g.in_edges(course_id, data=True)]

    def units(self, cid: str) -> int:
        return self.courses[cid].catalog_units if cid in self.courses else 0

    def universe(self) -> set[str]:
        return {c for g in self.program["groups"] for c in g.get("all", []) + g.get("from", [])}

    def required(self, profile: StudentProfile, done: set[str]) -> set[str]:
        """Resolve the program's requirement groups into concrete courses for this student."""
        wanted = profile.remaining_requirement_groups
        out = set()
        for g in self.program["groups"]:
            if wanted is not None and g["name"] not in wanted:
                continue
            if "all" in g:
                out |= set(g["all"])
                continue
            picks = [c for c in profile.choices.get(g["name"], []) if c in g["from"]]
            # Default picks: already-completed first, then least-gated, known offering, lowest number.
            pool = sorted(g["from"], key=lambda c: (c not in done, len(nx.ancestors(self.g, c)),
                                                    self.courses[c].term_offered == "Unknown", c))
            need_n, need_u = g.get("choose", 0), g.get("choose_units", 0)
            for c in pool:
                if len(picks) >= need_n and sum(map(self.units, picks)) >= need_u:
                    break
                if c not in picks:
                    picks.append(c)
            out |= set(picks)
        return out


@lru_cache
def load_catalog() -> Catalog:
    return Catalog(json.loads((DATA / "catalog.json").read_text(encoding="utf8")))


def load_students() -> dict[str, StudentProfile]:
    return {s["id"]: StudentProfile(**s) for s in json.loads((DATA / "students.json").read_text(encoding="utf8"))}
