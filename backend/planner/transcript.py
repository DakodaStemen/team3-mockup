"""Parse an unofficial transcript (PDF, plain text, or CSV) into a StudentProfile with term-by-term history (FR-26).

Tolerant by design: registrar exports differ, so the parser looks for three things line by line and reports
everything it could not place instead of guessing.
- a term header ("Fall 2025", "2025 Fall", "Spring Semester 2026", "Winter Intersession 2027");
- a "transfer" header, after which courses count as transfer credit with no CSUSB term;
- a course row: subject + number ("CSE 2010", "MATH2210", "PHYS 2500L"), then the grade that follows the units
  ("4.00 4.00 B 12.000"), or the last grade-like token on the row. A row with units but no grade is in progress.
Nothing is stored: the profile lives in the API's in-memory session store only.
"""
import csv
import io
import re

from .graph import Catalog, load_catalog
from .models import IN_PROGRESS, PastTerm, StudentProfile

MAX_PDF_PAGES = 30
SEASON = r"(Fall|Spring|Summer|Winter)"
TERM = re.compile(rf"\b{SEASON}\s+(?:Semester\s+|Quarter\s+|Session\s+|Intersession\s+)?(\d{{4}})\b|\b(\d{{4}})\s+{SEASON}\b", re.I)
COURSE = re.compile(r"\b([A-Z]{2,5})\s?-?\s?(\d{3,4}[A-Z]?)\b")
GRADE = r"(A|A-|B\+|B|B-|C\+|C|C-|D\+|D|D-|F|WU|W|NC|CR|P|I|IP|RP|RD|AU|T|TR)"
AFTER_UNITS = re.compile(rf"\b\d{{1,2}}\.\d{{1,3}}(?:\s+\d{{1,2}}\.\d{{1,3}})?\s+{GRADE}(?=\s|$)")
LAST_GRADE = re.compile(rf"(?:^|\s){GRADE}(?=\s*(?:\d+\.\d+)?\s*$)")
UNITS = re.compile(r"\b\d{1,2}\.\d{1,3}\b")
TRANSFER = re.compile(r"transfer|test credit|advanced placement|\bAP\b credit", re.I)
IN_PROGRESS_WORDS = re.compile(r"in progress|enrolled|current", re.I)


def extract_text(data: bytes, filename: str = "") -> str:
    """PDF (by magic bytes or name) via pdfplumber; anything else decoded as UTF-8 text."""
    if data[:5] == b"%PDF-" or filename.lower().endswith(".pdf"):
        try:
            import pdfplumber
        except ImportError as e:  # the in-browser demo has no PDF library
            raise ValueError("PDF upload is not available in this build; upload a text or CSV transcript") from e
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                raise ValueError(f"transcript PDF has {len(pdf.pages)} pages; the limit is {MAX_PDF_PAGES}")
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _term(line: str) -> str | None:
    m = TERM.search(line)
    if not m:
        return None
    season, year = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
    return f"{season.capitalize()} {year}"


def _key(label: str) -> tuple[int, int]:
    season, year = label.split()
    return int(year), ["Winter", "Spring", "Summer", "Fall"].index(season)


def _next_regular(label: str) -> str:
    """The first regular term after `label`: the plan starts there."""
    season, year = label.split()
    return {"Fall": f"Spring {int(year) + 1}", "Winter": f"Spring {year}"}.get(season, f"Fall {year}")


def _known(code: str, cat: Catalog) -> bool:
    return code in cat.courses or any(code in c.satisfied_by for c in cat.courses.values())


def _rows(text: str) -> list[list[str]]:
    """CSV with term/course/grade columns becomes synthetic lines the line parser already understands."""
    head = text.lstrip().splitlines()[0].lower() if text.strip() else ""
    if "," in head and "course" in head and "grade" in head:
        reader = csv.DictReader(io.StringIO(text.strip()))
        cols = {k.lower().strip(): k for k in reader.fieldnames or []}
        term_col = next((cols[k] for k in cols if "term" in k or "semester" in k), None)
        out, last = [], None
        for r in reader:
            term = (r.get(term_col) or "").strip() if term_col else ""
            if term and term != last:
                out.append([term])
                last = term
            out.append([f"{r.get(cols['course'], '')} {r.get(cols.get('units', ''), '') or ''} {r.get(cols['grade'], '')}"])
        return out
    return [[line] for line in text.splitlines()]


def parse(text: str, cat: Catalog | None = None, name: str = "Your transcript (uploaded)") -> tuple[StudentProfile, dict]:
    """Return the profile and a report: terms, course count, unrecognized codes, lines it could not read."""
    cat = cat or load_catalog()
    terms: dict[str, dict[str, str]] = {}
    transfer: dict[str, str] = {}
    unknown, unread = set(), []
    term, in_transfer = None, False
    for (line,) in _rows(text):
        line = " ".join(line.split())
        if not line:
            continue
        if (t := _term(line)) and not COURSE.search(line.replace(t, "")):
            term, in_transfer = t, False
            terms.setdefault(term, {})
            continue
        if TRANSFER.search(line) and not COURSE.search(line):
            in_transfer = True
            continue
        m = COURSE.search(line)
        if not m:
            continue
        code = f"{m.group(1)} {m.group(2)}"
        rest = line[m.end():]
        # With a units column, the grade must follow it: "Computer Science I 4.00" has no grade, not an I.
        g = AFTER_UNITS.search(rest) or (None if UNITS.search(rest) else LAST_GRADE.search(rest))
        grade = g.group(1).upper() if g else (IN_PROGRESS if UNITS.search(rest) or IN_PROGRESS_WORDS.search(rest) else None)
        if grade in ("IP", "RP"):
            grade = IN_PROGRESS
        if grade in ("T", "TR"):
            grade = "TR"
        if not _known(code, cat):
            unknown.add(code)
            continue
        if grade is None:
            unread.append(line[:120])
            continue
        if in_transfer or term is None:
            if grade != IN_PROGRESS:
                transfer[code] = grade
            else:
                unread.append(line[:120])
        else:
            terms[term][code] = grade  # a retake later in the same term list simply overwrites
    ordered = sorted((t for t in terms if terms[t]), key=_key)
    # Only the last term may still be in progress; an ungraded row in an earlier term is unreadable, not current.
    for t in ordered[:-1]:
        for code in [c for c, gr in terms[t].items() if gr == IN_PROGRESS]:
            unread.append(f"{code} in {t}: no grade")
            del terms[t][code]
    history = [PastTerm(term_label=t, grades=terms[t]) for t in ordered if terms[t]]
    start = _next_regular(history[-1].term_label) if history else "Fall 2026"
    loads = [sum(cat.units(c) for c in h.grades) for h in history if h.term_label.split()[0] in ("Fall", "Spring")]
    pref = min(18, max(12, round(sum(loads) / len(loads)))) if loads else 15
    profile = StudentProfile(id="upload", name=name, completed_courses=transfer, history=history, start_term=start,
                             unit_load_preference=pref,
                             notes=f"Parsed from an uploaded transcript: {len(history)} term(s), plan starts {start}.")
    report = {"terms": [h.term_label for h in history], "courses": sum(len(h.grades) for h in history),
              "transfer": sorted(transfer), "unrecognized": sorted(unknown), "unread": unread[:20],
              "start_term": start, "unit_load_preference": pref}
    return profile, report
