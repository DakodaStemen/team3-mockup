# Documentation index

Everything about the Adaptive Degree Pathway Planner (ADPP) that is not code. The project overview, quick start, and the full artifact table with owners and status are in the [root README](../README.md).

## Start here

| I want to… | Read |
|---|---|
| Understand what the product is and who it is for | [PRODUCT.md](../PRODUCT.md) |
| See how the system is built | [design.md](02-models-architecture/design.md), then the [UML diagrams](02-models-architecture/uml-diagrams.md) |
| Know what is implemented and what is not | [requirements register](01-product-requirements/requirements-register.md) |
| Find the test that proves a requirement | [traceability matrix](01-product-requirements/traceability.md) |
| See what changed and when | [CHANGELOG](../CHANGELOG.md) |
| Run or test the project | [README quick start](../README.md#quick-start) |
| Check the look and feel rules | [DESIGN.md](../DESIGN.md) |

## By folder

| Folder | Contents |
|---|---|
| [01-product-requirements](01-product-requirements/) | [Requirements register](01-product-requirements/requirements-register.md) · [Traceability matrix](01-product-requirements/traceability.md) (generated) · SRS change proposals [CH-02](01-product-requirements/srs-change-proposal-CH-02.md), [CH-03](01-product-requirements/srs-change-proposal-CH-03.md), [CH-04](01-product-requirements/srs-change-proposal-CH-04.md) · [References](01-product-requirements/references.md) · Technical spec (`.docx`) |
| [02-models-architecture](02-models-architecture/) | [design.md](02-models-architecture/design.md): ADRs, system models, 4+1 views, component specs, API contract · [uml-diagrams.md](02-models-architecture/uml-diagrams.md): the five UML views in Mermaid and PlantUML |
| [03-planning-risk](03-planning-risk/) | [Agile engineering plan](03-planning-risk/agile-engineering-plan.md) · [Risk register](03-planning-risk/risk-register.md) |
| [04-quality-security-testing](04-quality-security-testing/) | [Verification strategy](04-quality-security-testing/verification-strategy.md) · [Quality and CM plan](04-quality-security-testing/quality-and-cm-plan.md) · [Threat analysis](04-quality-security-testing/threat-analysis.md) |
| [05-ai-provenance](05-ai-provenance/) | [AI Engineering Log](05-ai-provenance/ai-engineering-log.md) |

## Conventions

- **Requirement IDs** (`FR-`, `NFR-`, `DR-`, `COM-`) come from SRS v0.1 and its proposed changes. IDs are stable; a removed requirement leaves a gap.
- **Status** of each requirement is only in the [register](01-product-requirements/requirements-register.md). The traceability matrix is generated from it: run `uv run python scripts/trace.py` in `backend/` after changing tests or the register.
- **Diagrams** are Mermaid (rendered by GitHub) with PlantUML equivalents in the UML file.
- **Changing an ADR or a requirement** is a change request: see [quality and CM plan §2.3](04-quality-security-testing/quality-and-cm-plan.md#23-change-management).
