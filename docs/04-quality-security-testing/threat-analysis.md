# Security, Privacy, and Ethics

> [Docs index](../README.md) · [Verification](verification-strategy.md) · [Quality and CM](quality-and-cm-plan.md) · [Threat analysis](threat-analysis.md)

This follows Sommerville Ch 13 (risk-driven security requirements, secure design guidelines) and §1.2 (software engineering ethics).

## 1. Security risk assessment (Sommerville Fig 13.5)

**Assets and exposure:**

| Asset | Value | Exposure if compromised |
|---|---|---|
| Plan correctness (engine and catalog data) | High: students act on plans | A wrong plan can delay graduation. Loss of trust. |
| Student academic records | Very high (FERPA) | Legal liability. **Mitigated by design:** only synthetic profiles exist (COM-03). |
| Ingested sources | Medium | Poisoned or altered data silently changes plans. |

**Threats, attacks, and controls:**

| Threat | Attack | Control | Req |
|---|---|---|---|
| Data poisoning | Altered catalog page or roadmap | Raw sources committed and reviewed as diffs. Rebuild check in CI. Discrepancy log. | FR-20, DR-07 |
| Privacy breach | Real transcripts committed as "test fixtures" | Out of scope by requirement. PR checklist item. Only the synthetic `sample_transcript.txt` is in the repo. | COM-03 |
| Privacy breach | A real transcript uploaded through the UI (FR-26) | The file is parsed in memory and never written to disk. The profile is kept in process memory only (newest 200, cleared on restart), keyed by a random id. Its contents are never logged. The UI says "not saved". **Open decision:** CH-04 §C-1 (real records vs SRS non-goals and DR-05). FERPA applies to any deployment (CH-04 §C-2). | FR-26, ADR-15 |
| Malicious upload | Oversized file, PDF bomb, or crafted text | Body capped at 1 MB (413), PDF capped at 30 pages, parse errors return a generic 422 without echoing the contents, unreadable lines are reported rather than guessed | FR-26, NFR-03 |
| Malformed or hostile API input | Oversized or malformed bodies, out-of-range values, control characters | Strict Pydantic models (`KnownPlan`, `EventIn`), size bounds on every list and string, body limit, security response headers | NFR-03 |
| Abusive scraping / legal | Crawling beyond public pages, or too fast | robots.txt check, a 2 s delay, an identifying user agent, and a fixed source list | COM-04 |

**Misuse cases:**

- *Someone commits a classmate's transcript as a "test fixture":* blocked by COM-03 and the review checklist.
- *Someone uploads a real transcript to the running app:* nothing is persisted, but the profile sits in memory until restart. This stays open until the team decides CH-04 §C-1.

## 2. Secure design guidelines (Sommerville Fig 13.15) as applied

| # | Guideline | Application |
|---|---|---|
| 1 | Base decisions on an explicit security policy | This document plus COM-03 and COM-04 |
| 2 | Use defense in depth | Strict input models → deterministic engine → preview-only → user must Keep |
| 3 | Specify the format of system inputs | Pydantic models at the API (`KnownPlan`, `EventIn`) |
| 4 | Compartmentalize assets | Ingestion is offline, never at request time; the engine takes only validated input |
| 5 | Design for deployment | Local-only defaults; no secrets are required to run |
| 6 | Design for recovery | Plans are stateless (client-held). Catalog rebuildable from committed raw sources. |

## 3. Reporting a vulnerability

The repo is public. Report a suspected issue to the team through a private message to the ScrumMaster, not a public issue. Include the steps and the affected commit.

## 4. Professional ethics (ACM/IEEE Code, Sommerville §1.2)

| Principle | How this project applies it |
|---|---|
| PUBLIC | Plans are advisory, every change is explained, and conflicts go to an advisor rather than being hidden. |
| CLIENT AND EMPLOYER | Use CSUSB's public data only as the spec's legal note allows. Never touch login-gated systems. |
| PRODUCT | Requirements-based testing; results are published even when unflattering (e.g. greedy packs GE late; recalculation is no faster than replanning at this scale). |
| JUDGMENT | The deterministic engine has the final say, and every rule is traceable to the catalog or a requirement. |
| MANAGEMENT | Realistic plan, explicit risk register, owner + backup per area. |
| PROFESSION | Cite prior art and sources (spec; `catalog.json` `sources`). |
| COLLEAGUES | Blameless reviews; knowledge sharing through the required non-author reviews. |
| SELF | Retrospectives each sprint ([agile engineering plan §6](../03-planning-risk/agile-engineering-plan.md#6-schedule-and-ceremonies)). |
