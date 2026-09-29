"""FR-26: transcript upload and parsing, including the formats and failures a real upload can bring."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from planner.api import UPLOADS, app
from planner.engine import make_plan, validate_plan
from planner.models import StudentProfile
from planner.transcript import extract_text, parse

SAMPLE = (Path(__file__).parent.parent / "data" / "sample_transcript.txt").read_text(encoding="utf8")
client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.req("FR-26", "DR-04")
def test_sample_transcript_becomes_history_transfer_and_in_progress():
    p, report = parse(SAMPLE)
    assert [h.term_label for h in p.history] == ["Fall 2025", "Winter 2026", "Spring 2026", "Summer 2026", "Fall 2026"]
    assert p.completed_courses["CSE 2010"] == "B"  # the D was retaken; the latest grade counts
    assert p.completed_courses["MATH 2220"] == "C+"  # the W was retaken in summer
    assert p.history[0].grades["CSE 2010"] == "D"  # but the attempt stays in history
    assert p.completed_courses["ENG 1070A"] == "TR" and "ENG 1070A" in report["transfer"]
    assert set(p.in_progress_courses) == {"CSE 2020", "CSE 2130", "MATH 2310"}
    assert report["unrecognized"] == ["BIOL 1000"] and p.start_term == "Spring 2027"
    assert validate_plan(make_plan(p), p) == []


@pytest.mark.req("FR-26")
@pytest.mark.parametrize("text,terms", [
    ("2025 Fall\nCSE 2010 Computer Science I 4.00 4.00 A 16.00\n", ["Fall 2025"]),                    # year first
    ("Spring Semester 2026\nMATH2210 Calculus I 4.0 4.0 B+\n", ["Spring 2026"]),                       # no space in code
    ("term,course,units,grade\nFall 2025,CSE 2010,4,B\nSpring 2026,CSE 2020,4,A-\n", ["Fall 2025", "Spring 2026"]),  # CSV
    ("Winter Intersession 2027\nMATH 2265 Statistics 3.00 3.00 C\n", ["Winter 2027"]),
])
def test_common_layouts_parse(text, terms):
    p, _ = parse(text)
    assert [h.term_label for h in p.history] == terms and all(h.grades for h in p.history)


@pytest.mark.req("FR-26")
def test_titles_with_grade_letters_do_not_become_grades():
    p, _ = parse("Fall 2025\nMATH 2210 Calculus I 4.00 4.00 B 12.000\nPHYS 2500 General Physics I 4.00 4.00 A 16.000\n")
    assert p.history[0].grades == {"MATH 2210": "B", "PHYS 2500": "A"}


@pytest.mark.req("FR-26")
def test_only_the_last_term_may_be_in_progress():
    p, report = parse("Fall 2025\nCSE 2010 Computer Science I 4.00\nSpring 2026\nCSE 2020 Computer Science II 4.00\n")
    assert [h.term_label for h in p.history] == ["Spring 2026"]  # Fall 2025 had only an ungraded row
    assert p.in_progress_courses == ["CSE 2020"] and any("CSE 2010" in u for u in report["unread"])


@pytest.mark.req("FR-26")
def test_quarter_era_and_unknown_courses_are_reported_not_counted():
    p, report = parse("Fall 2018\nCSE 201 Computer Science I 4.0 4.0 A\nART 1001 Drawing 3.00 3.00 A\n")
    assert report["unrecognized"] == ["ART 1001", "CSE 201"] and not p.history


@pytest.mark.req("FR-26", "DR-04")
def test_history_must_be_consistent():
    with pytest.raises(ValueError, match="chronological"):
        StudentProfile(id="x", name="x", history=[{"term_label": "Spring 2026", "grades": {"CSE 2010": "A"}},
                                                  {"term_label": "Fall 2025", "grades": {"MATH 2210": "A"}}])
    with pytest.raises(ValueError, match="disagrees"):
        StudentProfile(id="x", name="x", completed_courses={"CSE 2010": "C"},
                       history=[{"term_label": "Fall 2025", "grades": {"CSE 2010": "A"}}])
    with pytest.raises(ValueError, match="before the plan starts"):
        StudentProfile(id="x", name="x", start_term="Fall 2025", history=[{"term_label": "Fall 2025", "grades": {"CSE 2010": "A"}}])


@pytest.mark.req("FR-26", "NFR-03")
def test_upload_endpoint_round_trip_and_failures():
    r = client.post("/transcript?filename=mine.txt", content=SAMPLE.encode())
    assert r.status_code == 200
    sid = r.json()["student"]["id"]
    assert sid.startswith("upload-") and sid in UPLOADS
    plan = client.post("/plan", json={"student_id": sid}).json()
    assert plan["plan"]["terms"][0]["term_label"] == "Spring 2027"
    assert client.post("/risk", json={"plan": plan["plan"]}).status_code == 200
    assert client.post("/transcript", content=b"").status_code == 400
    assert client.post("/transcript", content=b"just some words").status_code == 422
    bad_pdf = client.post("/transcript?filename=x.pdf", content=b"%PDF-1.4 not really a pdf")
    assert bad_pdf.status_code == 422 and "PDF" in bad_pdf.json()["detail"]
    assert client.post("/transcript", content=b"x" * 1_100_000).status_code == 413


@pytest.mark.req("FR-26")
def test_upload_store_is_bounded():
    for _ in range(3):
        client.post("/transcript", content=SAMPLE.encode())
    from planner.api import MAX_UPLOADS
    assert len(UPLOADS) <= MAX_UPLOADS


def test_extract_text_decodes_non_utf8():
    assert "Fall 2025" in extract_text("Fall 2025 caf\xe9".encode("latin-1"))
