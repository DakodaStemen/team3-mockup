## What and why
<!-- Summary. Link the issue: Closes #n. Change requests: link the approved CR. -->

**SRS IDs:** <!-- e.g. FR-4, NFR-2 -->

## Author self-check (docs/QUALITY_AND_CM.md §1.4)
- [ ] CI green (ruff, pytest incl. traceability, frontend build)
- [ ] New or changed behavior has a `@pytest.mark.req(...)` test; `scripts/trace.py` re-run
- [ ] SRS / DESIGN (ADR) / CHANGELOG updated if behavior or decisions changed
- [ ] Inputs validated at trust boundaries; LLM/network errors escalate, never guess
- [ ] Catalog stays authoritative; AI does not schedule; discrepancies logged, not resolved
- [ ] No PII, transcripts, secrets, or new outbound network calls

## Reviewer (non-author)
- [ ] Checklist verified; defects raised as "Request changes"
