"""
app/schemas/attendance.py
--------------------------
Pydantic v2 request/response schemas for attendance-related endpoints.

Why separate schemas from models?
- ORM models represent DB structure; Pydantic schemas represent API contracts.
- This separation prevents accidentally exposing internal fields (like password_hash).
- It allows independent evolution of the DB schema and API contract.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.attendance import AttendanceStatus


# ---------------------------------------------------------------------------
# Individual Attendance Entry (used within bulk submission)
# ---------------------------------------------------------------------------

class AttendanceEntry(BaseModel):
    """
    Represents a single attendance record for one student within a bulk submission.
    """
    student_id: uuid.UUID = Field(
        ...,
        description="UUID of the student whose attendance is being recorded."
    )
    status: AttendanceStatus = Field(
        ...,
        description="Attendance status: 'present', 'absent', or 'late'."
    )
    remarks: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional remarks (e.g., 'left early', 'medical leave')."
    )


# ---------------------------------------------------------------------------
# Bulk Attendance Submission Request
# ---------------------------------------------------------------------------

class BulkAttendanceRequest(BaseModel):
    """
    Request body for POST /api/v1/attendance/bulk

    Submits attendance for an entire class on a specific date.
    The teacher must be authenticated; their ID is injected server-side.
    """
    course_id: uuid.UUID = Field(
        ...,
        description="UUID of the course for which attendance is being submitted."
    )
    attendance_date: date = Field(
        ...,
        description="The date for which attendance is being recorded (YYYY-MM-DD)."
    )
    records: list[AttendanceEntry] = Field(
        ...,
        min_length=1,
        description="List of attendance entries — one per student."
    )

    @field_validator("attendance_date")
    @classmethod
    def date_cannot_be_weekend(cls, v: date) -> date:
        """
        Business rule: Attendance cannot be marked on weekends (Saturday or Sunday).
        weekday() returns 5 for Saturday, 6 for Sunday.
        """
        if v.weekday() in (5, 6):
            day_name = "Saturday" if v.weekday() == 5 else "Sunday"
            raise ValueError(f"Attendance cannot be marked on a weekend ({day_name}).")
        return v

    @field_validator("records")
    @classmethod
    def no_duplicate_students(cls, v: list[AttendanceEntry]) -> list[AttendanceEntry]:
        """Ensure the same student doesn't appear twice in one bulk submission."""
        student_ids = [entry.student_id for entry in v]
        if len(student_ids) != len(set(student_ids)):
            raise ValueError("Duplicate student IDs found in attendance records.")
        return v


# ---------------------------------------------------------------------------
# Bulk Attendance Submission Response
# ---------------------------------------------------------------------------

class BulkAttendanceResponse(BaseModel):
    """Summary response after a bulk attendance submission."""
    message: str
    course_id: uuid.UUID
    attendance_date: date
    records_created: int
    records_updated: int  # If re-submission of same date (upsert behavior)


# ---------------------------------------------------------------------------
# Individual Attendance Record (for display in reports)
# ---------------------------------------------------------------------------

class AttendanceRecordOut(BaseModel):
    """Full attendance record returned from the database."""
    id: uuid.UUID
    enrollment_id: uuid.UUID
    attendance_date: date
    status: AttendanceStatus
    remarks: Optional[str]
    recorded_at: datetime
    recorded_by: uuid.UUID

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Student Attendance Summary (percentage calculation response)
# ---------------------------------------------------------------------------

class CourseAttendanceSummary(BaseModel):
    """
    Attendance breakdown for a student in a single course.
    'late' is counted as 'present' for percentage purposes (configurable).
    """
    course_id: uuid.UUID
    course_name: str
    course_code: str
    teacher_name: Optional[str] = None
    total_classes: int
    present_count: int   # Includes 'late'
    absent_count: int
    late_count: int
    attendance_percentage: float = Field(
        ...,
        description="Percentage of classes attended (present + late) / total * 100"
    )


class StudentAttendanceReport(BaseModel):
    """Full attendance report for a student across all their courses."""
    student_id: uuid.UUID
    student_name: str
    courses: list[CourseAttendanceSummary]
    overall_percentage: float = Field(
        ...,
        description="Weighted average attendance across all courses."
    )


# ---------------------------------------------------------------------------
# Bunk Calculator Result
# ---------------------------------------------------------------------------

class BunkCalculatorResult(BaseModel):
    """
    Result of the bunk calculator for a student.
    Threshold is 75%. Tells the student how many classes they can safely miss
    (if currently safe) or must attend consecutively to recover (if critical).
    """
    student_id: uuid.UUID
    student_name: str
    overall_percentage: float
    total_classes: int
    attended_classes: int
    threshold: float = 75.0
    status: str = Field(
        ...,
        description="One of: 'safe' (≥75%), 'critical' (<75%), 'no_data' (no classes yet)."
    )
    safe_to_bunk: Optional[int] = Field(
        default=None,
        description="How many more classes the student can miss and still stay at ≥75%. Only set when status='safe'."
    )
    must_attend: Optional[int] = Field(
        default=None,
        description="How many consecutive classes the student must attend to reach 75%. Only set when status='critical'."
    )
    message: str = Field(..., description="Human-readable summary.")
