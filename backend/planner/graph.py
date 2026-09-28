"""Catalog loading, prerequisite DAG, and bottleneck priority."""
import json
from functools import lru_cache
from pathlib import Path

import networkx as nx

from .models import Course, PrerequisiteEdge, StudentProfile

DATA = Path(__file__).parent


class Catalog:
    def __init__(self, raw: dict):
        self.courses = {c["id"]: Course(**c) for c in raw["courses"]}
        self.discrepancies: list[str] = list(raw.get("discrepancies", []))
        self.discrepancies += [
            f"{c.id} units: roadmap says {c.roadmap_units}, catalog says {c.catalog_units} (catalog wins)."
            for c in self.courses.values() if c.discrepancy_flag
        ]
        self.g = nx.DiGraph()
        self.g.add_nodes_from(self.courses)
        for e in map(PrerequisiteEdge.model_validate, raw["edges"]):
            # A cycle is a data error: block the edge, log it for advisor review.
            if e.to_course == e.from_course or (e.to_course in self.g and nx.has_path(self.g, e.to_course, e.from_course)):
                self.discrepancies.append(f"Rejected prerequisite {e.from_course} -> {e.to_course}: would create a cycle.")
                continue
            self.g.add_edge(e.from_course, e.to_course, edge=e)
        # Priority = direct dependents + longest downstream chain (spec: Planning engine).
        depth = {}
        for n in reversed(list(nx.topological_sort(self.g))):
            depth[n] = max((depth[s] + 1 for s in self.g.successors(n)), default=0)
        self.depth = depth
        # +1 for once-a-year courses: missing the offering costs a full year.
        self.priority = {n: self.g.out_degree(n) + depth[n] + (self.courses[n].term_offered in ("Fall", "Spring"))
                         for n in self.g}

    def prereqs(self, course_id: str) -> list[PrerequisiteEdge]:
        return [d["edge"] for _, _, d in self.g.in_edges(course_id, data=True)]


@lru_cache
def load_catalog() -> Catalog:
    return Catalog(json.loads((DATA / "catalog.json").read_text()))


def load_students() -> dict[str, StudentProfile]:
    return {s["id"]: StudentProfile(**s) for s in json.loads((DATA / "students.json").read_text())}
