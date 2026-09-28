"""Ingest public CSUSB catalog + roadmap data into planner/catalog.json.

Sources (public, no login; robots.txt checked; 2s between requests; raw copies cached in data/raw/):
  catalog.csusb.edu/coursesaz/{cse,math,phys}/     course units, titles, prerequisites (authoritative)
  catalog.csusb.edu/.../computer-science-bs/       degree requirements (authoritative)
  csusb.edu/.../undergraduate-roadmaps PDFs        recommended sequence + term offerings (authoritative)

Catalog/roadmap disagreements are logged as discrepancies, never silently resolved.

    uv run python scripts/ingest.py            # use cached raw files if present
    uv run python scripts/ingest.py --refresh  # re-download
"""
import html
import json
import random
import re
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import pdfplumber
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "planner" / "catalog.json"
UA = "CSE6550-degree-planner-student-project (academic; low-rate)"
CATALOG = "https://catalog.csusb.edu"
ROADMAPS = "https://www.csusb.edu/sites/default/files/upload/file/2026"
SOURCES = {
    "courses_cse.html": f"{CATALOG}/coursesaz/cse/",
    "courses_math.html": f"{CATALOG}/coursesaz/math/",
    "courses_phys.html": f"{CATALOG}/coursesaz/phys/",
    "program_bs_cs.html": f"{CATALOG}/colleges-schools-departments/natural-sciences/computer-science-engineering/computer-science-bs/",
    "roadmap_bs_cs_freshman.pdf": f"{ROADMAPS}/BS%20-%20Computer%20Science%20-%20First%20Time%20Freshman%20-%20Roadmap_0.pdf",
    "roadmap_bs_cs_transfer.pdf": f"{ROADMAPS}/BS%20-%20Computer%20Science%20-%20Transfer%20-%20Roadmap_1.pdf",
}
STANDING = {"freshman": 0, "sophomore": 30, "junior": 60, "senior": 90}
UD_STANDING = 60  # assumption: upper-division GE needs junior standing (60 units)

CODE = re.compile(r"\b([A-Z]{2,4})\s(\d{4}[A-Z]?)\b|(?<![\d.])\b(\d{4}[A-Z]?)\b(?!\.\d)")
GRADE = re.compile(r"with an? (?:minimum )?grade of ([A-D][+-]?)(?:\s*\([\d.]+\))? or better", re.I)
CONCURRENT = re.compile(r"\(?\s*(?:as a )?pre-?\s*(?:/|or)\s*co-?req(?:uisite)?\s*\)?|\(\s*co-?requisite\s*\)", re.I)


# ---------- fetching ----------

def fetch(name: str, url: str, refresh: bool) -> Path:
    path = RAW / name
    if path.exists() and not refresh:
        return path
    u = urlparse(url)
    rp = urllib.robotparser.RobotFileParser(f"{u.scheme}://{u.netloc}/robots.txt")
    rp.read()
    if not rp.can_fetch(UA, url):
        sys.exit(f"robots.txt disallows {url}")
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    path.write_bytes(r.content)
    time.sleep(2)
    return path


# ---------- prerequisite text parser ----------

def parse_requisites(text: str, concurrent_all: bool = False) -> tuple[list[dict], int, list[str]]:
    """Parse e.g. 'CSE 2010 with a grade of C or better and MATH 2372'.

    Returns (groups, min_standing_units, notes). Each group is a list of alternatives ORed together;
    groups are ANDed. Alternative = {course, grade_minimum, concurrent_ok}.
    Non-course alternatives (consent, placement, GE completion) become notes.
    """
    text = html.unescape(text).replace("\xa0", " ").strip().rstrip(".")
    groups, standing, notes, subject = [], 0, [], None  # subject carries: "PHYS 2000 and 2000L"
    for part in re.split(r";|,(?!\s*or\b)|\band\b", text):
        part = part.strip(" ,.")
        if not part:
            continue
        grade = (m.group(1).upper() if (m := GRADE.search(part)) else None)
        concurrent = concurrent_all or bool(CONCURRENT.search(part))
        part = CONCURRENT.sub("", GRADE.sub("", part))
        alts = []
        for alt in re.split(r"\bor\b", part):
            codes = []
            for m in CODE.finditer(alt):
                subject = m.group(1) or subject
                num = m.group(2) or m.group(3)
                if subject:
                    codes.append(f"{subject} {num}")
            if codes:
                alts += [{"course": c, "grade_minimum": grade or "D-", "concurrent_ok": concurrent} for c in codes]
            elif alt.strip():
                low = alt.lower()
                for word, units in STANDING.items():
                    if f"{word} standing" in low:
                        standing = max(standing, units)
                notes.append(alt.strip())
        # "A or B" alternatives stay in one group; a comma list with no "or" was already split into groups.
        if alts:
            groups.append(alts)
    return groups, standing, notes


