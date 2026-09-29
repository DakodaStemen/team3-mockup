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
    "ge_program.html": f"{CATALOG}/general-education-program/",
}
# Every current CSE-department roadmap: used only for term-offering evidence (sequence comes from the BS CS ones).
OTHER_ROADMAPS = {
    "bs_ce_freshman": "BS%20-%20Computer%20Engineering%20-%20First%20Time%20Freshman%20-%20Roadmap_0.pdf",
    "bs_ce_transfer": "BS%20-%20Computer%20Engineering%20-%20Transfer%20-%20Roadmap_0.pdf",
    "bs_bioinf_freshman": "BS%20-%20Bioinformatics%20-%20First%20Time%20Freshman%20-%20Roadmap_0.pdf",
    "bs_bioinf_transfer": "BS%20-%20Bioinformatics%20-%20Transfer%20-%20Roadmap_0.pdf",
    "ba_game_freshman": "BA%20-%20Computer%20Systems%20-%20Game%20Development%20Concentration%20-%20First%20Time%20Freshman%20-%20Roadmap.pdf",
    "ba_game_transfer": "BA%20-%20Computer%20Systems%20-%20Game%20Development%20Concentration%20-%20Transfer%20-%20Roadmap.pdf",
    "ba_general_freshman": "BA%20-%20Computer%20Systems%20-%20General%20Interdisciplinary%20Concentration%20-%20First%20Time%20Freshman%20-%20Roadmap.pdf",  # noqa: E501
    "ba_general_transfer": "BA%20-%20Computer%20Systems%20-%20General%20Interdisciplinary%20Concentration%20-%20Transfer%20-%20Roadmap.pdf",
    "ba_sysadmin_freshman": "BA%20-%20Computer%20Systems%20-%20System%20Administration%20Concentration%20-%20First%20Time%20Freshman%20-%20Roadmap.pdf",  # noqa: E501
    "ba_sysadmin_transfer": "BA%20-%20Computer%20Systems%20-%20System%20Administration%20Concentration%20-%20Transfer%20-%20Roadmap.pdf",
}
SOURCES |= {f"roadmap_{k}.pdf": f"{ROADMAPS}/{v}" for k, v in OTHER_ROADMAPS.items()}
# BS CS roadmap GE slots -> catalog GE areas. BS CS is exempt from 1B, 4, 5B (program page); MATH 2210 covers 2,
# PHYS 2500/2500L cover 5A/5C. The 5 remaining lower-division slots are 3A, 3B, 6 and the two American Institutions
# courses (history; California government). The constitution part is met by either (e.g. HIST 1460, PSCI 2030).
GE_SLOTS = {"GE 1A": ["1A"], "GE LD": ["3A", "3B", "6", "AI-HIST", "AI-GOV"], "GE 1C": ["1C"], "GE UD": ["UD-2/5", "UD-3", "UD-4"]}
WORD_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "six": 6}
STANDING = {"freshman": 0, "sophomore": 30, "junior": 60, "senior": 90}
UD_STANDING = 60  # assumption: upper-division GE needs junior standing (60 units)

MAX_BYTES = 20 * 1024 * 1024  # largest raw source is ~1 MB; refuse anything that looks like a bomb or a wrong URL
MAX_REDIRECTS = 5
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}

CODE = re.compile(r"\b([A-Z]{2,4})\s(\d{4}[A-Z]?)\b|(?<![\d.])\b(\d{4}[A-Z]?)\b(?!\.\d)")
GRADE = re.compile(r"with an? (?:minimum )?grade of ([A-D][+-]?)(?:\s*\([\d.]+\))? or better", re.I)
CONCURRENT = re.compile(r"\(?\s*(?:as a )?pre-?\s*(?:/|or)\s*co-?req(?:uisite)?\s*\)?|\(\s*co-?requisite\s*\)", re.I)


# ---------- fetching ----------

def on_site(url: str) -> bool:
    """Only CSUSB hosts over HTTPS; redirects elsewhere are refused."""
    u = urlparse(url)
    return u.scheme == "https" and (u.hostname == "csusb.edu" or (u.hostname or "").endswith(".csusb.edu"))


