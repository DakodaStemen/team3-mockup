# Quality Plan and Configuration Management Plan

> [Docs index](../README.md) · [Verification](verification-strategy.md) · [Quality and CM](quality-and-cm-plan.md) · [Threat analysis](threat-analysis.md)

Two supplementary plans from Sommerville Fig 23.2. §1 follows Ch 24 (quality management); §2 follows Ch 25 (configuration management).

## 1. Quality plan

### 1.1 Quality goals

Of Sommerville's quality attributes (Fig 24.2), these are prioritized for this product:

| Priority | Attribute | Why it matters here | How it's assured |
|---|---|---|---|
| 1 | Correctness / dependability | A wrong plan can cost a student a year | Validator (FR-14), 285-run scenario sweep, fuzz and exhaustive term sweeps, requirements-based tests |
| 2 | Understandability (explainability) | Advisors must be able to defend a plan | Templated explanations (FR-12); discrepancy log (FR-20) |
| 3 | Security / privacy | FERPA; transcript upload | [threat-analysis.md](threat-analysis.md); COM-03 |
| 4 | Maintainability | 5-person team, 10 weeks, handoffs | Standards (§1.2), reviews (§1.3), traceability |
| 5 | Efficiency | Interactive what-ifs | NFR-04 (≤ 2 s, provisional; measured ~1 ms) |
| 6 | Usability | Students, not engineers | NFR-05 usability sessions |

### 1.2 Standards (Sommerville Fig 24.4)

