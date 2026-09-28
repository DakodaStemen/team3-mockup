import os
import tempfile

# Keep test decisions out of the real audit trail; must run before planner.guardrail is imported.
os.environ["AUDIT_LOG"] = os.path.join(tempfile.mkdtemp(), "audit.jsonl")