def robots(url: str) -> urllib.robotparser.RobotFileParser:
    """robots.txt per host, fetched once with our User-Agent and a timeout (RobotFileParser.read() has neither)."""
    u = urlparse(url)
    base = f"{u.scheme}://{u.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser(f"{base}/robots.txt")
        r = requests.get(rp.url, headers={"User-Agent": UA}, timeout=30)
        if r.status_code in (401, 403):
            rp.disallow_all = True
        elif r.status_code >= 400:
            rp.allow_all = True  # no robots.txt: the standard default
        else:
            rp.parse(r.text.splitlines())
        _robots[base] = rp
    return _robots[base]


def fetch(name: str, url: str, refresh: bool) -> Path:
    path = RAW / name
    if path.exists() and not refresh:
        return path
    for _ in range(MAX_REDIRECTS + 1):
        if not on_site(url):
            sys.exit(f"refusing to fetch off-site or non-HTTPS URL {url}")
        if not robots(url).can_fetch(UA, url):
            sys.exit(f"robots.txt disallows {url}")
        with requests.get(url, headers={"User-Agent": UA}, timeout=30, stream=True, allow_redirects=False) as r:
            if r.is_redirect:
                url = requests.compat.urljoin(url, r.headers["Location"])
                continue
            r.raise_for_status()
            data = bytearray()
            for chunk in r.iter_content(64 * 1024):
                data += chunk
                if len(data) > MAX_BYTES:
                    sys.exit(f"{url} is larger than {MAX_BYTES // 2**20} MB; refusing")
        break
    else:
        sys.exit(f"too many redirects fetching {name}")
    tmp = path.with_name(path.name + ".part")  # a failed download never leaves a truncated cache file
    tmp.write_bytes(data)
    tmp.replace(path)
    time.sleep(2)
    return path


