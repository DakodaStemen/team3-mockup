"""Pydantic models shared by the engine, API, and guardrail layer (spec: Data models)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TermOffered = Literal["Fall", "Spring", "Both", "Unknown"]
EventType = Literal["Pass", "Fail", "Withdraw", "Add Summer", "Change Unit Load"]


class Course(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str = ""
    catalog_units: int
    roadmap_units: int | None = None
    discrepancy_flag: bool = False
    term_offered: TermOffered = "Unknown"
    requirement_groups: list[str] = []
    min_standing_units: int = 0  # e.g. 90 for "Senior standing"
    placeholder: bool = False  # GE / free-elective slot rather than a specific course
    prereq_text: str = ""
    offering_confidence: Literal["high", "low", "unknown"] = "unknown"  # roadmaps agree / conflict / no roadmap
    satisfied_by: list[str] = []  # GE slot: catalog courses that fill it (e.g. ENG 1070A for GE 1A)
    satisfied_by_min_grade: str = "D-"

    @model_validator(mode="after")
    def _flag(self):
        # Catalog is authoritative for units; disagreement is flagged, never resolved.
        self.discrepancy_flag = self.roadmap_units is not None and self.roadmap_units != self.catalog_units
        return self


class PrerequisiteEdge(BaseModel):
    model_config = ConfigDict(extra="ignore")
    from_course: str
    to_course: str
    condition: Literal["AND", "OR"] = "AND"  # OR = one of several alternatives in the same group
    group: int = 0  # groups are ANDed; edges within a group are ORed
    grade_minimum: str = "D-"
    concurrent_ok: bool = False  # corequisite / "pre- or co-requisite": same term is fine


UNIT_LOAD_RANGE = (3, 21)  # allowed unit cap for Change Unit Load, on every path (API, NL guardrail, engine)


class StudentProfile(BaseModel):
    id: str
    name: str
    completed_courses: dict[str, str] = {}  # course_id -> letter grade
    in_progress_courses: list[str] = []
    remaining_requirement_groups: list[str] | None = None  # None = every program group
    choices: dict[str, list[str]] = {}  # requirement group -> chosen courses (else engine picks)
    transfer_units: int = 0  # units counted toward standing but not tied to catalog courses
    unit_load_preference: int = Field(15, ge=UNIT_LOAD_RANGE[0], le=UNIT_LOAD_RANGE[1])
    start_term: str = "Fall 2026"
    notes: str = ""


class TermPlan(BaseModel):
    term_label: str
    courses: list[str] = []
    total_units: int = 0
    warnings: list[str] = []
    unit_cap: int | None = None  # cap in force when the engine filled this term (summer: at most 8); None = plan's


class ScenarioEvent(BaseModel):
    event_type: EventType
    course_id: str | None = None
    term_label: str
    unit_load: int | None = Field(None, description="New unit cap, only for Change Unit Load")


class Plan(BaseModel):
    student_id: str
    unit_cap: int
    summers: list[str] = []  # summer term labels the student opted into
    credited: dict[str, str] = {}  # course -> term it was marked passed in by a Pass scenario event
    terms: list[TermPlan] = []