# ---------- catalog course pages ----------

def parse_courses(path: Path) -> list[dict]:
    soup = BeautifulSoup(path.read_text(encoding="utf8"), "html.parser")
    out = []
    for block in soup.select("div.courseblock"):
        title = block.select_one(".coursetitle").get_text(" ").replace("\xa0", " ")
        m = re.match(r"\s*([A-Z]{2,4} \d{4}[A-Z]?)\.\s+(.*?)\.?\s*$", title)
        if not m:
            continue
        cid, name = m.groups()
        units_text = block.select_one(".coursehours").get_text()
        units = [int(u) for u in re.findall(r"\d+", units_text)]
        desc = block.select_one(".courseblockdesc")
        segments = [BeautifulSoup(s, "html.parser").get_text(" ") for s in re.split(r"<br\s*/?>", desc.decode_contents())] if desc else []
        prereq_text = coreq_text = ""
        for seg in segments:
            seg = re.sub(r"\s+", " ", seg.replace("\xa0", " ")).strip()
            if m := re.match(r"(?:Semester )?Prerequisites?:\s*(.*)", seg):
                prereq_text = prereq_text or re.split(r"\.?\s*(?:Quarter|Prerequisite:|Semester Corequisite)", m.group(1))[0]
            if m := re.search(r"Semester Corequisites?:\s*(.*)", seg):
                coreq_text = re.split(r"\.?\s*Quarter", m.group(1))[0]
        groups, standing, notes = parse_requisites(prereq_text)
        cgroups, _, cnotes = parse_requisites(coreq_text, concurrent_all=True)
        ge = re.search(r"Satisfies GE ([^.,;]+)", desc.get_text(" ") if desc else "")
        out.append({
            "id": cid, "title": name, "catalog_units": units[0] if units else 0,
            "variable_units": len(units) > 1, "min_standing_units": standing,
            "ge": ge.group(1).strip() if ge else None,
            "prereq_text": prereq_text.strip(), "coreq_text": coreq_text.strip(),
            "notes": notes + cnotes, "_groups": groups + cgroups,
        })
    return out


# ---------- degree requirements ----------

WORDS = {"three": 3, "six": 6, "nine": 9, "twelve": 12, "fifteen": 15, "eighteen": 18}