def need(pattern: str, text: str, what: str) -> re.Match:
    """re.search that fails with a clear message when a source page's layout has changed."""
    if not (m := re.search(pattern, text)):
        raise ValueError(f"Source layout changed: could not find {what}. Check data/raw/ against the live page.")
    return m


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
        title_el, hours_el = block.select_one(".coursetitle"), block.select_one(".coursehours")
        if not title_el or not hours_el:
            continue
        title = title_el.get_text(" ").replace("\xa0", " ")
        m = re.match(r"\s*([A-Z]{2,4} \d{4}[A-Z]?)\.\s+(.*?)\.?\s*$", title)
        if not m:
            continue
        cid, name = m.groups()
        units_text = hours_el.get_text()
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
        if any(a["course"] == cid for g in groups + cgroups for a in g):
            # "X, which may be taken concurrently with <this course>": a remark about this course, not a prerequisite on itself.
            groups = [g for g in ([a for a in g if a["course"] != cid] for g in groups) if g]
            cgroups = [g for g in ([a for a in g if a["course"] != cid] for g in cgroups) if g]
            notes.append(prereq_text.strip()[:200])
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
    groups, current, ge_covered = [], None, []
    for tr in soup.select("table.sc_courselist tr"):
        cells = [re.sub(r"\s+", " ", c.get_text(" ")).strip() for c in tr.find_all("td")]
        if not cells or not cells[0]:
            continue
        cls = tr.get("class", [])
        first = cells[0]
        if "areaheader" in cls:
            current = {"name": re.sub(r"\s*\(\d+\)", "", first), "all": []}
            groups.append(current)
        elif current is None:
            continue  # rows before the first area header
        elif (m := re.match(r"or ([A-Z]{2,4} \d{4}[A-Z]?)", first)) and current["all"]:
            if isinstance(current["all"][-1], str):
                current["all"][-1] = {"choose": 1, "from": [current["all"][-1]]}
            current["all"][-1]["from"].append(m.group(1))
        elif m := re.match(r"([A-Z]{2,4} \d{4}[A-Z]?)$", first):
            current["all"].append(m.group(1))
            if len(cells) > 1 and "*" in cells[1] and "Upper Division Mathematical" in text:
                ge_covered.append({"course": m.group(1), "area": "UD-2/5"})
        elif m := re.match(r"(\w+) units chosen from ([A-Z]+) (\d)000-level and above", first, re.I):
            n = m.group(1).lower()
            groups.append({"name": f"{m.group(2)} Elective", "choose_units": int(n) if n.isdigit() else WORDS[n],
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
    total = int(need(r"Total units required for graduation:\s*(\d+)", text, "total units").group(1))
    code = need(r"Program Code:\s*(\w+)", text, "program code").group(1)
    return {"code": code, "name": "BS Computer Science", "catalog_total_units": total, "groups": final, "ge_covered_by_major": ge_covered}


# ---------- general education ----------

def parse_ge(path: Path) -> dict:
    """GE areas -> {title, units, min_grade, courses}. American Institutions lists become AI-HIST / AI-GOV / AI-CONST."""
    soup = BeautifulSoup(path.read_text(encoding="utf8"), "html.parser")
    areas = {}
    for table in soup.select("table.sc_courselist"):
        head = re.sub(r"\s+", " ", table.find_previous(["h2", "h3", "h4"]).get_text(" ")).strip()
        note = re.sub(r"\s+", " ", (table.find_previous("p") or soup).get_text(" "))
        rows = [[re.sub(r"\s+", " ", td.get_text(" ")).strip() for td in tr.find_all("td")] for tr in table.select("tr")]
        ids = [c for r in rows if r for c in re.findall(r"[A-Z]{2,4} \d{4}[A-Z]?", r[0])]
        choose = next((r[0] for r in rows if r and r[0].lower().startswith("choose")), "")
        units = WORD_UNITS.get((re.search(r"choose (\w+) unit", choose, re.I) or [None, ""])[1].lower(), 3)
        if m := re.match(r"(?:Area )?(\d[A-C]?|UD-[\d/]+):\s*(.+)", head):
            key, title = m.groups()
        elif head.startswith("History, Constitution"):
            key = "AI-CONST" if "Constitution" in note[:60] else "AI-HIST" if "U.S. History" in note[:60] else "AI-GOV"
            title = {"AI-CONST": "U.S. Constitution", "AI-HIST": "U.S. History", "AI-GOV": "California State & Local Government"}[key]
        else:
            continue  # foundation seminar and designations overlay other areas
        area = areas.setdefault(key, {"title": title, "units": units, "min_grade": "C-" if "C-" in note else "D-", "courses": []})
        area["courses"] += [c for c in ids if c not in area["courses"]]
    return areas


# ---------- roadmaps ----------

def slot(text: str, offered: str, prereq: str, units: str) -> dict:
    text = text.replace("\n", " ").strip()
    off = {"Fall & Spring": "Both", "Fall": "Fall", "Spring": "Spring"}.get(offered.strip(), "Unknown")
    s = {"text": text, "term_offered": off, "prereq_text": prereq.replace("\n", " ").strip(),
         "units": int(m.group()) if (m := re.search(r"\d+", units)) else 0}  # a range like "3-4" uses the minimum
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
                row = [*row, *[None] * (8 - len(row))]  # short rows (merged cells) are padded, not an IndexError
                if row[0] and re.match(r"[A-Z]{2,4} \d|General|Written|Oral|Free|CSE", row[0]) and row[3]:
                    fall.append(slot(row[0], row[1] or "", row[2] or "", row[3]))
                if row[4] and re.match(r"[A-Z]{2,4} \d|General|Written|Oral|Free|CSE", row[4]) and row[7]:
                    spring.append(slot(row[4], row[5] or "", row[6] or "", row[7]))
                if row[5] == "Degree Units Total" and row[7] and row[7].strip().isdigit():
                    total = int(row[7])
            terms += [{"season": "Fall", "slots": fall}, {"season": "Spring", "slots": spring}]
    return {"source": path.name, "terms": terms, "total_units": total}


# ---------- assembly ----------

def build(refresh: bool = False) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    paths = {name: fetch(name, url, refresh) for name, url in SOURCES.items()}
    courses = {c["id"]: c for n in ("cse", "math", "phys") for c in parse_courses(paths[f"courses_{n}.html"])}
    program = parse_program(paths["program_bs_cs.html"])
    ge = parse_ge(paths["ge_program.html"])
    roadmaps = {k: parse_roadmap(paths[f"roadmap_bs_cs_{k}.pdf"]) for k in ("freshman", "transfer")}
    all_roadmaps = {f"bs_cs_{k}": v for k, v in roadmaps.items()} | {k: parse_roadmap(paths[f"roadmap_{k}.pdf"]) for k in OTHER_ROADMAPS}
    discrepancies = []

    # Term offerings: evidence from every CSE-department roadmap. Sequence, units and prerequisites: BS CS roadmaps only.
    offered: dict[str, dict[str, str]] = {}
    roadmap_units, roadmap_prereq = {}, {}
    for key, rm in all_roadmaps.items():
        for t in rm["terms"]:
            for s in t["slots"]:
                if "course" not in s:
                    continue
                if s["term_offered"] != "Unknown":
                    offered.setdefault(s["course"], {})[key] = s["term_offered"]
                if key.startswith("bs_cs"):
                    roadmap_units[s["course"]] = s["units"]
                    roadmap_prereq.setdefault(s["course"], s["prereq_text"])

    def offering(cid: str) -> tuple[str, str]:
        """(pattern, confidence). Conflicting roadmaps -> most restrictive pattern, low confidence."""
        offs = set(offered.get(cid, {}).values())
        if not offs:
            return "Unknown", "unknown"
        if len(offs) == 1:
            return offs.pop(), "high"
        return sorted(offs - {"Both"})[0], "low"

    for cid, by_src in sorted(offered.items()):
        if len(set(by_src.values())) > 1:
            detail = "; ".join(f"{o} in {', '.join(sorted(k for k, v in by_src.items() if v == o))}" for o in sorted(set(by_src.values())))
            discrepancies.append(f"{cid} term offering: roadmaps disagree ({detail}); planning uses the most restrictive, low confidence.")

    # GE: map the BS CS freshman roadmap's GE slots onto catalog GE areas (GE_SLOTS), each satisfiable by the area's courses.
    covered = {g["area"]: g["course"] for g in program.get("ge_covered_by_major", [])}
    placeholders, used = [], {k: 0 for k in GE_SLOTS}
    for t in roadmaps["freshman"]["terms"]:
        for s in t["slots"]:
            kind = s.get("kind")
            if kind not in GE_SLOTS:
                continue
            areas = GE_SLOTS[kind]
            if used[kind] >= len(areas):
                discrepancies.append(f"Freshman roadmap has more {kind} slots than mapped GE areas; extra slot ignored.")
                continue
            area = areas[used[kind]]
            used[kind] += 1
            if area in covered:
                discrepancies.append(f"Freshman roadmap schedules a {kind} slot for GE {area}, but the catalog says {covered[area]} "
                                     f"satisfies GE {area} for this major (catalog wins; slot dropped).")
                continue
            placeholders.append({"id": f"GE {area}", "title": f"GE {area}: {ge[area]['title']}", "catalog_units": ge[area]["units"],
                                 "term_offered": "Both", "offering_confidence": "unknown", "placeholder": True,
                                 "min_standing_units": UD_STANDING if area.startswith("UD") else 0,
                                 "satisfied_by": ge[area]["courses"], "satisfied_by_min_grade": ge[area]["min_grade"]})
    for kind, areas in GE_SLOTS.items():
        if used[kind] != len(areas):
            discrepancies.append(f"Freshman roadmap has {used[kind]} {kind} slots; {len(areas)} GE areas are mapped.")

    # Elective pool: subject courses at/above min level, not required elsewhere, not consent/GPA/proposal-gated,
    # not variable-unit, not graduate (6000+).
    named = {c for g in program["groups"] for c in g.get("all", []) + g.get("from", [])}
    for g in program["groups"]:
        if "choose_units" in g:
            g["from"] = sorted(
                cid for cid, c in courses.items()
                if cid.startswith(g["subject"] + " ") and g["min_level"] <= int(cid.split()[1][:4]) < 6000
                and cid not in named and not c["variable_units"]
                and not re.search(r"consent of the school|grade point|proposal|approval", c["prereq_text"], re.I)
            )
    # Electives gated by a course outside required + pool (e.g. CSE 4030 needs CSE 3350) stay available when that
    # supporting course is itself plannable from required + pool; the engine schedules it when the elective is chosen.
    required = {c for g in program["groups"] if "choose_units" not in g for c in g.get("all", []) + g.get("from", [])}
    supporting = set()
    for g in program["groups"]:
        if "choose_units" not in g:
            continue
        ok = required | set(g["from"])
        keep = []
        for cid in g["from"]:
            need = [grp for grp in courses[cid]["_groups"] if not any(a["course"] in ok for a in grp)]
            fix = [next((a["course"] for a in grp if a["course"] in courses and all(
                any(b["course"] in ok for b in grp2) for grp2 in courses[a["course"]]["_groups"])), None) for grp in need]
            if all(fix):
                keep.append(cid)
                supporting |= set(fix)
        g["from"] = keep
    program_units = (sum(courses[c]["catalog_units"] for g in program["groups"] for c in g.get("all", []))
                     + sum(courses[g["from"][0]]["catalog_units"] for g in program["groups"] if g.get("choose") == 1)
                     + sum(g["choose_units"] for g in program["groups"] if "choose_units" in g))
    ge_units = sum(p["catalog_units"] for p in placeholders)
    free = program["catalog_total_units"] - program_units - ge_units
    if free > 0:
        placeholders.append({"id": "FREE 1", "title": "Free Elective", "catalog_units": free, "term_offered": "Both",
                             "offering_confidence": "unknown", "min_standing_units": 0, "placeholder": True})
    program["groups"].append({"name": "General Education & Free Electives", "all": [p["id"] for p in placeholders]})
    program["program_units"] = program_units
    if (rt := roadmaps["freshman"]["total_units"]) != program["catalog_total_units"]:
        discrepancies.append(f"Program total units: freshman roadmap says {rt}, catalog says {program['catalog_total_units']} "
                             f"(catalog wins: {program_units} major + {ge_units} GE + {max(free, 0)} free elective).")

    # Universe = everything the program can schedule. Prereqs outside it are entry-level (placement) assumptions.
    universe = {c for g in program["groups"] for c in g.get("all", []) + g.get("from", [])} | supporting
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
    missing = sorted(e for e in entry if e not in courses)
    if missing:
        discrepancies.append(f"Prerequisites reference courses not in fetched catalog pages: {', '.join(missing)}.")

    # Catalog vs BS CS roadmaps: units and prerequisite course sets.
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
        term, confidence = offering(cid)
        groups = [g["name"] for g in program["groups"] if cid in g.get("all", []) + g.get("from", [])]
        out_courses.append({
            "id": cid, "title": c["title"], "catalog_units": c["catalog_units"], "roadmap_units": roadmap_units.get(cid),
            "term_offered": term, "offering_confidence": confidence, "offering_evidence": offered.get(cid, {}),
            "min_standing_units": c["min_standing_units"], "ge": c["ge"],
            "prereq_text": c["prereq_text"], "coreq_text": c["coreq_text"], "notes": c["notes"],
            "requirement_groups": groups or (["Supporting prerequisite"] if cid in supporting else []),
        })
    for p in placeholders:
        out_courses.append({**p, "requirement_groups": ["General Education & Free Electives"]})

    return {
        "_source": "Ingested by scripts/ingest.py from public CSUSB catalog, GE, and roadmap pages (2026-27). Raw copies in data/raw/.",
        "sources": SOURCES, "program": program, "roadmaps": roadmaps, "offering_roadmaps": sorted(all_roadmaps),
        "courses": out_courses, "edges": edges, "entry_assumed": sorted(entry), "supporting": sorted(supporting),
        "discrepancies": discrepancies,
        "assumptions": [
            f"Upper-division GE requires {UD_STANDING} completed units (junior standing).",
            "BS CS GE slots map to areas 1A, 1C, 3A, 3B, 6, American Institutions (history; CA government), UD-3, UD-4; "
            "inferred from the program page exemptions and the roadmap slot count. The U.S. Constitution part is assumed met "
            "by the history or government course (true for HIST 1460 and PSCI 2030).",
            "Prerequisites outside the program (e.g. CSE 1250, MATH 1401) are entry-level placement assumptions.",
            "Courses on no roadmap have Unknown offering (allowed with a warning). Summer offerings are never published: "
            "summer placements are allowed only when the student adds a summer term, and are flagged unconfirmed.",
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
