"""The all-subject catalog dump agrees with the planner's catalog on the courses they share, and has no crashers."""
import json
from pathlib import Path

from planner.graph import load_catalog

ALL = json.loads((Path(__file__).parent.parent / "data" / "all_courses.json").read_text(encoding="utf8"))
CAT = load_catalog()
KNOWN_STALE = [("MATH 3012", "MATH 3011"), ("PHYS 3050L", "PHYS 3040")]


def test_every_subject_ingested():
    assert ALL["failed"] == [] and len(ALL["subjects"]) >= 80 and len(ALL["courses"]) > 3500


def test_shared_courses_agree_with_the_planner_catalog():
    shared = [c for c in CAT.courses.values() if c.id in ALL["courses"] and not c.placeholder]
    assert len(shared) > 40
    for c in shared:
        a = ALL["courses"][c.id]
        assert a["catalog_units"] == c.catalog_units, c.id
        assert a["min_standing_units"] == c.min_standing_units, c.id


def test_no_dangling_prerequisites_in_the_planner_subjects():
    planner_subjects = ("CSE ", "MATH ", "PHYS ")
    bad = [(c, d) for c, v in ALL["courses"].items() if c.startswith(planner_subjects)
           for g in v["_groups"] for d in g if d not in ALL["courses"]]
    # Stale references inside the published catalog itself (the target course no longer exists); neither is on the BS CS path.
    assert sorted(bad) == KNOWN_STALE


def test_no_course_lists_itself_as_a_prerequisite():
    assert [c for c, v in ALL["courses"].items() if any(c in g for g in v["_groups"])] == []
