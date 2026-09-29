# ADPP Study Guide: the concepts under the project

Built from a read of the repo at `release/0.7.0` (engine, graph, guardrail, API, transcript parser, ingestion, evaluation scripts, frontend graph view, and the `docs/` dossier).

**How to use it.** Part 1 is the whole system on one page. Parts 2–8 are the concepts, grouped by the layer of the project that uses them. Each concept has the same five handles:

1. **Root**: the axiom or core logic, and why the mechanics work.
2. **Genesis**: who, when, and what problem forced the idea into existence.
3. **Evolution**: how the original idea became today's notation or usage.
4. **In ADPP**: exactly where it lives in your code.
5. **Master it when**: the question you should be able to answer cold.

Parts 9–10 are the software-engineering vocabulary the course grades you on, and a reading order.

---

## Part 1. The system in one picture

```
catalog HTML + roadmap PDFs ──ingest.py──▶ catalog.json ──▶ Catalog (graph.py)
   (public sources)          (pipe & filter)                  │  courses = nodes, prerequisites = edges  (a DAG)
                                                              ▼
StudentProfile ──baseline()──▶ (satisfied, todo, earned) ──place()──▶ Plan = list[TermPlan]
                                                              │
      ScenarioEvent ──apply_scenario()── descendants(course) ─┘  "ripple" = what must be re-placed
           ▲
           │ typed, validated
   guardrail.classify(text)  ← LLM (Ollama) only *interprets*; never schedules
        calibrate → validate → threshold → audit line; circuit breaker around the LLM
```

The design bet (ADR-03): **the engine decides, the AI interprets.** Every concept below serves one of two jobs: *deciding correctly* (graphs, scheduling, constraints) or *knowing how much to trust a guess* (probability, calibration, escalation).

---

## Part 2. The mathematics of the prerequisite graph

### 2.1 Directed graph, DAG, and partial order

**Root.** A directed graph is $G = (V, E)$ with $E \subseteq V \times V$. A **DAG** is one with no directed cycle. The reason a DAG is the right model for prerequisites is logical, not conventional: "A must come before B" is *asymmetric* and *transitive*. If A precedes B and B precedes C, then A precedes C. A cycle would say a course must precede itself, which no schedule can satisfy. The transitive closure of a DAG is a **strict partial order** $\prec$:

$$
\text{irreflexive: } a \not\prec a \qquad \text{transitive: } a \prec b \prec c \Rightarrow a \prec c \qquad \text{(hence asymmetric)}
$$

"Partial" means some pairs are incomparable (CSE 2130 and MATH 2210 can go in either order). That incomparability is the *freedom* the scheduler exploits.

**Genesis.** Leonhard Euler, 1736, Königsberg bridges: the first graph-theoretic argument, invented to decide whether a walk with a property exists. Directed graphs as models of *precedence* came with 1950s project management: **PERT** (US Navy Polaris program, 1958) and **CPM** (Kelley and Walker, DuPont, 1957–59) had to schedule thousands of activities that depend on each other.

