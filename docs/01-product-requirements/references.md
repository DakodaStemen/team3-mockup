# References

The SRS §1.5 reference list continues here. REF-01 to REF-05 match SRS v0.1; later IDs are proposed additions. **Verification** records whether someone on the team actually opened the source. An unverified item is a lead, not evidence.

## Course and standards

| ID | Reference | Use | Verification |
|---|---|---|---|
| REF-01 | Sommerville, *Software Engineering*, 10th ed., Ch 4 (and Ch 3, 5–8, 13, 22–25 for the process documents) | Requirements and SE process foundation | Read (course textbook) |
| REF-02 | ISO/IEC/IEEE 29148:2018 | Course-tailored requirements guidance | Course copy |
| REF-03 | CSE 6550 Project 3 brief: Adaptive Degree Pathway Planner | Problem, capabilities, scope | Course document |
| REF-04 | CSE 6550 Engineering Dossier and Workspace pages; SRS v0.1 template | Dossier structure, restricted-data rules, AI provenance | Read 2026-09-28 |
| REF-05 | CSUSB catalog and BS CS roadmaps. Links: [CSE courses](https://catalog.csusb.edu/coursesaz/cse/), [MATH](https://catalog.csusb.edu/coursesaz/math/), [PHYS](https://catalog.csusb.edu/coursesaz/phys/), [BS CS program](https://catalog.csusb.edu/colleges-schools-departments/natural-sciences/computer-science-engineering/computer-science-bs/), [General Education](https://catalog.csusb.edu/general-education-program/), [Undergraduate Roadmaps, all 12 CSE](https://www.csusb.edu/advising/advising-tools/undergraduate-roadmaps?field_rm_department_target_id=37186) | Program data (EV-02) | Fetched by `ingest.py` 2026-09-28; raw copies in `backend/data/raw/` |
| REF-06 | Adaptive Degree Pathway Planner Technical Spec v0.1 ([docx](ADPP_TechnicalSpec_v0.1_2026-09-28.docx)) | Architecture and guardrail design (EV-08) | Team-authored |

## Cited in the technical spec

Verification notes are as recorded by the spec's author.

| ID | Reference | Verification |
|---|---|---|
| REF-07 | CourseRank project page, Stanford InfoLab | Verified; the page doesn't state the 10,000-student figure |
| REF-08 | Slim et al., "An Efficient Linearized Optimization Framework for Designing Balanced and Efficient Degree Plans," EDM 2025 | Verified |
| REF-09 | Paz, "The CAPIRE Curriculum Graph," arXiv 2025 | Verified |
| REF-10 | Slim et al., "Integrated Curriculum Analytics," EDM 2025 | Verified |
| REF-11 | Marusich et al., "Trust Calibration for Joint Human/AI Decision-Making," HCII 2025 | Verified (paywalled) |
| REF-12 | "Recommendation systems with complex constraints," ACM TOIS vol. 29 no. 4 | **Not verified** (ACM blocked the check) |
| REF-13 | CMU Course Advisor | Not opened (from search results) |
| REF-14 | course_plan_optimizer | Not opened (from search results) |
| REF-15 | purdue-degree-planner | Not opened (from search results) |
| REF-16 | PSAIAC advising assistant | Not opened (from search results) |
| REF-17 | Sushanth0003/project- | Not opened (from search results) |
| REF-18 | PuLP | Not opened (from search results) |
| REF-19 | Unstructured | Not opened (from search results) |

## Named in the spec, no link yet

These are leads; add a link and verification when used as evidence.

- Instructor (567-labs/instructor on GitHub). *Used in code.*
- scikit-learn probability calibration docs (CalibratedClassifierCV). *Used in code.*
- Reagraph (reaviz/reagraph on GitHub). *Used in code until v0.6; replaced by a hand-built SVG map.*
- NetworkX, Pydantic, FastAPI, SQLite, PyMuPDF, pdfplumber. Named from general knowledge, not researched. *All but SQLite and PyMuPDF are used in code.*
- structlog guides
- MLflow vs. Weights and Biases comparisons
- Brier score and reliability-diagram references
- Brandes, "A Faster Algorithm for Betweenness Centrality" (2001)
- Kahn (1962) and Tarjan (1976) on topological sorting
- Precision@K / recall@K recommender-evaluation guides
- CSUSB ScholarWorks catalog archive
- CollegeSource v. AcademyOne, via the law review article "Data Scraping as a Cause of Action: Limiting Use of the CFAA". Only a search snippet was read. **Needs verification before it is relied on (COM-04).**
- LLM circuit-breaker and retry-pattern guides (DEV Community and others)
- CSUSB myCAP and PAWS pages (Registrar, Advising)
- The CSE 6550 course-material prompt that was the source of the drift audit numbers. Those numbers are now independently reproduced by EV-10.

## Consulted but not used

GradPath (Zenodo); AI-Course-Advisor (71ashu); Aarush-D/Course-Planner (PSU, 1,573 tests incl. AND-vs-OR prerequisite cases); cohm/ProgramVisualization; mizcausevic-dev/curriculum-knowledge-graph; ASSIGNA and ChronoSolve (OR-Tools CP-SAT); mucsci/Scheduler; Analysis of Student Progression Through Curricular Networks (Illinois); Comparative analysis of course prerequisite networks at five Midwestern institutions (Applied Network Science); Slack-based course scheduling algorithm (ICEIT 2020); Course Planning Optimization with Conditional Constraints using ILP; Human-in-the-Loop AI: a systematic review (PMC); CSUSB Office of Institutional Research FERPA statement; University of Iowa, FERPA and Research; Apify catalog scrapers.
