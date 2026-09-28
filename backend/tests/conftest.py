import os
import tempfile

# Keep test decisions out of the real audit trail; must run before planner.guardrail is imported.
os.environ["AUDIT_LOG"] = os.path.join(tempfile.mkdtemp(), "audit.jsonl")


def pytest_configure(config):
    config.addinivalue_line("markers", "req(*ids): SRS requirement IDs this test verifies (see docs/TRACEABILITY.md)")