| Product standards | Process standards |
|---|---|
| Requirements document: SRS v0.1 (course template, ISO/IEC/IEEE 29148 tailored; Sommerville Ch 4) plus the [attribute register](../01-product-requirements/requirements-register.md) | Requirements change: CR form, §2.3 |
| Python style: `ruff` rules E, F, I, B (line length 150), in `backend/pyproject.toml` | Code submission: branch → PR → CI green → non-author review → squash merge (§2.1) |
| TypeScript: `tsc` strict build; `oxlint` (`npm run lint`) | Version release process: §2.4 |
| Test format: setup / call / assert, tagged `@pytest.mark.req(...)` | Test recording: [verification-strategy.md §6](verification-strategy.md#6-test-recording-and-defect-handling) |
| Change request form: `.github/ISSUE_TEMPLATE/change_request.yml` (Fig 25.15) | Project plan review: at each milestone ([agile plan §5](../03-planning-risk/agile-engineering-plan.md#5-backlog-and-increments)) |
| Commit messages: imperative summary ≤ 72 chars; body explains *why*; references issue `#n` | Design review: ADR table in [design.md §1](../02-models-architecture/design.md#1-architecture-decision-records) updated in the same PR as the decision |

### 1.3 Review process (Sommerville §24.3.1, adapted to pull requests)

**Pre-review (the author):**

- Open the PR from the template.
- Link the issue and the SRS IDs.
- Self-check against §1.4.
- Make sure CI is green.

**Review (at least one non-author reviewer, async):**

- Read the diff against the checklist.
- Record every issue as a PR comment. Use "Request changes" for defects and "Comment" for suggestions.
- Engine and data changes also need the area owner or backup.

**Post-review:**

- The author resolves or answers every comment.
- The reviewer approves.
- Squash-merge.
- If the review found a missed defect class, add it to §1.4 (Sommerville: "checklists should be regularly updated").

Reviews check the work, not the person (Sommerville §24.3: "support without blame").

### 1.4 Inspection checklist

Adapted from Sommerville Fig 24.8 for Python/TypeScript and this domain. It's embedded in the PR template.

| Fault class | Check |
|---|---|
| Data | Constants named (e.g. `SUMMER_CAP`, `WINTER_CAP`, `REGULAR_MAX`, `ACCEPT`), not magic numbers. Files read and written as UTF-8. No mutation of inputs (FR-15). |
| Control | Every loop terminates (see the 30-term horizon in `place()`). All `event_type` / `term_offered` cases handled. |
| Input/output | External input validated at the trust boundary: API bodies via Pydantic, uploaded transcripts and scraped text via their parsers. |
| Interface | API shapes match design.md §6 (IF-02). Frontend types updated with backend models. |
| Exception management | Network errors are logged and never crash or guess. Scraping failures are logged with the raw source. |
| Domain rules | The catalog wins for units and prerequisites (ADR-02). The engine is deterministic (NFR-08). Discrepancies are logged, never auto-resolved. |
| Traceability | New behavior has a tagged test. The SRS was updated if a requirement changed. `traceability.md` regenerated. |
| Privacy / security | No PII, transcripts, or keys committed. No new outbound network calls beyond the documented sources. |

### 1.5 Quality metrics

Reported at each sprint review (Sommerville §24.5: static and dynamic metrics):

- Tests passing / total, and traceability gaps (target 0).
- Lint findings (target 0).
- Open bugs by severity.
- From `backend/results/summary.md`:
  - Pathway P@term and R@term, and exact-term match vs roadmap.
  - Scenario validity (target 100%).
  - Recalculation time.

## 2. Configuration management plan

### 2.1 Version management

- **Tool:** Git; GitHub public repo `DakodaStemen/team3-mockup`.
- **Codelines:** `main` is the mainline and is always releasable (CI green). Work happens on short-lived branches named `feat/<issue>-<slug>`, `fix/<issue>-<slug>`, `docs/<slug>`, or `data/<slug>`, merged by PR (squash).
- **Rules:**
  - No direct pushes or force-pushes to `main`.
  - Commits reference their issue.
  - Generated artifacts (`catalog.json`, `traceability.md`, `results/`) are committed together with the change that produced them.
  - `backend/data/raw/*` is stored byte-exact (`.gitattributes` `-text`).
- **Enforcement:** GitHub branch protection or rulesets on `main` (required checks + 1 review) are free on this public repo but not yet enabled; until then they are a team standard, checked at review.

### 2.2 System building

- **Reproducible environments:** `backend/uv.lock`, `frontend/package-lock.json`.
- **CI build** (`.github/workflows/ci.yml`, on every push and PR):
  1. Backend: `uv sync --frozen` → `ruff check` → `pytest`. Pytest includes the traceability check and the rebuild-from-cache ingestion check.
  2. Frontend: `npm ci` → `npm run lint` → `npm run build` (`tsc -b && vite build`) → `npm audit --audit-level=high`.
  3. End to end: Playwright starts the API and Vite and drives the real app (`npm run test:e2e`); the report is uploaded when it fails. The job has a 20-minute limit and 60 s per test.

  The workflow runs with read-only permissions, and third-party actions are pinned to commit SHAs.
- **Local build:** the same commands, in the [README](../../README.md#setup-and-run).
- **Data build:** `scripts/ingest.py` (from cache; `--refresh` to re-fetch). `scripts/results.py` regenerates `results/`.

### 2.3 Change management

Sommerville §25.3 and §4.6. The SRS v0.1 baseline (course Week 5) starts change control. Course rule for important artifacts: identify the reason, assess impact, update, keep stable IDs, record the revision, update traceability. After the baseline, any change to a requirement, an ADR, or released behavior goes through this process:

1. **Change request:** open an issue with the *Change request* form. Its fields follow Fig 25.15: requester, requested change, reason, affected SRS IDs, components affected, associated components, assessment, priority, estimated effort.
2. **Analysis and costing:** the area owner assesses impact using [traceability.md](../01-product-requirements/traceability.md) (requirements → tests) and [design.md](../02-models-architecture/design.md) (components).
3. **CCB decision:** the Product Owner, the ScrumMaster, and the affected area owner decide. They weigh the five factors from Sommerville p748:
   - The consequences of *not* making the change.
   - The benefits.
   - The number of users affected.
   - The cost.
   - The release cycle.

   The decision and target release are recorded on the issue.
4. **Record and implement:**
   - Add a CH-nn row to **SRS Appendix A** (the requirements change log) and update the SRS text first.
   - Then open a branch and PR linked to the CR. It updates the register, the affected tests, `traceability.md`, and the CHANGELOG.
   - A worked example is [CH-02](../01-product-requirements/srs-change-proposal-CH-02.md).

Bug fixes that don't change a requirement skip the CCB: use the *Bug report* form and go straight to a PR.

### 2.4 Release management

- **Versioning:** Semantic Versioning `MAJOR.MINOR.PATCH`. Sommerville §25.4 distinguishes major releases (new functionality) from minor releases (repairs). Before 1.0, MINOR marks increments.
- **Release contents:**
  - Tagged source.
  - `backend/planner/catalog.json` with its `data/raw/` sources.
  - Datasets.
  - `results/`.
  - `docs/` at that tag.
- **Process:**
  1. Release candidate tag `vX.Y.Z-rc.N` on `main`.
  2. Release testing per verification-strategy §4, recorded in the release PR.
  3. CHANGELOG entry.
  4. Tag `vX.Y.Z`.
  5. GitHub Release with notes copied from the CHANGELOG.
- **History:** [CHANGELOG.md](../../CHANGELOG.md).
