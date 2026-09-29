"""Ingest every subject in the CSUSB catalog A-Z (current year) into data/all_courses.json.

Reuses ingest.py's polite fetcher (robots.txt, 2 s spacing, HTTPS-on-csusb.edu only) and course parser.
    uv run python scripts/ingest_all.py [--refresh]
"""
import json
import re
import sys
from datetime import date

from ingest import CATALOG, RAW, ROOT, fetch, parse_courses

OUT = ROOT / "data" / "all_courses.json"
(RAW / "all").mkdir(parents=True, exist_ok=True)


def main(refresh: bool) -> None:
    index = fetch("all/index.html", f"{CATALOG}/coursesaz/", refresh).read_text(encoding="utf8")
    subjects = sorted(set(re.findall(r'href="/coursesaz/([a-z0-9]+)/"', index)))
    courses, failed = {}, []
    for s in subjects:
        try:
            for c in parse_courses(fetch(f"all/{s}.html", f"{CATALOG}/coursesaz/{s}/", refresh)):
                courses[c["id"]] = c
        except Exception as e:  # one bad subject page must not lose the other 83
            failed.append({"subject": s, "error": str(e)})
    for c in courses.values():
        c["_groups"] = [[a["course"] for a in g] for g in c["_groups"]]
    OUT.write_text(json.dumps({"fetched": date.today().isoformat(), "source": CATALOG, "subjects": subjects,
                               "failed": failed, "courses": courses}, indent=1), encoding="utf8")
    print(f"{len(courses)} courses, {len(subjects)} subjects, {len(failed)} failed")


if __name__ == "__main__":
    main("--refresh" in sys.argv)
