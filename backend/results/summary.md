# Results

Data: BS Computer Science (CSCI), CSUSB 2026-27 catalog + roadmaps. 67 courses, 76 prerequisite edges, 12 discrepancies.

## Pathway quality vs official roadmaps

| student | roadmap | cap | terms (plan/roadmap) | mean P@term | mean R@term | exact-term match | mean abs displacement | valid |
|---|---|---|---|---|---|---|---|---|
| alex | freshman | 15 | 9/8 | 0.394 | 0.365 | 0.524 | 0.905 | True |
| alex | freshman | 16 | 8/8 | 0.431 | 0.41 | 0.524 | 0.905 | True |
| alex | freshman | 18 | 8/8 | 0.463 | 0.39 | 0.476 | 1 | True |
| taylor | transfer | 15 | 4/4 | 0.613 | 0.55 | 0.727 | 0.364 | True |
| taylor | transfer | 17 | 4/4 | 0.7 | 0.6 | 0.727 | 0.364 | True |
| taylor | transfer | 18 | 4/4 | 0.7 | 0.6 | 0.727 | 0.364 | True |

## Official roadmaps checked against the catalog

- **freshman**: 0 violation(s)
- **transfer**: 0 violation(s)

## Scenario sweep

- 280 what-if runs across 6 students; **280/280 produced valid plans**.
- Fail/withdraw delay distribution (terms): {0: 33, 1: 46, 2: 27, 3: 3}
- Mean ripple size on Fail: 2.7 courses
- Recalc time: median 0.42 ms (full plan from scratch: median 0.41 ms, median ratio 0.9x)

## Bottlenecks

Spearman correlation with measured delay-when-failed (29 courses): priority score 0.65, descendant count 0.51, betweenness centrality 0.32. Delay is measured by the same greedy engine that schedules by priority, so this correlation is a consistency check, not validation. Betweenness is 0 by construction for all 6 courses with no prerequisites to plan, including gatekeepers like CSE 2010 and MATH 2372.

| course | priority | descendants | betweenness | mean delay when failed |
|---|---|---|---|---|
| CSE 2020 | 23 | 27 | 0.0139 | 1 |
| MATH 2210 | 11 | 18 | 0.0 | 2 |
| MATH 2220 | 9 | 12 | 0.0002 | 2 |
| CSE 2010 | 8 | 39 | 0.0 | 1 |
| MATH 2310 | 7 | 7 | 0.0037 | 2 |
| CSE 2130 | 6 | 8 | 0.0011 | 1.667 |
| CSE 3100 | 6 | 7 | 0.003 | 2 |
| MATH 2372 | 5 | 36 | 0.0 | 1 |
| PHYS 2500 | 5 | 3 | 0.0002 | 1.333 |
| CSE 4010 | 4 | 3 | 0.0032 | 2 |
| CSE 4200 | 3 | 1 | 0.0016 | None |
| CSE 4310 | 3 | 1 | 0.0016 | 1 |

## Discrepancies (catalog vs roadmap)

- CSE 4100 term offering: roadmaps disagree (Both in bs_cs_freshman; Spring in bs_cs_transfer); planning uses the most restrictive, low confidence.
- CSE 4310 term offering: roadmaps disagree (Both in bs_bioinf_freshman, bs_bioinf_transfer, bs_cs_freshman; Spring in bs_cs_transfer); planning uses the most restrictive, low confidence.
- CSE 4880 term offering: roadmaps disagree (Both in ba_game_freshman, ba_game_transfer, ba_general_freshman, ba_general_transfer, ba_sysadmin_freshman, ba_sysadmin_transfer, bs_bioinf_freshman, bs_bioinf_transfer, bs_cs_freshman; Spring in bs_cs_transfer); planning uses the most restrictive, low confidence.
- CSE 5250 term offering: roadmaps disagree (Both in bs_cs_freshman; Spring in bs_cs_transfer); planning uses the most restrictive, low confidence.
- Freshman roadmap schedules a GE UD slot for GE UD-2/5, but the catalog says CSE 4880 satisfies GE UD-2/5 for this major (catalog wins; slot dropped).
- Program total units: freshman roadmap says 125, catalog says 120 (catalog wins: 89 major + 27 GE + 4 free elective).
- CSE 4010 units: roadmap says 3, catalog says 4 (catalog wins).
- CSE 4550 units: roadmap says 4, catalog says 3 (catalog wins).
- CSE 2020 prerequisites: roadmap lists CSE 2010 / MATH 2372 / MATH 2720, catalog requires CSE 2010 / MATH 2372 (catalog wins).
- CSE 4600 prerequisites: roadmap lists CSE 2130, catalog requires CSE 2020 / CSE 2130 (catalog wins).
- PHYS 2500L prerequisites: roadmap lists PHYS 2500, catalog requires MATH 2210 / MATH 2220 / PHYS 2500 (catalog wins).
- PHYS 2510L prerequisites: roadmap lists PHYS 2510, catalog requires MATH 2220 / PHYS 2500 / PHYS 2500L / PHYS 2510 (catalog wins).