def parse_program(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf8"), "html.parser")
    text = soup.get_text(" ")
    groups, current = [], None
    for tr in soup.select("table.sc_courselist tr"):
        cells = [re.sub(r"\s+", " ", c.get_text(" ")).strip() for c in tr.find_all("td")]
        if not cells or not cells[0]:
            continue
        cls = tr.get("class", [])
        first = cells[0]
        if "areaheader" in cls:
            current = {"name": re.sub(r"\s*\(\d+\)", "", first), "all": []}
            groups.append(current)
        elif m := re.match(r"or ([A-Z]{2,4} \d{4}[A-Z]?)", first):
            if isinstance(current["all"][-1], str):
                current["all"][-1] = {"choose": 1, "from": [current["all"][-1]]}
            current["all"][-1]["from"].append(m.group(1))
        elif m := re.match(r"([A-Z]{2,4} \d{4}[A-Z]?)$", first):
            current["all"].append(m.group(1))
        elif m := re.match(r"(\w+) units chosen from ([A-Z]+) (\d)000-level and above", first, re.I):
            groups.append({"name": f"{m.group(2)} Elective", "choose_units": WORDS[m.group(1).lower()],
                           "subject": m.group(2), "min_level": int(m.group(3)) * 1000})
    # Pull inline choice groups out into their own named groups.
    final = []
    for g in groups:
        if "all" in g:
            choices = [c for c in g["all"] if isinstance(c, dict)]
            g["all"] = [c for c in g["all"] if isinstance(c, str)]
            final.append(g)
            final += [{"name": " / ".join(c["from"]), **c} for c in choices]
        else:
            final.append(g)
    total = int(re.search(r"Total units required for graduation:\s*(\d+)", text).group(1))
    code = re.search(r"Program Code:\s*(\w+)", text).group(1)
    return {"code": code, "name": "BS Computer Science", "catalog_total_units": total, "groups": final}


# ---------- roadmaps ----------

def slot(text: str, offered: str, prereq: str, units: str) -> dict:
    text = text.replace("\n", " ").strip()
    off = {"Fall & Spring": "Both", "Fall": "Fall", "Spring": "Spring"}.get(offered.strip(), "Unknown")
    s = {"text": text, "term_offered": off, "prereq_text": prereq.replace("\n", " ").strip(), "units": int(units)}
    if m := re.match(r"([A-Z]{2,4} \d{4}[A-Z]?)(?:\s|\(|$)", text):
        if "," not in text:
            s["course"] = m.group(1)
            return s
    low = text.lower()
    s["kind"] = ("CHOICE" if "," in text else "ELECTIVE" if "elective (cse" in low else "FREE" if "free elective" in low
                 else "GE 1A" if "1a" in low else "GE 1C" if "1c" in low else "GE UD" if "(ud)" in low
                 else "GE LD" if "general education" in low else "OTHER")
    return s


def parse_roadmap(path: Path) -> dict:
    terms, total = [], None
    with pdfplumber.open(path) as pdf:
        for table in pdf.pages[0].extract_tables():
            fall, spring = [], []
            for row in table:
                if row[0] and re.match(r"[A-Z]{2,4} \d|General|Written|Oral|Free|CSE", row[0]) and row[3]:
                    fall.append(slot(row[0], row[1] or "", row[2] or "", row[3]))
                if row[4] and re.match(r"[A-Z]{2,4} \d|General|Written|Oral|Free|CSE", row[4]) and row[7]:
                    spring.append(slot(row[4], row[5] or "", row[6] or "", row[7]))
                if row[5] == "Degree Units Total":
                    total = int(row[7])
            terms += [{"season": "Fall", "slots": fall}, {"season": "Spring", "slots": spring}]
    return {"source": path.name, "terms": terms, "total_units": total}


# ---------- assembly ----------

def build(refresh: bool = False) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    paths = {name: fetch(name, url, refresh) for name, url in SOURCES.items()}
    courses = {c["id"]: c for n in ("cse", "math", "phys") for c in parse_courses(paths[f"courses_{n}.html"])}
    program = parse_program(paths["program_bs_cs.html"])
    roadmaps = {k: parse_roadmap(paths[f"roadmap_bs_cs_{k}.pdf"]) for k in ("freshman", "transfer")}
    discrepancies = []

    # Term offerings come from the roadmaps. If the two roadmaps disagree, take the more restrictive and flag it.
    offered: dict[str, set] = {}
    roadmap_units, roadmap_prereq = {}, {}
    for rm in roadmaps.values():
        for t in rm["terms"]:
            for s in t["slots"]:
                if "course" in s:
                    offered.setdefault(s["course"], set()).add(s["term_offered"])
                    roadmap_units[s["course"]] = s["units"]
                    roadmap_prereq.setdefault(s["course"], s["prereq_text"])
    for cid, offs in offered.items():
        if len(offs) > 1:
            discrepancies.append(f"{cid} term offering: roadmaps disagree ({' vs '.join(sorted(offs))}); using the more restrictive for planning.")

    # GE / free-elective placeholders from the freshman roadmap, sized to the catalog total (catalog wins).
    counts: dict[str, int] = {}
    placeholders = []
    for t in roadmaps["freshman"]["terms"]:
        for s in t["slots"]:
            kind = s.get("kind")
            if kind in ("GE 1A", "GE 1C", "GE LD", "GE UD"):
                counts[kind] = counts.get(kind, 0) + 1
                pid = kind if kind in ("GE 1A", "GE 1C") else f"{kind} {counts[kind]}"
                placeholders.append({"id": pid, "title": s["text"], "catalog_units": s["units"], "term_offered": "Both",
                                     "min_standing_units": UD_STANDING if kind == "GE UD" else 0, "placeholder": True})

    # Elective pool: subject courses at/above min level, not required elsewhere, not consent/GPA-gated,
    # and not graduate (6000+).
    named = {c for g in program["groups"] for c in g.get("all", []) + g.get("from", [])}
    for g in program["groups"]:
        if "choose_units" in g:
            g["from"] = sorted(
                cid for cid, c in courses.items()
                if cid.startswith(g["subject"] + " ") and g["min_level"] <= int(cid.split()[1][:4]) < 6000
                and cid not in named and (c["_groups"] or c["min_standing_units"]) and not c["variable_units"]
                and not re.search(r"consent of the school|grade point|proposal|approval", c["prereq_text"], re.I)
            )
    # Default-plannable electives only: drop ones gated by courses outside required + pool (e.g. CSE 3350).
    required = {c for g in program["groups"] if "choose_units" not in g for c in g.get("all", []) + g.get("from", [])}
    for g in program["groups"]:
        if "choose_units" in g:
            ok = required | set(g["from"])
            g["from"] = [cid for cid in g["from"] if all(any(a["course"] in ok for a in grp) for grp in courses[cid]["_groups"])]
    program_units = (sum(courses[c]["catalog_units"] for g in program["groups"] for c in g.get("all", []))
                     + sum(courses[g["from"][0]]["catalog_units"] for g in program["groups"] if g.get("choose") == 1)
                     + sum(g["choose_units"] for g in program["groups"] if "choose_units" in g))
    ge_units = sum(p["catalog_units"] for p in placeholders)
    free = program["catalog_total_units"] - program_units - ge_units
    if free > 0:
        placeholders.append({"id": "FREE 1", "title": "Free Elective", "catalog_units": free, "term_offered": "Both",
                             "min_standing_units": 0, "placeholder": True})
    program["groups"].append({"name": "General Education & Free Electives", "all": [p["id"] for p in placeholders]})
    program["program_units"] = program_units
    if (rt := roadmaps["freshman"]["total_units"]) != program["catalog_total_units"]:
        discrepancies.append(f"Program total units: freshman roadmap says {rt}, catalog says {program['catalog_total_units']} "
                             f"(catalog wins; free electives sized to {max(free, 0)} units).")

    # Universe = everything the program can schedule. Prereqs outside it are entry-level (placement) assumptions.
    universe = {c for g in program["groups"] for c in g.get("all", []) + g.get("from", [])}
    edges, entry = [], set()
    for cid in sorted(universe):
        c = courses.get(cid)
        if not c:
            continue
        for gi, group in enumerate(c["_groups"]):
            for alt in group:
                edges.append({"from_course": alt["course"], "to_course": cid, "condition": "OR" if len(group) > 1 else "AND",
                              "group": gi, "grade_minimum": alt["grade_minimum"], "concurrent_ok": alt["concurrent_ok"]})
                if alt["course"] not in universe:
                    entry.add(alt["course"])
    # An OR group satisfied by any in-program course does not need its out-of-program alternatives.
    missing = sorted(e for e in entry if e not in courses)
    if missing:
        discrepancies.append(f"Prerequisites reference courses not in fetched catalog pages: {', '.join(missing)}.")

    # Catalog vs roadmap: units and prerequisite course sets.
    for cid, units in sorted(roadmap_units.items()):
        if cid in courses and courses[cid]["catalog_units"] != units:
            discrepancies.append(f"{cid} units: roadmap says {units}, catalog says {courses[cid]['catalog_units']} (catalog wins).")
    for cid, text in sorted(roadmap_prereq.items()):
        if cid not in courses:
            continue
        rm = {a["course"] for g in parse_requisites(text)[0] for a in g}
        cat = {a["course"] for g in courses[cid]["_groups"] for a in g}
        if rm != cat:
            discrepancies.append(f"{cid} prerequisites: roadmap lists {' / '.join(sorted(rm)) or 'none'}, "
                                 f"catalog requires {' / '.join(sorted(cat)) or 'none'} (catalog wins).")

    out_courses = []
    for cid in sorted(universe | entry):
        c = courses.get(cid)
        if not c:
            continue
        offs = offered.get(cid, set())
        term = "Unknown" if not offs else "Both" if offs == {"Both"} else sorted(offs - {"Both", "Unknown"})[0]
        out_courses.append({
            "id": cid, "title": c["title"], "catalog_units": c["catalog_units"], "roadmap_units": roadmap_units.get(cid),
            "term_offered": term, "min_standing_units": c["min_standing_units"], "ge": c["ge"],
            "prereq_text": c["prereq_text"], "coreq_text": c["coreq_text"], "notes": c["notes"],
            "requirement_groups": [g["name"] for g in program["groups"] if cid in g.get("all", []) + g.get("from", [])],
        })
    for p in placeholders:
        out_courses.append({**p, "requirement_groups": ["General Education & Free Electives"]})

    return {
        "_source": "Ingested by scripts/ingest.py from public CSUSB catalog and roadmap pages (2026-27). Raw copies in data/raw/.",
        "sources": SOURCES, "program": program, "roadmaps": roadmaps,
        "courses": out_courses, "edges": edges, "entry_assumed": sorted(entry),
        "discrepancies": discrepancies,
        "assumptions": [
            f"Upper-division GE requires {UD_STANDING} completed units (junior standing).",
            "Prerequisites outside the program (e.g. CSE 1250, MATH 1401) are entry-level placement assumptions.",
            "Courses not on a roadmap have Unknown term offering; the planner allows them and warns.",
            "Units given as a range use the minimum; variable-unit courses are excluded from the elective pool.",
        ],
    }


# ---------- labeled records for the (future) intake guardrail ----------

def labeled_records(catalog: dict, n: int = 40, seed: int = 6550) -> list[dict]:
    """Known-good course records plus deliberately corrupted copies, labeled with the defect."""
    rng = random.Random(seed)
    real = [c for c in catalog["courses"] if not c.get("placeholder")]
    ids = [c["id"] for c in real]
    out = []
    for c in rng.sample(real, min(n, len(real))):
        rec = {k: c[k] for k in ("id", "title", "catalog_units", "term_offered", "prereq_text")}
        out.append({"record": rec, "malformed": False, "defect": None})
        bad, defect = dict(rec), rng.choice(["units", "term", "self_prereq", "unknown_prereq", "empty_title", "bad_id"])
        if defect == "units":
            bad["catalog_units"] = rng.choice([0, 12, -3])
        elif defect == "term":
            bad["term_offered"] = rng.choice(["Winter", "fall-ish", ""])
        elif defect == "self_prereq":
            bad["prereq_text"] = f"{rec['id']} with a grade of C or better"
        elif defect == "unknown_prereq":
            bad["prereq_text"] = f"CSE {rng.randint(7000, 9999)}"
        elif defect == "empty_title":
            bad["title"] = ""
        else:
            bad["id"] = rec["id"].replace(" ", "")[:5] + "?"
        assert bad["id"] in ids or defect == "bad_id"
        out.append({"record": bad, "malformed": True, "defect": defect})
    return out


if __name__ == "__main__":
    data = build(refresh="--refresh" in sys.argv)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf8")
    (ROOT / "data" / "labeled_records.json").write_text(json.dumps(labeled_records(data), indent=1), encoding="utf8")
    print(f"{len(data['courses'])} courses, {len(data['edges'])} prerequisite edges, "
          f"{len(data['discrepancies'])} discrepancies -> {OUT.relative_to(ROOT)}")
    for d in data["discrepancies"]:
        print("  !", d)
