# UML Diagram Set (Sommerville Ch 5)

> [Docs index](../README.md) · [Design and ADRs](design.md) · [UML diagrams](uml-diagrams.md)

**Contents:** [1 Context and use cases](#1-context-and-use-cases) · [2 Class diagram](#2-class-diagram-structure) · [3 Sequence diagram](#3-sequence-diagram-recalculation-after-failing-cse-2020) · [4 Activity diagram](#4-activity-diagram-pathway-generation-and-recalculation) · [5 State diagram](#5-state-diagram-pathway-lifecycle)

Five perspectives, each in Mermaid (renders in GitHub) and PlantUML (for export). They extend the models in [design.md §2](design.md#2-system-models), use the same requirement IDs, and were checked against the code on 2026-09-29 (`engine.py`, `api.py`, `models.py`, `graph.py`). Names in the diagrams are the code's names.

Some elements of the original modeling brief are not in the code. The diagrams show what exists:

| Brief element | What the code has |
|---|---|
| Advisor "Validate & Approve Plan", `ApprovedBaseline` state | Validation exists (`POST /validate`, FR-14); approval and the advisor view do not (FR-18) |
| `RequirementGroup` class | Data only: `Catalog.program["groups"]`, resolved by `Catalog.required()` |
| `DataConflictWarning` class | Strings in `Catalog.discrepancies`, plus `results/roadmap_audit.json` (FR-20) |
| `ScenarioController`, `ConstraintValidator`, `TimelineAnalyzer` | `api.py`, the rules inside `place()`, and `timeline()` |
| Catalog Scraper and Roadmap Parser as external actors | Inside the boundary (`scripts/ingest.py`); the external systems are catalog.csusb.edu and the roadmap PDFs |
| Parallel GE / core planning | One greedy pass over a single priority-ordered candidate list; GE slots are placeholder courses |

## 1. Context and use cases

**Summary.** Shows the system boundary and who uses it (SRS §2.2, IF-01..IF-05). The two public sources are external actors for the ingestion subsystem. "Simulate what-if" includes recalculation, and recalculation offers Summer/Winter catch-up when graduation slips. Students can start from a synthetic profile or an uploaded transcript.

```mermaid
flowchart LR
  Student([Student])
  Advisor([Academic Advisor])
  CAT[/catalog.csusb.edu/]
  RM[/Roadmap PDFs/]
  subgraph Planner [Adaptive Degree Pathway Planner]
    UC1(Establish starting point:<br/>pick a student or upload a transcript<br/>FR-26 DR-04)
    UC2(Generate term pathway<br/>FR-05..FR-08)
    UC3(Simulate what-if<br/>FR-09..FR-11 FR-15)
    UC4(Recalculate on failure or delay<br/>FR-04 FR-10 FR-12)
    UC8(Recover with Summer / Winter<br/>FR-24)
    UC9(Show bottlenecks<br/>FR-25)
    UC5(Flag catalog vs roadmap conflicts<br/>FR-20)
    UC6(Validate a plan<br/>FR-14)
    UC7(Ingest program data<br/>DR-07)
  end
  Student --- UC1
  Student --- UC2
  Student --- UC3
  Student --- UC9
  Advisor --- UC5
  Advisor --- UC6
  UC3 -. include .-> UC4
  UC4 -. extend .-> UC8
  UC2 -. include .-> UC5
  UC7 -. extend .-> UC5
  CAT --> UC7
  RM --> UC7
```

```plantuml
@startuml
left to right direction
actor Student
actor "Academic Advisor" as Advisor
actor "catalog.csusb.edu" as CAT <<external>>
actor "Roadmap PDFs" as RM <<external>>
rectangle "Adaptive Degree Pathway Planner" {
  usecase "Establish Starting Point\n(pick a student or upload a transcript)" as UC1
  usecase "Generate Term Pathway" as UC2
  usecase "Simulate What-If" as UC3
  usecase "Recalculate Pathway on\nFailure/Delay" as UC4
  usecase "Recover with Summer / Winter" as UC8
  usecase "Show Bottlenecks" as UC9
  usecase "Flag Catalog vs. Roadmap\nData Conflicts" as UC5
  usecase "Validate a Plan\n(approval: FR-18, not built)" as UC6
  usecase "Ingest Program Data" as UC7
}
Student --> UC1
Student --> UC2
Student --> UC3
Student --> UC9
Advisor --> UC5
Advisor --> UC6
UC3 ..> UC4 : <<include>>
UC8 ..> UC4 : <<extend>>
UC2 ..> UC5 : <<include>>
UC7 ..> UC5 : <<extend>>
CAT --> UC7
RM --> UC7
@enduml
```

## 2. Class diagram (structure)

**Summary.** The domain model for DR-01/DR-02. The prerequisite graph is the source of truth: `PrerequisiteEdge` links two `Course`s, and requirement groups are a view over it (EV-09 hybrid schema, ADR-02). `Course.discrepancy_flag` and `Catalog.discrepancies` are where catalog and roadmap disagreements surface. A `StudentProfile` carries its term-by-term `history` (DR-04), and a `Plan` records the opted-in Summer/Winter terms and the courses credited by Pass events.

```mermaid
classDiagram
  class Course {
    +id: str
    +title: str
    +catalog_units: int
    +roadmap_units: int
    +term_offered: Fall|Spring|Both|Unknown
    +offering_confidence: high|low|unknown
    +discrepancy_flag: bool
    +requirement_groups: list
    +min_standing_units: int
    +placeholder: bool
    +satisfied_by: list
  }
  class PrerequisiteEdge {
    +from_course: str
    +to_course: str
    +condition: AND|OR
    +group: int
    +grade_minimum: str
    +concurrent_ok: bool
  }
  class Catalog {
    +courses
    +g: DiGraph
    +program: groups
    +priority
    +lab_for
    +entry_assumed
    +discrepancies: list
    +required(profile)
  }
  class StudentProfile {
    +id: str
    +completed_courses: dict
    +in_progress_courses: list
    +history: list
    +transfer_units: int
    +unit_load_preference: int
    +start_term: str
  }
  class PastTerm {
    +term_label: str
    +grades: dict
  }
  class Plan {
    +student_id: str
    +unit_cap: int
    +summers: list
    +winters: list
    +credited: dict
  }
  class TermPlan {
    +term_label: str
    +courses: list
    +total_units: int
    +warnings: list
    +unit_cap: int
  }
  class ScenarioEvent {
    +event_type: Pass|Fail|Withdraw|Add Summer|Add Winter|Change Unit Load
    +course_id: str
    +term_label: str
    +unit_load: int
  }
  Catalog "1" o-- "*" Course
  Catalog "1" o-- "*" PrerequisiteEdge
  PrerequisiteEdge "*" --> "1" Course : from_course
  PrerequisiteEdge "*" --> "1" Course : to_course
  StudentProfile "1" *-- "*" PastTerm
  StudentProfile "1" --> "*" Plan : planned as
  Plan "1" *-- "*" TermPlan
  TermPlan "*" ..> "*" Course : places by id
  ScenarioEvent "*" ..> "1" Plan : applied to a copy of
  ScenarioEvent "*" ..> "0..1" Course : course_id
```

`RequirementGroup` and `DataConflictWarning` from the modeling brief are not classes: groups are `Catalog.program["groups"]` resolved by `Catalog.required()`, and conflicts are strings in `Catalog.discrepancies` plus `results/roadmap_audit.json`.

```plantuml
@startuml
class Course {
  +id : str
  +title : str
  +catalog_units : int
  +roadmap_units : int
  +term_offered : Fall|Spring|Both|Unknown
  +offering_confidence : high|low|unknown
  +discrepancy_flag : bool
  +requirement_groups : list
  +min_standing_units : int
  +placeholder : bool
  +satisfied_by : list
}
class PrerequisiteEdge {
  +from_course : str
  +to_course : str
  +condition : AND|OR
  +group : int
  +grade_minimum : str
  +concurrent_ok : bool
}
class Catalog {
  +courses
  +g : DiGraph
  +program
  +priority
  +lab_for
  +entry_assumed
  +discrepancies : list
  +required(profile)
}
class StudentProfile {
  +id : str
  +completed_courses : dict
  +in_progress_courses : list
  +history : list
  +transfer_units : int
  +unit_load_preference : int
  +start_term : str
}
class PastTerm {
  +term_label : str
  +grades : dict
}
class Plan {
  +student_id : str
  +unit_cap : int
  +summers : list
  +winters : list
  +credited : dict
}
class TermPlan {
  +term_label : str
  +courses : list
  +total_units : int
  +warnings : list
  +unit_cap : int
}
class ScenarioEvent {
  +event_type : Pass|Fail|Withdraw|\nAdd Summer|Add Winter|Change Unit Load
  +course_id : str
  +term_label : str
  +unit_load : int
}
Catalog "1" o-- "*" Course
Catalog "1" o-- "*" PrerequisiteEdge
PrerequisiteEdge "*" --> "1" Course : from_course
PrerequisiteEdge "*" --> "1" Course : to_course
StudentProfile "1" *-- "*" PastTerm
StudentProfile "1" --> "*" Plan : planned as
Plan "1" *-- "*" TermPlan
TermPlan "*" ..> "*" Course : places by id
ScenarioEvent "*" ..> "1" Plan : applied to a copy of
ScenarioEvent "*" ..> "0..1" Course : course_id
@enduml
```

## 3. Sequence diagram: recalculation after failing CSE 2020

**Summary.** Traces FR-04, FR-10, FR-12, FR-24 and NFR-11 for the highest-impact bottleneck course. The API is the controller. `apply_scenario` removes the failed course and its planned descendants, re-places them from the next term, and returns the before/after delta. The API then runs `recover()` when graduation slipped. The `alt` branches are a valid result and an unplaceable or mismatched request, which `/scenario` answers with 400. `apply_scenario` does not call `validate_plan`: the rules are applied inside `place()`, and `/validate` is a separate endpoint. There is no authorization branch because the API has no sign-in yet (NFR-01, OQ-06).

```mermaid
sequenceDiagram
  actor U as Student / Advisor
  participant UI as Web client
  participant API as API (controller)
  participant E as Engine: apply_scenario
  participant G as Catalog DAG
  participant P as place()
  participant R as recover()
  U->>UI: Fail CSE 2020 in its planned term
  UI->>API: POST /scenario {plan, event: Fail}
  API->>API: check body shape (KnownPlan, EventIn)
  API->>E: apply_scenario(profile, plan, event)
  E->>G: descendants(CSE 2020) ∩ planned from that term
  G-->>E: affected set (plus a moved lab's lecture)
  E->>E: remove affected set, keep everything else in place
  E->>E: drop kept courses that lose class standing
  E->>P: re-place affected set from the next term
  alt placeable
    P-->>E: new terms
    E->>E: timeline before/after → delta, one-sentence explanation, moved
    E-->>API: {plan', timeline, delta_terms, moved, explanation}
    opt delta_terms > 0
      API->>R: recover(profile, plan', original graduation, event term)
      R-->>API: fewest Summer/Winter terms that win the time back, or none
    end
    API-->>UI: 200 result (+ recovery)
    UI-->>U: new graduation term, ripple summary, Keep / Discard
  else unknown course, course not in that term, or a course that cannot be placed
    P-->>E: ValueError (blocking course and constraint)
    E-->>API: ValueError
    API-->>UI: 400 message
    UI-->>U: the reason, the saved plan is unchanged
  end
```

```plantuml
@startuml
actor "Student / Advisor" as U
participant "Web client" as UI
participant "API (controller)" as API
participant "Engine: apply_scenario" as E
participant "Catalog DAG" as G
participant "place()" as P
participant "recover()" as R
U -> UI : Fail CSE 2020 in its planned term
UI -> API : POST /scenario {plan, event: Fail}
API -> API : check body shape (KnownPlan, EventIn)
API -> E : apply_scenario(profile, plan, event)
E -> G : descendants(CSE 2020) ∩ planned from that term
G --> E : affected set (plus a moved lab's lecture)
E -> E : remove affected set, keep the rest in place
E -> E : drop kept courses that lose class standing
E -> P : re-place affected set from the next term
alt placeable
  P --> E : new terms
  E -> E : timeline before/after -> delta, explanation, moved
  E --> API : {plan', timeline, delta_terms, moved, explanation}
  opt delta_terms > 0
    API -> R : recover(profile, plan', original graduation, event term)
    R --> API : fewest Summer/Winter terms that win time back, or none
  end
  API --> UI : 200 result (+ recovery)
  UI --> U : new graduation term, ripple summary, Keep / Discard
else unknown course, not in that term, or unplaceable
  P --> E : ValueError
  E --> API : ValueError
  API --> UI : 400 message
  UI --> U : the reason; saved plan unchanged
end
@enduml
```

## 4. Activity diagram: pathway generation and recalculation

**Summary.** The process behind FR-03..FR-08, FR-10, FR-13 and FR-24, and the source for the SRS §6 rules. `make_plan` calls `place()`; `apply_scenario` clears the invalidated part of a plan and calls the same `place()`. Each term repeats a candidate pass, because a corequisite or lab placed in the term can unlock its partner. The guards are the ones in the code: standing, prerequisites, offering, and the unit cap. There is no parallel branch: GE and core courses share one priority-ordered candidate list. Mermaid has no activity diagram, so it is a flowchart.

```mermaid
flowchart TD
  S((●)) --> A[Load profile and catalog]
  A --> B[baseline: credit completed and in-progress courses, resolve remaining required courses]
  B --> C{Scenario event?}
  C -- no --> D[Start at the first term]
  C -- yes --> C1[Compute invalidated set: descendants, lab partners, lost standing]
  C1 --> C2[Clear those courses, keep pinned Pass terms, start after the event term]
  C2 --> D
  D --> E[Take the next term; Summer and Winter exist only if opted in]
  E --> F[Candidates: standing met and prerequisites met, sorted by priority then id]
  F --> G{Offered in this term?}
  G -- no --> W[Warn: waiting for next offering]
  G -- yes --> H{Lab bundle and unit cap fit?}
  H -- no --> W
  H -- yes --> I[Place course with its lab and corequisite partners]
  I --> J{Anything placed this pass?}
  W --> J
  J -- yes --> F
  J -- no --> K{Courses left to place?}
  K -- yes and under 30 terms --> E
  K -- no --> L[Compute timeline: graduation term, critical path]
  K -- yes and over 30 terms --> X[ValueError naming each blocking course: 422 from /plan, 400 from /scenario]
  L --> M{Event delayed graduation?}
  M -- yes --> N[recover: try Summer/Winter terms]
  M -- no --> Z((◉))
  N --> Z
  X --> Z
```

```plantuml
@startuml
start
:Load profile and catalog;
:baseline: credit completed and in-progress courses,\nresolve remaining required courses;
if (Scenario event?) then (yes)
  :Compute invalidated set\n(descendants, lab partners, lost standing);
  :Clear them, keep pinned Pass terms;
else (no)
endif
repeat :Take next term\n(Summer / Winter only if opted in);
  repeat :Candidates: standing and prerequisites met,\nsorted by priority then id;
    while (More ready candidates?) is (yes)
      if (Offered in this term?) then ([yes])
        if (Lab bundle and unit cap fit?) then ([yes])
          :Place course with lab and corequisite partners;
        else ([no])
          :Skip for this term;
        endif
      else ([no])
        :Warn: waiting for next offering;
      endif
    endwhile (no)
  repeat while (Anything placed this pass?) is (yes)
repeat while (Courses left and under 30 terms?) is (yes)
if (Courses still unplaced?) then (yes)
  :ValueError naming each blocking course\n(422 /plan, 400 /scenario);
  stop
else (no)
endif
:Compute timeline;
if (Event delayed graduation?) then (yes)
  :recover(): try Summer / Winter terms;
endif
stop
@enduml
```

## 5. State diagram: pathway lifecycle

**Summary.** The lifecycle the code implements for a plan, as the client drives it (FR-15, FR-17). The server is stateless, so every state lives in the browser (the current plan, the preview, and the stack of kept plans). The brief's `ValidatingConstraints` / `ConflictFlagged` / `ApprovedBaseline` states do not exist: the engine enforces the rules while placing, `/validate` is a stateless check, and approval needs the advisor view (FR-18).

```mermaid
stateDiagram-v2
  [*] --> Loading: choose student or upload transcript
  Loading --> Baseline: POST /plan ok
  Loading --> Failed: 404 or 422 (unplaceable, bad cap, unreadable transcript)
  Failed --> Loading: change student, cap, or file
  Baseline --> Previewing: what-if
  Baseline --> Kept: choose an alternative pathway (FR-17)
  Baseline --> Loading: change student or base unit cap
  Previewing --> Baseline: Discard (no kept changes)
  Previewing --> Kept: Keep this plan
  Previewing --> Previewing: another what-if replaces the preview
  Kept --> Previewing: another what-if on the kept plan
  Kept --> Kept: Undo last (earlier kept changes remain)
  Kept --> Baseline: Undo last (only one kept change) or Reset to baseline
  Kept --> Loading: change student or base unit cap
```

A 400 while previewing shows a message and leaves the current plan as it was.

```plantuml
@startuml
[*] --> Loading : choose student or\nupload transcript
Loading --> Baseline : POST /plan ok
Loading --> Failed : 404 or 422
Failed --> Loading : change student, cap, or file
Baseline --> Previewing : what-if
Baseline --> Kept : choose an alternative (FR-17)
Baseline --> Loading : change student or base cap
Previewing --> Baseline : Discard (no kept changes)
Previewing --> Kept : Keep this plan
Previewing --> Previewing : another what-if
Kept --> Previewing : another what-if
Kept --> Kept : Undo last (more history)
Kept --> Baseline : Undo last (last one) /\nReset to baseline
Kept --> Loading : change student or base cap
@enduml
```
