# Results

Data: BS Computer Science (CSCI), CSUSB 2026-27 catalog + roadmaps. 63 courses, 69 prerequisite edges, 11 discrepancies.

## Pathway quality vs official roadmaps

| student | roadmap | cap | terms (plan/roadmap) | mean P@term | mean R@term | exact-term match | mean abs displacement | valid |
|---|---|---|---|---|---|---|---|---|
| alex | freshman | 15 | 8/8 | 0.412 | 0.41 | 0.524 | 0.905 | True |
| alex | freshman | 16 | 8/8 | 0.412 | 0.41 | 0.524 | 0.905 | True |
| alex | freshman | 18 | 8/8 | 0.481 | 0.421 | 0.476 | 1 | True |
| taylor | transfer | 15 | 5/4 | 0.49 | 0.44 | 0.727 | 0.455 | True |
| taylor | transfer | 17 | 4/4 | 0.525 | 0.5 | 0.636 | 0.636 | True |
| taylor | transfer | 18 | 4/4 | 0.542 | 0.5 | 0.636 | 0.636 | True |

## Official roadmaps checked against the catalog

- **freshman**: 0 violation(s)
- **transfer**: 0 violation(s)

## Scenario sweep

- 282 what-if runs across 6 students; **282/282 produced valid plans**.
- Fail/withdraw delay distribution (terms): {0: 48, 1: 37, 2: 20, 3: 4}
- Mean ripple size on Fail: 2.7 courses
- Recalc time: median 0.91 ms (full plan from scratch: median 0.90 ms, median ratio 0.9x)

## Bottlenecks

Spearman correlation with measured delay-when-failed (29 courses): priority score 0.62, descendant count 0.49, betweenness centrality 0.31.

| course | priority | descendants | betweenness | mean delay when failed |
|---|---|---|---|---|
| CSE 2020 | 22 | 26 | 0.0148 | 0.5 |
| MATH 2210 | 11 | 18 | 0.0 | 2 |
| CSE 2010 | 8 | 37 | 0.0 | 0.5 |
| MATH 2220 | 8 | 12 | 0.0002 | 2 |
| CSE 2130 | 6 | 8 | 0.0012 | 1.667 |
| MATH 2310 | 6 | 7 | 0.0041 | 1.667 |
| CSE 3100 | 5 | 6 | 0.0028 | 1.25 |
| MATH 2372 | 5 | 34 | 0.0 | 1 |
| PHYS 2500 | 5 | 3 | 0.0002 | 1 |
| CSE 4010 | 4 | 3 | 0.0035 | 1.25 |
| CSE 4310 | 3 | 1 | 0.0018 | 0.75 |
| CSE 5720 | 3 | 1 | 0.0009 | 1.333 |

## Discrepancies (catalog vs roadmap)

- CSE 4310 term offering: roadmaps disagree (Both vs Spring); using the more restrictive for planning.
- CSE 4100 term offering: roadmaps disagree (Both vs Spring); using the more restrictive for planning.
- CSE 4880 term offering: roadmaps disagree (Both vs Spring); using the more restrictive for planning.
- CSE 5250 term offering: roadmaps disagree (Both vs Spring); using the more restrictive for planning.
- Program total units: freshman roadmap says 125, catalog says 120 (catalog wins; free electives sized to 1 units).
- CSE 4010 units: roadmap says 3, catalog says 4 (catalog wins).
- CSE 4550 units: roadmap says 4, catalog says 3 (catalog wins).
- CSE 2020 prerequisites: roadmap lists CSE 2010 / MATH 2372 / MATH 2720, catalog requires CSE 2010 / MATH 2372 (catalog wins).
- CSE 4600 prerequisites: roadmap lists CSE 2130, catalog requires CSE 2020 / CSE 2130 (catalog wins).
- PHYS 2500L prerequisites: roadmap lists PHYS 2500, catalog requires MATH 2210 / MATH 2220 / PHYS 2500 (catalog wins).
- PHYS 2510L prerequisites: roadmap lists PHYS 2510, catalog requires MATH 2220 / PHYS 2500 / PHYS 2500L / PHYS 2510 (catalog wins).
