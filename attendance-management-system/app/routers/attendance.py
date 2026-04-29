"""
app/routers/attendance.py
--------------------------
FastAPI router for attendance-related endpoints.

All endpoints are JWT-protected. Role rules:
  - Roster + bulk attendance: teacher/admin only, must own the course (or be admin).
  - Student attendance report + bunk calculator: student (own data only) or teacher/admin (any).
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_teacher, get_current_user
from app.models.course import Course
from app.models.user import UserRole
from app.schemas.attendance import (
    BulkAttendanceRequest,
    BulkAttendanceResponse,
    BunkCalculatorResult,
    StudentAttendanceReport,
)
from app.schemas.course import CourseRosterResponse
from app.services import attendance_service

router = APIRouter(tags=["Attendance"])


async def _require_course_access(
    course_id: uuid.UUID,
    current_user,
    db: AsyncSession,
) -> Course:
    """
    Fetches a course and verifies the current user is allowed to manage it.
    Admins bypass the ownership check; teachers must own the course.
    """
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found.")

    if current_user.role == UserRole.admin:
        return course

    if course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the teacher of this course.",
        )

    return course


# =============================================================================
# ENDPOINT 1: GET CLASS ROSTER
# =============================================================================

@router.get(
    "/courses/{course_id}/roster",
    response_model=CourseRosterResponse,
    summary="Get Class Roster",
    description="Returns enrolled students for a course. Teacher must own the course (admin bypasses).",
    responses={
        200: {"description": "Class roster returned successfully."},
        403: {"description": "Not the teacher of this course."},
        404: {"description": "Course not found."},
    },
)
async def get_class_roster(
    course_id: uuid.UUID,
    current_user=Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    await _require_course_access(course_id, current_user, db)
    return await attendance_service.get_class_roster(db=db, course_id=course_id)


# =============================================================================
# ENDPOINT 2: SUBMIT BULK ATTENDANCE
# =============================================================================

@router.post(
    "/attendance/bulk",
    response_model=BulkAttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Bulk Attendance",
    description=(
        "Submit attendance for an entire class. The submitting teacher is taken "
        "from the JWT — no query param needed. Supports UPSERT (correcting past records)."
    ),
    responses={
        201: {"description": "Attendance submitted successfully."},
        403: {"description": "Not the teacher of this course."},
        404: {"description": "Course not found."},
        422: {"description": "Student not enrolled in the course."},
    },
)
async def submit_bulk_attendance(
    payload: BulkAttendanceRequest,
    current_user=Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    await _require_course_access(payload.course_id, current_user, db)
    return await attendance_service.submit_bulk_attendance(
        db=db,
        course_id=payload.course_id,
        attendance_date=payload.attendance_date,
        records=payload.records,
        recorded_by_id=current_user.id,
    )


# =============================================================================
# ENDPOINT 3: GET STUDENT ATTENDANCE REPORT
# =============================================================================

@router.get(
    "/students/{student_id}/attendance",
    response_model=StudentAttendanceReport,
    summary="Get Student Attendance Report",
    description=(
        "Returns attendance breakdown for a student. "
        "Students can only request their own data. Teachers/admins can request any student."
    ),
    responses={
        200: {"description": "Attendance report returned successfully."},
        403: {"description": "Students may only view their own attendance."},
        404: {"description": "Student not found."},
    },
)
async def get_student_attendance(
    student_id: uuid.UUID,
    course_id: Optional[uuid.UUID] = Query(
        default=None,
        description="Filter report to a single course. If omitted, all courses are included."
    ),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.student and current_user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only view their own attendance data.",
        )

    return await attendance_service.get_student_attendance(
        db=db,
        student_id=student_id,
        course_id=course_id,
    )


# =============================================================================
# ENDPOINT 4: BUNK CALCULATOR
# =============================================================================

@router.get(
    "/students/{student_id}/bunk-calculator",
    response_model=BunkCalculatorResult,
    summary="Bunk Calculator",
    description=(
        "Calculates how many classes a student can safely miss (if ≥75%) "
        "or must attend consecutively to recover (if <75%). "
        "Students can only query their own data."
    ),
    responses={
        200: {"description": "Bunk calculation returned successfully."},
        403: {"description": "Students may only query their own data."},
        404: {"description": "Student not found."},
    },
)
async def get_bunk_calculator(
    student_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.student and current_user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only query their own bunk calculator.",
        )

    return await attendance_service.calculate_bunk_info(db=db, student_id=student_id)


# =============================================================================
# ENDPOINT 5: EXPORT ATTENDANCE AS CSV
# =============================================================================

@router.get(
    "/students/{student_id}/attendance/export",
    summary="Export Attendance as CSV",
    description="Downloads attendance data as a CSV file. Students can only export their own data.",
    responses={
        200: {"content": {"text/csv": {}}, "description": "CSV file download."},
        403: {"description": "Students may only export their own data."},
    },
)
async def export_attendance_csv(
    student_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import StreamingResponse
    import io

    if current_user.role == UserRole.student and current_user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only export their own attendance data.",
        )

    report = await attendance_service.get_student_attendance(db=db, student_id=student_id)

    lines = ["Course Code,Course Name,Total Classes,Present,Absent,Late,Attendance %\n"]
    for c in report.courses:
        lines.append(
            f"{c.course_code},{c.course_name},{c.total_classes},"
            f"{c.present_count},{c.absent_count},{c.late_count},"
            f"{c.attendance_percentage}\n"
        )
    lines.append(f"\nOverall Attendance %,{report.overall_percentage}\n")

    content = "".join(lines)

    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="attendance_{student_id}.csv"'},
    )


# =============================================================================
# ENDPOINT 6: EXPORT COURSE ATTENDANCE AS CSV
# =============================================================================

from datetime import date

@router.get(
    "/courses/{course_id}/attendance/export",
    summary="Export Course Attendance as CSV",
    description="Downloads attendance data for an entire course as a CSV file. Teachers must own the course. Admins bypass.",
    responses={
        200: {"content": {"text/csv": {}}, "description": "CSV file download."},
        403: {"description": "Not the teacher of this course."},
    },
)
async def export_course_attendance_route(
    course_id: uuid.UUID,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user=Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import StreamingResponse
    import io

    # Check authorization
    await _require_course_access(course_id, current_user, db)

    csv_content = await attendance_service.export_course_attendance_csv(
        db=db,
        course_id=course_id,
        start_date=start_date,
        end_date=end_date,
    )

    filename = f"course_{course_id}_attendance.csv"
    if start_date or end_date:
        filename = f"course_{course_id}_attendance_{start_date or 'any'}_to_{end_date or 'any'}.csv"

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

