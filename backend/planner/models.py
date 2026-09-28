"""Pydantic models shared by the engine, API, and guardrail layer (spec: Data models)."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

TermOffered = Literal["Fall", "Spring", "Both", "Unknown"]
EventType = Literal["Pass", "Fail", "Withdraw", "Add Summer", "Change Unit Load"]


class Course(BaseModel):
    id: str
    title: str = ""
    catalog_units: int
    roadmap_units: int | None = None
    discrepancy_flag: bool = False
    term_offered: TermOffered = "Both"
    requirement_groups: list[str] = []

    @model_validator(mode="after")
    def _flag(self):
        # Catalog is authoritative for units; disagreement is flagged, never resolved.
        self.discrepancy_flag = self.roadmap_units is not None and self.roadmap_units != self.catalog_units
        return self


class PrerequisiteEdge(BaseModel):
    from_course: str
    to_course: str
    condition: Literal["AND", "OR"] = "AND"  # all AND edges required; at least one OR edge required
    grade_minimum: str = "D"


class StudentProfile(BaseModel):
    id: str
    name: str
    completed_courses: dict[str, str] = {}  # course_id -> letter grade
    in_progress_courses: list[str] = []
    remaining_requirement_groups: list[str] = []
    unit_load_preference: int = 15
    start_term: str = "Fall 2026"


class TermPlan(BaseModel):
    term_label: str
    courses: list[str] = []
    total_units: int = 0
    warnings: list[str] = []


class ScenarioEvent(BaseModel):
    event_type: EventType
    course_id: str | None = None
    term_label: str
    unit_load: int | None = Field(None, description="New unit cap, only for Change Unit Load")


class Plan(BaseModel):
    student_id: str
    unit_cap: int
    summers: list[str] = []  # summer term labels the student opted into
    credited: list[str] = []  # courses marked passed by a Pass scenario event
    terms: list[TermPlan] = []
