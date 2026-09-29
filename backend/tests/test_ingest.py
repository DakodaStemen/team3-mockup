"""Prerequisite-text parser checks, using phrasings copied from the live catalog and roadmaps."""
import pytest

from scripts.ingest import parse_requisites


def flat(groups):
    return [[(a["course"], a["grade_minimum"], a["concurrent_ok"]) for a in g] for g in groups]


@pytest.mark.req("DR-02")
def test_grade_and_and():
    g, _, _ = parse_requisites("CSE 2010 with a grade of C or better and MATH 2372")
    assert flat(g) == [[("CSE 2010", "C", False)], [("MATH 2372", "D-", False)]]


@pytest.mark.req("DR-02")
def test_or_with_non_course_alternative():
    g, _, notes = parse_requisites("MATH 1401 or MATH 1403 or satisfactory score on department placement exam")
    assert flat(g) == [[("MATH 1401", "D-", False), ("MATH 1403", "D-", False)]]
    assert notes == ["satisfactory score on department placement exam"]


@pytest.mark.req("DR-02")
def test_c_minus_and_pre_or_coreq():
    g, _, _ = parse_requisites("MATH 2210 with a grade of C- or better; and MATH 2220 as a pre- or co-requisite")
    assert flat(g) == [[("MATH 2210", "C-", False)], [("MATH 2220", "D-", True)]]


@pytest.mark.req("DR-02")
def test_grade_with_gpa_and_q2s_code_ignored():
    g, _, _ = parse_requisites("MATH 2210 or MATH 2120Q2S with a grade of C- (1.7) or better")
    assert flat(g) == [[("MATH 2210", "C-", False)]]


@pytest.mark.req("DR-02")
def test_subject_carry_and_comma_list():
    assert flat(parse_requisites("PHYS 2000 and 2000L")[0]) == [[("PHYS 2000", "D-", False)], [("PHYS 2000L", "D-", False)]]
    assert len(parse_requisites("MATH 2220, PHYS 2500, PHYS 2500L")[0]) == 3


@pytest.mark.req("DR-02")
def test_standing_and_roadmap_coreq():
    assert parse_requisites("Senior Standing")[1] == 90
    g, _, _ = parse_requisites("MATH 2210; MATH 2220 (Corequisite)")
    assert flat(g) == [[("MATH 2210", "D-", False)], [("MATH 2220", "D-", True)]]


@pytest.mark.req("DR-02")
def test_consent_alternative_keeps_courses():
    g, _, notes = parse_requisites("CSE 5300 or CSE 4100 or consent of instructor")
    assert [a["course"] for a in g[0]] == ["CSE 5300", "CSE 4100"] and notes == ["consent of instructor"]


@pytest.mark.req("DR-07")
def test_rebuild_from_cached_sources_matches_committed_catalog():
    import json
    from pathlib import Path

    from scripts.ingest import OUT, build
    assert Path(OUT).exists()
    assert build(refresh=False) == json.loads(Path(OUT).read_text(encoding="utf8"))


class FakeResponse:
    def __init__(self, status=200, body=b"ok", headers=None, text=""):
        self.status_code, self.body, self.headers, self.text = status, body, headers or {}, text

    @property
    def is_redirect(self):
        return self.status_code in (301, 302, 303, 307, 308)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)

    def iter_content(self, n):
        for i in range(0, len(self.body), n):
            yield self.body[i:i + n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def fake_net(monkeypatch, tmp_path):
    """Route ingest's HTTP through a dict of url -> FakeResponse; no network, no 2 s sleeps."""
    from scripts import ingest
    routes: dict[str, FakeResponse] = {}
    monkeypatch.setattr(ingest, "RAW", tmp_path)
    monkeypatch.setattr(ingest, "_robots", {})
    monkeypatch.setattr(ingest.time, "sleep", lambda s: None)
    monkeypatch.setattr(ingest.requests, "get", lambda url, **kw: routes.get(url, FakeResponse(404)))
    return ingest, routes, tmp_path


@pytest.mark.req("DR-07")
def test_fetch_caches_atomically(fake_net):
    ingest, routes, raw = fake_net
    routes["https://catalog.csusb.edu/x/"] = FakeResponse(body=b"page")
    assert ingest.fetch("x.html", "https://catalog.csusb.edu/x/", refresh=True).read_bytes() == b"page"
    assert not list(raw.glob("*.part"))


@pytest.mark.req("DR-07")
@pytest.mark.parametrize("routes_extra,msg", [
    ({"https://catalog.csusb.edu/x/": FakeResponse(302, headers={"Location": "https://evil.example/x"})}, "off-site"),
    ({"https://catalog.csusb.edu/x/": FakeResponse(302, headers={"Location": "http://catalog.csusb.edu/x/"})}, "non-HTTPS"),
    ({"https://catalog.csusb.edu/x/": FakeResponse(body=b"x" * (21 * 2**20))}, "larger than"),
    ({"https://catalog.csusb.edu/robots.txt": FakeResponse(text="User-agent: *\nDisallow: /x/")}, "robots.txt disallows"),
])
def test_fetch_refuses_unsafe_sources(fake_net, routes_extra, msg):
    ingest, routes, raw = fake_net
    routes.update(routes_extra)
    with pytest.raises(SystemExit, match=msg):
        ingest.fetch("x.html", "https://catalog.csusb.edu/x/", refresh=True)
    assert not (raw / "x.html").exists() and not list(raw.glob("*.part"))


@pytest.mark.req("DR-07")
def test_changed_layout_fails_with_a_clear_message(tmp_path):
    from scripts.ingest import parse_program
    page = tmp_path / "p.html"
    page.write_text("<html><body><p>Page redesigned</p></body></html>", encoding="utf8")
    with pytest.raises(ValueError, match="Source layout changed: could not find total units"):
        parse_program(page)
