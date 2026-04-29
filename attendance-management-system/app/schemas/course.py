"""
app/schemas/course.py
---------------------
Pydantic schemas for course/subject and roster endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Student info as it appears on a course roster
# ---------------------------------------------------------------------------

class RosterStudentEntry(BaseModel):
    """
    A single student's entry in the class roster.
    Returned by GET /api/v1/courses/{course_id}/roster
    """
    enrollment_id: uuid.UUID
    student_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    enrolled_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Full Course Roster Response
# ---------------------------------------------------------------------------

class CourseRosterResponse(BaseModel):
    """
    Full class roster for a given course.
    """
    course_id: uuid.UUID
    course_name: str
    course_code: str
    semester: str
    year: int
    teacher_name: Optional[str]
    student_count: int
    students: list[RosterStudentEntry]


# ---------------------------------------------------------------------------
# Course Create / Update schemas
# ---------------------------------------------------------------------------

class CourseCreate(BaseModel):
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=20)
    credit_hours: int = Field(..., ge=1, le=6)
    department_id: uuid.UUID
    teacher_id: Optional[uuid.UUID] = None
    semester: str = Field(..., max_length=20)
    year: int = Field(..., ge=2000)


class CourseOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    credit_hours: int
    semester: str
    year: int
    is_active: bool

    model_config = {"from_attributes": True}
