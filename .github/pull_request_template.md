## What and why
<!-- Summary. Link the issue: Closes #n. Change requests: link the approved CR. -->

**SRS IDs:** <!-- e.g. FR-10, NFR-11 (SRS v0.1 / CH-nn) -->

## Author self-check (docs/04-quality-security-testing/quality-and-cm-plan.md §1.4)
- [ ] CI green (ruff, pytest incl. traceability, frontend build)
- [ ] New or changed behavior has a `@pytest.mark.req(...)` test; `uv run python scripts/trace.py` re-run
- [ ] Requirement changed? SRS updated first (CH-nn in Appendix A), then register; ADR/CHANGELOG updated if decisions or behavior changed
- [ ] Significant AI assistance recorded in docs/05-ai-provenance/ai-engineering-log.md
- [ ] Inputs validated at trust boundaries; network errors are logged, never guessed
- [ ] Catalog stays authoritative; discrepancies logged, not resolved
- [ ] No PII, transcripts, secrets, or new outbound network calls

## Reviewer (non-author)
- [ ] Checklist verified; defects raised as "Request changes"