**Evolution.** Euler had no notation for graphs at all; $G=(V,E)$ arrived with 20th-century combinatorics. The order-theoretic reading (a DAG *is* a partial order's Hasse diagram) is what makes "topological sort" a theorem rather than a trick (see 2.2).

**In ADPP.**
- `graph.py::Catalog.__init__` builds `nx.DiGraph`; an edge that would close a cycle is rejected and logged (ADR-10). The check is `nx.has_path(g, to, from)` before adding `from → to`. Adding $u \to v$ creates a cycle iff $v$ already reaches $u$.
- 67 courses, 76 edges (`PRODUCT.md`).

**Master it when** you can explain why rejecting the *edge* (not the load) is the safe failure mode, and why a cycle means "no valid order exists".

### 2.2 Topological sort and linear extensions

**Root.** A **topological order** is a listing $v_1, \dots, v_n$ with $v_i \to v_j \in E \Rightarrow i < j$. Theorem: one exists **iff** $G$ is acyclic. Proof sketch: (⇒) a cycle has no first element. (⇐) a finite DAG has a vertex of in-degree 0 (otherwise walk backwards forever and, by finiteness, repeat a vertex: a cycle); emit it, delete it, recurse. That proof *is* Kahn's algorithm. In order-theory terms, a topological order is a **linear extension** of the partial order.

**Genesis.** Szpilrajn (1930) proved every partial order extends to a total order (existence, non-constructive). Arthur B. Kahn (1962, *Topological sorting of large networks*) gave the constructive algorithm, motivated by PERT networks too large to order by hand. Tarjan (1976) gave the DFS-based version.

**Evolution.** Existence theorem (1930) → practical $O(|V|+|E|)$ algorithm (1962) → library call (`nx.topological_sort`). Note the twist for *scheduling*: a course-per-term schedule is not one linear order but a **layering** (many courses per term), and the layers are constrained by capacity. That is what `place()` does.

**In ADPP.** `graph.py` uses `nx.topological_sort` (reversed) to compute depth. `engine.place()` is a *constrained greedy topological sort*: each term it collects courses whose prerequisites are satisfied (a Kahn-style "ready set"), then packs the ready set under a unit cap.

**Master it when** you can say why the number of valid plans is astronomically large (many linear extensions) and why that motivates a *heuristic* choice among them.

### 2.3 Reachability: ancestors, descendants, and the "ripple"

**Root.** $v$ is a **descendant** of $u$ iff there is a directed path $u \leadsto v$. The set of descendants is the row of the **transitive closure** $E^{*}$. If $u$ is not completed, then *exactly* the descendants of $u$ cannot proceed on schedule, and nothing else is forced to move. That is a precise, provable definition of "ripple effect".

**Genesis.** Stephen Kleene (1951, regular expressions) and Stephen Warshall (1962, the $O(n^3)$ closure algorithm) both formalized "everything reachable". The practical driver for Warshall was compiler and relational-database work: which items depend, directly or indirectly, on which.

**Evolution.** Matrix-closure algorithms → BFS/DFS reachability (linear per source) → `nx.descendants`.

**In ADPP.** `apply_scenario`: `invalid = (nx.descendants(cat.g, cid) | {cid}) & planned_after`. The intersection with `planned_after` matters: only courses still ahead can be invalidated. NFR-11 ("only recalculate what the event invalidates") is this line. `Catalog.required` also uses `nx.ancestors` to sort electives by "least gated".

**Master it when** you can prove that courses outside $\text{desc}(c) \cup \{c\}$ never need to move because of $c$ (they have no path from $c$), and then name the *extra* things that break that proof in your code: **standing gates** and **lab pairing**, which are non-graph constraints (ADR-11).

### 2.4 Prerequisite logic: AND of ORs (conjunctive normal form)

**Root.** In `PrerequisiteEdge`: edges with the same `group` are **ORed**; different groups are **ANDed**. So a course's prerequisite formula is

$$
\bigwedge_{g}\ \bigvee_{e \in g} \text{satisfied}(e)
$$

which is **conjunctive normal form (CNF)**: a conjunction of disjunctions. Any propositional formula can be rewritten into CNF, so this is expressive enough for "MATH 2210 or 2220, and CSE 2010".

**Genesis.** George Boole, *The Mathematical Analysis of Logic* (1847), showed logic obeys algebraic laws over $\{0,1\}$. Normal forms were formalized later; CNF became the workhorse of automated reasoning (SAT) in the 1960s–70s.

**Evolution.** Catalog text ("CSE 2010 and (MATH 2372 or MATH 2720)") → parsed into groups by `ingest.py` → evaluated in `engine.prereqs_met`:

```python
groups[e.group] = groups.get(e.group, False) or ok      # OR within a group
return all(groups.values())                             # AND across groups
```

**Two extra edge attributes, with meaning.** `grade_minimum` turns a boolean into a threshold predicate (a "C-" gate). `concurrent_ok` relaxes the *strict* order to a *weak* order: same-term is allowed (corequisite).

**Master it when** you can rewrite a catalog sentence into groups by hand and predict what `prereqs_met` returns.

### 2.5 Longest path, depth, and the critical path

**Root.** In a DAG the longest path is computable in linear time by dynamic programming over a topological order:

$$
\text{depth}(v) = \max_{v \to w \in E}\bigl(\text{depth}(w) + 1\bigr), \qquad \text{depth}(\text{sink}) = 0
$$

(In general graphs, longest simple path is NP-hard. Acyclicity is what makes it easy.) With one course per unit of time, the longest prerequisite chain is a **lower bound** on the number of terms: no amount of extra capacity can beat a chain of dependencies. That is the **critical path**.

**Genesis.** CPM (Kelley and Walker, 1957–59) for DuPont plant-shutdown scheduling. Their insight: shortening any activity *not* on the critical path does not shorten the project; **slack (float)** is the room an off-path activity has, $\text{float}(a) = LS(a) - ES(a)$ (latest start minus earliest start).

**Evolution.** Manual network diagrams → CPM/PERT software → `nx.dag_longest_path`. In ADPP the weight is 1 per edge (chain length), not calendar time. A corequisite edge can share a term, so treat it as an approximation of the true term lower bound.

**In ADPP.**
- `graph.py`: `depth[n] = max(depth[s]+1 …)` over successors.
- `engine.timeline`: `critical_path = nx.dag_longest_path(subgraph(planned))`. The UI highlights it.
- Explanations say "existing slack absorbs it": that's *float*, in the CPM sense.

**Master it when** you can explain why failing an off-critical-path course often costs 0 terms (results: 29 of the fail/withdraw runs had delay 0).

### 2.6 The priority score

$$
p(c) = \underbrace{\text{outdeg}(c)}_{\text{direct dependents}} + \underbrace{\text{depth}(c)}_{\text{longest chain below}} + \underbrace{\mathbb{1}[c \text{ offered only Fall or only Spring}]}_{\text{missing it costs a year}}
$$

**Root.** Prefer to schedule first the courses whose delay would hurt most. Depth captures *serial* damage; out-degree captures *breadth*; the indicator captures *calendar* damage (a once-a-year course that slips waits two terms, not one).

**Genesis.** Hu (1961, *Parallel sequencing and assembly line problems*) proved that "highest level first" (schedule the task with the longest remaining chain) is optimal for unit-time tasks on identical processors when the precedence graph is a tree. For general DAGs it is only a heuristic. Graham (1966, *Bounds for certain multiprocessing anomalies*) proved list scheduling is within a factor $2 - 1/m$ of optimal for $m$ processors, and showed it can behave counter-intuitively ("Graham's anomalies").

**In ADPP.** Note the interesting consequence in `results/summary.md`: **CSE 2010 has 39 descendants but priority 8**, while CSE 2020 has 27 descendants and priority 23. Priority weighs *depth*, not descendant *count*. Descendants measure blast radius; depth measures how far it can push graduation.

**Master it when** you can argue both for and against this formula (it is a hand-designed heuristic, not derived from an optimum; see 3.2).

---

## Part 3. Scheduling under constraints (the engine)

### 3.1 Constraint satisfaction: what "valid plan" means

A plan is valid iff **all** of these hold (see `validate_plan`, the independent checker):

| Constraint | Formal shape | Code |
|---|---|---|
| Precedence | $v \to w \Rightarrow \text{term}(v) < \text{term}(w)$, or $\le$ if `concurrent_ok` | `prereqs_met` |
| Grade minimum | $\text{points}(g) \ge \text{points}(\text{min})$ | `grade_ok` |
| Offering | term season $\in$ course's `term_offered` | `offered` |
| Capacity | $\sum_{c \in T} \text{units}(c) \le \text{cap}(T)$ | `place`, `validate_plan` |
| Standing | units earned so far $\ge$ `min_standing_units` | `earned >=` checks |
| Lab pairing | lecture and lab in the *same* term | `_bundle`, `lab_for` |
| Uniqueness | each course at most once | `validate_plan` counts |

**The single most important design idea here: `place()` constructs, `validate_plan()` verifies, and they are separate code.** A checker written independently of the generator is how you catch generator bugs. It's also why the validator can grade *official roadmaps* and *hand-edited plans* (FR-14). Same principle as a proof checker versus a proof search.

### 3.2 Greedy algorithms, and why "constrained greedy" is not optimal

**Root.** A **greedy** algorithm makes the locally best choice at each step and never revisits it. It is provably optimal only when the problem has the **greedy-choice property** and **optimal substructure** (e.g., matroids). Precedence-constrained scheduling with capacity and deadlines has no such guarantee. It is **NP-hard** in general (Ullman, 1975). So the engine trades optimality for speed and *explainability* (ADR-04).

**Genesis / evolution.** List scheduling (Graham 1966) → priority-rule heuristics (highest level first, Hu 1961) → integer programming for exact answers. Your upgrade path is a **MILP** (mixed-integer linear program):

$$
\min\ T \quad \text{s.t.} \quad \sum_{t} x_{c,t} = 1\ \ \forall c, \qquad \sum_{c} u_c\, x_{c,t} \le \text{cap}_t\ \ \forall t, \qquad \sum_{t} t\,x_{c,t} \ge \sum_{t} t\,x_{p,t} + 1\ \ \forall (p \to c)
$$

with binary $x_{c,t} = 1$ iff course $c$ is placed in term $t$. History: linear programming was formalized by Kantorovich (1939) and solved by Dantzig's simplex method (1947); Gomory (1958) added cutting planes for integer variables.

**In ADPP.** `place()`, the inner `while added:` loop (repeat because placing a corequisite can unlock its partner in the same term). Determinism (NFR-08): sort key `(-priority, course_id)`, so ties break alphabetically and the same input always gives the same plan.

**Master it when** you can name what greedy sacrifices (it "packs GE slots late", EV-07) and what the results table measures about it (P@term, R@term versus the official roadmap).

### 3.3 Subset sum inside `_exact_fill`

`Catalog._exact_fill` picks electives whose units sum to *exactly* the requirement, by depth-first search over the preference-ordered pool. That is **subset sum**: given integers $a_i$ and target $s$, is there $S$ with $\sum_{i \in S} a_i = s$? NP-complete (Karp, 1972, one of the original 21), but with a handful of 3–4-unit electives the search is trivial. Order-of-pool encodes *preference* (the first solution found is the most preferred).

### 3.4 Local search with lookahead: `recover()`

`recover` adds Summer/Winter terms to win back delay. It is **hill climbing**: repeatedly take the single addition that most improves `score = (regular-term ordinal, term key, term count)`. When no single step improves, it tries **pairs** (a depth-2 lookahead) because a Summer retake can pay off only once a Winter opens room. That's the classic fix for a hill-climber stuck on a plateau. The code says so honestly: `ponytail: greedy with pair lookahead, not an exhaustive search`.

### 3.5 Sensitivity analysis: `course_risk`

For each planned course, simulate "fail it in its planned term" and measure delay, then see if opt-in terms recover it. This is a **what-if / sensitivity analysis**: perturb one input, measure the output shift. It is *measured* risk, not a formula, and the results file warns that priority-vs-delay correlation is a **consistency check, not validation**, because the same greedy engine produces both numbers.

### 3.6 Invariants, pre/postconditions, determinism

Learn to state these for each engine function; they are what your tests assert.
- `apply_scenario`: **the input plan is unchanged** (it deep-copies), and courses outside the removed set keep their term.
- `make_plan`: postcondition `validate_plan(plan) == []`.
- Idempotence and determinism: same inputs, same plan. Nothing random, no LLM in the loop.
- `Pass` is a **pin**: `credited` marks a course that stays in its term; a later retake **revokes** passes that depended on it (`_pinned`, `_rebuild_from`).

---

## Part 4. Domain vocabulary (the registrar side)

Know these exactly. Most bugs and most advisor conversations live here.

| Term | Meaning in this project |
|---|---|
| **Catalog** | Authoritative for **units and prerequisites** (ADR-02). |
| **Roadmap** | Official term-by-term sample plan (PDF); authoritative for **sequence and offering pattern**. |
| **Discrepancy** | Where catalog and roadmap disagree. **Stored and flagged, never silently resolved.** 12 currently. |
| **Term offered** | `Fall`, `Spring`, `Both`, `Unknown`. "Once-a-year course" = Fall-only or Spring-only. |
| **Offering confidence** | `high` (roadmaps agree), `low` (they conflict; plan uses the *most restrictive*, ADR-07), `unknown` (no roadmap). |
| **Standing / `min_standing_units`** | A gate on *units earned*, e.g. Senior = 90. Not a graph edge, which is why losing units can break later courses. |
| **Corequisite (`concurrent_ok`)** | May be taken in the same term. |
| **Lab pairing** | `PHYS 2500L` goes with `PHYS 2500` in one term. A stricter rule than the catalog's "corequisite". |
| **Placeholder / GE slot** | A slot ("GE 1A", free elective) rather than a specific course; `satisfied_by` lists what fills it. |
| **`entry_assumed`** | Courses assumed satisfied at program entry (CSE 1250, MATH 1401/1403): **placement assumptions** (ADR-08). |
| **Requirement group** | A block of the program: `all` (take all) or `from` (choose `choose` courses / `choose_units` units). |
| **Unit cap / load** | Maximum units per term. Preference default 15; allowed range 3–21; Registrar regular max 18 (overload beyond). |
| **Intersession** | Summer (max 14; engine plans 7) and Winter (max 4). **Opt-in**, never planned by default; only `Both` courses are candidates. |
| **Transfer units** | Count toward standing but map to no catalog course. |
| **Grade minimum** | On the +/- scale. `CR/P/TR` treated as C-equivalent (an assumption to confirm: CH-02 C-8). `W`, `NC`, `I` never pass. |
| **PAWS / myCAP / Schedule Planner** | The official systems you are *not* integrating with (non-goal, COM-03). |

**Grade math.** GPA scale: $A=4.0,\ A^-=3.7,\ B^+=3.3,\dots,\ D^-=0.7,\ F=0$. `grade_ok(g, m)` is simply $\text{pts}(g)\ge \text{pts}(m)$. The subtlety is `baseline()`: a grade that passes the course (D) but not a *downstream* minimum (C- needed for CSE 2020) leaves the course *unsatisfied*, so it re-enters the todo list as a **forced retake**.

---

## Part 5. Scenario semantics (what each event does)

| Event | Mechanism |
|---|---|
| **Fail / Withdraw** | Remove the course and its planned descendants (plus standing-broken and lab-paired courses) from the event term onward; re-`place()` from the next term. Revoke any earlier `Pass` that depended on it. |
| **Pass** | Credit the course in its term (pin); re-check later terms; some things may move *earlier*. |
| **Add Summer / Add Winter** | Opt in to an intersession; rebuild from there. |
| **Change Unit Load** | New cap from the event term on; earlier terms keep their cap (`caps` history). |

**Explanation is a template, not an LLM output** (FR-12): `delta = ordinal(after) − ordinal(before)`, where `_ordinal` maps Summer to the preceding Spring and Winter to the preceding Fall so that intersessions do not count as "a term later". Three outcomes: unchanged (slack absorbed it), delayed by $\delta > 0$, moved up by $|\delta|$.

---

## Part 6. Probability, calibration, and trust (the guardrail)

This is the part with the most first-principles math. The question it answers: *when an LLM says "I'm 92% sure", should the engine believe it?*

### 6.1 Classification, confidence, and the reject option

**Root.** The LLM outputs a structured guess $\hat{e}$ (an event) and a self-reported confidence $s \in [0,1]$. A decision rule turns $s$ into an action:

$$
\text{action}(s) = \begin{cases} \text{auto-accept} & s \ge 0.90 \\ \text{accept, flag for review} & 0.60 \le s < 0.90 \\ \text{escalate to a human} & s < 0.60 \ \text{or any validation failure} \end{cases}
$$

**Genesis.** C. K. Chow (1957; formalized in *On optimum recognition error and reject tradeoff*, 1970) proved that for a classifier with cost of an error $c_e$ and cost of rejecting $c_r$, the optimal rule is to **reject when the maximum posterior probability falls below** $1 - c_r/c_e$. Origin: optical character recognition (reading checks and forms), where a wrong read cost more than a manual look.

**Evolution.** Chow's "reject option" → selective classification → today's "human in the loop" / escalation design. Your 0.90/0.60 are **placeholders** (a code comment says so). Chow's rule says they should come from real costs and a calibrated $s$.

### 6.2 Why raw LLM confidence is not a probability: calibration

**Root.** A model is **calibrated** if

$$
P(\text{correct} \mid \hat{p} = p) = p \quad \forall p \in [0,1]
$$

"Of the times you say 90%, you are right 90% of the time." LLM self-reports are typically overconfident, so they must be **recalibrated** against labeled outcomes before they mean anything.

**Genesis.** Meteorologists asked this first. Glenn Brier (1950, *Verification of forecasts expressed in terms of probability*) needed a way to score "70% chance of rain".

### 6.3 Brier score

$$
\text{BS} = \frac{1}{N}\sum_{i=1}^{N}(f_i - o_i)^2, \qquad f_i \in [0,1],\ o_i \in \{0,1\}
$$

**Why it works.** It is a **strictly proper scoring rule**: expected score is minimized *only* by reporting your true belief, so honesty is the optimal strategy. (Compare absolute error $|f-o|$, which rewards rounding to 0 or 1.) Murphy (1973) decomposed it into reliability, resolution, and uncertainty. Used in `calibrate.py::evaluate` (`brier_raw` versus `brier_calibrated`).

### 6.4 Expected Calibration Error (ECE)

$$
\text{ECE} = \sum_{b=1}^{B} \frac{|S_b|}{N}\,\bigl|\,\text{acc}(S_b) - \text{conf}(S_b)\,\bigr|
$$

Bin predictions by confidence; in each bin compare average confidence to actual accuracy; weight by bin size. Introduced by Naeini, Cooper and Hauskrecht (2015), popularized for neural networks by Guo et al. (2017, *On Calibration of Modern Neural Networks*). Your `ece()` uses 5 bins, and the comment explains why: with ~45 queries, 10 bins is noise. **Known weakness**: ECE depends on the bin count and can be gamed by binning; treat it as a diagnostic.

### 6.5 Platt scaling (what `calibrate.py` fits)

**Root.** Fit a logistic curve mapping raw score to probability of being correct:

$$
P(\text{correct} \mid s) = \frac{1}{1 + e^{\,A s + B}}
$$

The logistic function's root: it maps $\mathbb{R} \to (0,1)$, and it is the unique form whose *log-odds are linear*: $\ln\frac{p}{1-p} = -(As+B)$.

**Genesis.** Pierre-François Verhulst (1838) invented the logistic curve for population growth with a carrying capacity. John Platt (1999) applied it to turn SVM margins into probabilities.

**Evolution.** Verhulst's population model → logistic regression (statistics, mid-20th century) → Platt scaling (1999) → alternatives (isotonic regression; temperature scaling, Guo 2017).

**In ADPP.** `CalibratedClassifierCV(LogisticRegression(), method="sigmoid")` fits it; the result is written as a 21-point table; `guardrail.calibrate` linearly interpolates with `np.interp`. **Cross-validated** metrics (out-of-fold) matter because scoring calibration on the data you fit it on is optimistic. Needs $\ge 4$ examples of each class.

### 6.6 Defense in depth: validation after the model

The LLM output is *never trusted structurally*. `guardrail.validate` re-checks deterministically: does the course exist, is it in that term, is the term in the plan, is the unit load in 3–21? Only then does the threshold apply. Principle: **parse, don't validate** in the type-driven sense: convert untrusted text into a typed value (`ScenarioEvent` via Pydantic/Instructor) at the boundary, so everything downstream can assume well-formedness.

### 6.7 Circuit breaker

**Root.** A failing dependency, retried without limit, drags the caller down with it. After $n=3$ consecutive failures, *stop calling* for 60 s and fail fast; then let one trial request through ("half-open").

**Genesis.** Named by analogy with the electrical breaker that trips to prevent a fire. Michael Nygard, *Release It!* (2007), for production systems that cascaded when one service hung; popularized by Martin Fowler (2014).

**In ADPP.** State machine in `design.md` §2.5 (Closed → Open → Trial). Note the honest limits in code: in-process state, guarded by a lock; only correct for one worker.

### 6.8 Prompt injection and the audit trail

The threat model (R-5): text in the query box tries to steer the LLM. Defense is *architectural*: the LLM has **no tools and no write path**, and its only output is a typed event that gets validated. The **audit log** (`audit.jsonl`, structlog) writes one line per decision, and `/audit` exposes it; JSON rendering escapes newlines so one decision is always one line (a log-injection defense).

---

## Part 7. Evaluation statistics (`results.py`, `summary.md`)

| Metric | Definition | Reading |
|---|---|---|
| **Precision @ term** | $\frac{\lvert\text{plan}_t \cap \text{roadmap}_t\rvert}{\lvert\text{plan}_t\rvert}$ | Of what I planned this term, how much matches the official roadmap? |
| **Recall @ term** | $\frac{\lvert\text{plan}_t \cap \text{roadmap}_t\rvert}{\lvert\text{roadmap}_t\rvert}$ | Of what the roadmap has, how much did I plan? |
| **Exact-term match / mean abs displacement** | Fraction placed in the same term; average $\lvert \text{term}_{plan} - \text{term}_{roadmap}\rvert$ | |
| **Spearman's $\rho$** | Pearson correlation of the *ranks* | Used to compare priority score vs measured delay |
| **Betweenness centrality** | $C_B(v) = \sum_{s \ne v \ne t} \frac{\sigma_{st}(v)}{\sigma_{st}}$ | Fraction of shortest paths passing through $v$ |

**Precision/recall.** Kent et al. (1955) for document retrieval; van Rijsbergen (1979) combined them as $F_\beta$. They are the two ways to be wrong: *extra* items and *missing* items.

**Spearman.** Charles Spearman (1904) wanted association between two measures (school subjects) without assuming a linear relation. Without ties, $\rho = 1 - \dfrac{6\sum d_i^2}{n(n^2-1)}$, where $d_i$ is the rank difference. Your results: priority 0.62, descendant count 0.48, betweenness 0.31 against measured delay. **Read with care**: the results file itself says the delay is produced by the same greedy engine, so this is a consistency check, not independent validation. Say it that way in the SRS and the demo.

**Betweenness.** Anthonisse (1971) and Linton Freeman (1977) in sociometry: who sits *between* others in a social network. Brandes (2001) gave the $O(VE)$ algorithm. In a course DAG it is **zero for every source** (a course with no prerequisites is the start of any path, never in the middle), which is why gatekeepers like CSE 2010 score 0 there. A good example of a metric that does not fit its domain. Your summary already says this; being able to explain it is the mark of mastery.

**Sweep testing.** 285 what-if runs across 6 students, all valid: this is **property-based / exhaustive scenario testing**, checking an invariant (`validate_plan == []`) over many inputs. See also `test_fuzz.py`.

---

## Part 8. Data, API, and UI engineering

| Concept | Where | Root idea |
|---|---|---|
| **Pipe and filter** | `ingest.py` | Stages composed by data flow (McIlroy's 1964 memo on connecting programs "like garden hose"; Unix pipes 1973). Each stage testable alone; raw sources are cached and committed so ingestion is reproducible (DR-07). |
| **Parsing requisite text → AND/OR groups** | `ingest.py` | Turning natural-language grammar into CNF (2.4). Fragile against format changes (R-2). |
| **REST, stateless server** | `api.py` | Fielding (2000). ADR-06: the client sends the full plan with each scenario, so the server keeps no session. Trade-off: request bodies are *untrusted client state*, so the API re-validates them (`KnownPlan`, size limits, `MAX_BODY`). |
| **Schema validation at the boundary** | `models.py`, `api.py` | Pydantic models with regex-constrained types (`TermLabel`, `CourseId`, `Cap`). Permissive core models, strict API models. |
| **Security headers, body-size limit** | `api.py` middleware | Cheap defense in depth (`nosniff`, frame deny, 413 on oversize). |
| **In-memory uploads** | `api.py`, `transcript.py` | Transcripts (FR-26) live only in process memory, newest 200, never on disk or in the audit log (privacy by design; R-1). |
| **Tolerant parser + report what you could not place** | `transcript.py` | Registrar exports differ; recognize term header, transfer header, course row, grade; return the unplaced remainder instead of guessing. |
| **Layered graph drawing (Sugiyama)** | `PrereqMap.tsx` | Sugiyama, Tagawa and Toda (1981): layer nodes so edges point one direction, insert *dummy nodes* on long edges, order each layer by a **barycenter** heuristic to reduce crossings (crossing minimization is NP-hard: Garey and Johnson 1983). Your layers are the plan's own terms. |
| **Accessibility** | `PRODUCT.md` | WCAG AA; status never color-only (labels like "(affected)"); keyboard reachable; e2e tests depend on accessible names and `data-testid`. |
| **Stack** | `pyproject.toml`, `package.json` | FastAPI, Pydantic v2, NetworkX, Instructor, scikit-learn, structlog, pdfplumber, BeautifulSoup; React 19, Vite, TypeScript, Playwright, oxlint. |

---

## Part 9. Software-engineering vocabulary (CSE 6550 dossier)

| Term | Meaning | Where in your repo |
|---|---|---|
| **SRS** | Software Requirements Specification: the authoritative statement of what to build (IEEE 830, now ISO/IEC/IEEE 29148). | Google Doc v0.1; repo holds only attributes. |
| **FR / NFR / DR / IF / COM / LIM / PR / AS / EV** | Functional, non-functional, data, interface, compliance, limitation, prototype, assumption, evidence IDs. | `requirements-register.md` |
| **Traceability** | Requirement ↔ design ↔ test links, for **change-impact analysis** (R-11). | `@pytest.mark.req("FR-10")`, generated `traceability.md`, checked in CI. |
| **Change proposal (CH-nn)** | Requirement changes go into the SRS first. | `srs-change-proposal-CH-02..04` |
| **ADR** | Architecture Decision Record: decision, motivation, consequence (Nygard, 2011). | `design.md` §1 (ADR-01..11) |
| **4+1 views** | Logical, process, development, physical, plus scenarios (Kruchten, 1995). | `design.md` §3 |
| **Architectural patterns** | Layered, repository, pipe-and-filter, client-server. | `design.md` §4 |
| **Dependency injection** | Pass collaborators in: `classify(text, plan, llm=...)`, so tests use a fake LLM with no network. | `guardrail.py` |
| **Equivalence partitioning and boundary-value analysis** | Split inputs into classes the code treats alike; test each class **and its edges** (Myers, 1979). E.g. unit load: 2 ✗, 3 ✓, 21 ✓, 22 ✗. | `verification-strategy.md` §2.1 |
| **TDD** | A failing tagged test before the implementation; a bug gets a regression test (Beck, 2002). | Policy in verification strategy §2 |
| **Inspection** | Structured peer review of artifacts (Fagan, 1976). | PR checklist, mandatory non-author reviewer |
| **Verification vs validation** | *Built it right* (matches spec) vs *built the right thing* (meets need). | Release testing vs user testing |
| **Development / release / user testing** | Unit → component → system; requirements-based and scenario; alpha, usability, acceptance. | `verification-strategy.md` |
| **Risk register** | Identify → analyze → plan → monitor. Probability × effect; strategies **avoid / minimize / contingency** (Sommerville §22.1). | `risk-register.md` (R-1..R-14) |
| **CM / CCB / baseline** | Configuration management; change control board; an agreed, versioned snapshot (SRS v0.1). | `quality-and-cm-plan.md` |
| **Definition of Done, sprint, backlog, ScrumMaster, Product Owner** | Scrum vocabulary (Takeuchi and Nonaka, 1986; Schwaber and Sutherland). | `agile-engineering-plan.md`, GitHub Issues |
| **AI provenance** | Log significant AI output and how it was validated; AI-generated content is never presented as stakeholder evidence. | `ai-engineering-log.md`, R-14 |
| **CI** | Automated build/test on every push; the gate for merging. | `.github/workflows/ci.yml` |

---

## Part 10. Suggested order of mastery

1. **Graph core:** 2.1 → 2.2 → 2.3. Then read `graph.py` top to bottom and `apply_scenario`'s first branch. You should be able to trace "fail CSE 2020" by hand.
2. **Constraints:** 2.4, 3.1, and `prereqs_met`, `offered`, `baseline`. Write five unit tests in your head (grade boundary, OR group, corequisite, once-a-year, standing).
3. **Scheduling theory:** 2.5, 2.6, 3.2. Be ready to defend "greedy, not optimal" with Hu, Graham, and NP-hardness, and to describe the MILP alternative.
4. **Ripple and recovery:** Part 5, 3.4, 3.5.
5. **Guardrail math:** 6.1 → 6.5. Derive Brier and ECE on a 6-row toy table by hand before running `calibrate.py`.
6. **Evaluation honesty:** Part 7, especially why the bottleneck correlation is a consistency check.
7. **Dossier language:** Part 9, then map each term to a file.

**Exercises worth doing.**
- Pick a course and compute its `outdeg`, `depth`, `priority`, and `descendants` from `catalog.json`. Explain any gap between priority rank and descendant rank.
- Construct an input on which greedy is beaten by a different placement (a tiny 4-course DAG suffices), and state which extra rule would have fixed it.
- Given 8 hand-made (confidence, correct) pairs, compute BS and a 2-bin ECE, then decide whether 0.90 is a defensible threshold.
- Write the CNF for `CSE 2020`'s prerequisites and run it through `prereqs_met` in a REPL.

---

## Things I noticed while reading (worth a decision, not fixed here)

- `design.md` (component spec) says summer cap **8**; `engine.py` uses `SUMMER_CAP = 7` (max 14). The code comment cites a re-verification on 2026-09-29, so the doc is probably stale.
- `README.md` status still says "Week 5 … prototype `v0.3`", while `CHANGELOG.md` and git history are at **0.7.0**.
- The guardrail thresholds 0.90/0.60 are explicitly placeholders until `calibrate.py` is run against a real local model, which is risk R-3.
- The bottleneck validation is circular (same greedy engine produces the priority and the delay); the results file says so, so keep the SRS wording consistent.
