"""The in-browser demo (Pyodide) drives the FastAPI app through planner.browser.handle and ships a bundle built by pages_bundle."""
import asyncio
import json
import zipfile

import pytest

from planner.browser import handle
from scripts import pages_bundle


def call(method, path, query="", body=b"", content_type="application/json"):
    reply = json.loads(asyncio.run(handle(method, path, query, body, content_type)))
    return reply["status"], reply["type"], reply["body"]


def test_handle_matches_the_api():
    status, _, body = call("GET", "/students")
    assert status == 200 and {s["id"] for s in json.loads(body)} >= {"alex"}
    status, _, body = call("POST", "/plan", body=b'{"student_id": "alex"}')
    assert status == 200 and json.loads(body)["timeline"]["graduation_term"] == "Spring 2030"


def test_handle_reports_errors_like_the_server():
    assert call("POST", "/plan", body=b'{"student_id": "nobody"}')[0] == 404
    assert call("POST", "/plan", body=b"not json")[0] == 422


def test_handle_uploads_a_transcript():
    _, kind, sample = call("GET", "/transcript/sample")
    assert kind.startswith("text/plain")
    status, _, body = call("POST", "/transcript", "filename=s.txt", sample.encode(), "text/plain")
    assert status == 200 and json.loads(body)["student"]["id"].startswith("upload-")


NEEDED = ["planner/api.py", "planner/browser.py", "planner/catalog.json", "data/sample_transcript.txt", "networkx/__init__.py"]


@pytest.mark.parametrize("name", NEEDED)
def test_bundle_has_what_the_browser_needs(tmp_path, name):
    out = tmp_path / "planner.zip"
    pages_bundle.build(out)
    names = zipfile.ZipFile(out).namelist()
    assert name in names and not any("/tests/" in n or "__pycache__" in n for n in names)
