# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Versioning: SemVer ([quality and CM plan §2.4](docs/04-quality-security-testing/quality-and-cm-plan.md#24-release-management)).

## [0.1.0] - 2026-09-29

First release: a working prototype on real CSUSB program data. The planner is fully deterministic.

### Added

- Planning engine: term-by-term BS CS pathways with OR prerequisite groups, corequisites, +/- grade minimums, class standing, requirement groups, lecture/lab pairing, and Registrar unit limits (fall/spring 18, summer 14, winter 4). `validate_plan()` checks any plan independently of the engine.
- What-ifs (Fail, Withdraw, Pass, lighter load, Summer/Winter terms) with moved-course lists, unplaceable-plan explanations, and a catch-up search for the fewest Summer/Winter terms that win time back.
- Measured bottlenecks: the delay if each planned course is failed, shown as a "Protect these" strip, per-course badges, and a bottleneck table.
- Real CSUSB 2026-27 data: catalog, BS CS requirements, General Education slots (89 major + 27 GE + 4 free = 120 units), and term offerings from all 12 CSE roadmaps with confidence levels and discrepancy logging.
- Past terms and transcript upload (PDF, text, or CSV), parsed in memory and never stored.
- All-subject dataset (84 subjects, 4,042 courses) with outlier screening.
- GitHub Pages demo: the same FastAPI app runs in the browser under Pyodide (no server), built and deployed by `.github/workflows/pages.yml`. PDF transcript upload is unavailable there.
- FastAPI service and React UI: term grid, SVG prerequisite map, plan history with undo and reset, light and dark themes.
- Engineering Dossier per CSE 6550: requirement register, SRS change proposals CH-02 to CH-04, design and UML, verification strategy, agile plan, risk register, quality and CM plan, threat analysis, AI Engineering Log.
- Requirement-tagged tests (207), a generated traceability matrix, Playwright end-to-end tests, and CI.

### Known limitations

- 95 dangling prerequisites and one ESPE loop are in the published catalog itself.
- No persistence and no SIS integration; student records are synthetic.
