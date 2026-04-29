"""
app/services/attendance_service.py
------------------------------------
Business logic layer for all attendance-related operations.

Service layer responsibilities:
  1. Orchestrate DB queries (via SQLAlchemy ORM)
  2. Enforce business rules BEFORE hitting the DB
  3. Translate DB errors into domain exceptions
  4. Keep routers clean — routers only call service functions

Three core operations:
  A. get_class_roster()         — fetch all enrolled students for a course
  B. submit_bulk_attendance()   — record attendance for an entire class on a date
  C. get_student_attendance()   — compute a student's attendance % per course
"""

import uuid
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import (
    BusinessRuleViolationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceEntry,
    BulkAttendanceResponse,
    BunkCalculatorResult,
    CourseAttendanceSummary,
    StudentAttendanceReport,
)
from app.schemas.course import CourseRosterResponse, RosterStudentEntry


# =============================================================================
# A. GET CLASS ROSTER
# =============================================================================

async def get_class_roster(
    db: AsyncSession,
    course_id: uuid.UUID,
) -> CourseRosterResponse:
    """
    Fetches all students currently enrolled in a course.

    Query strategy:
    - Join Enrollments → Users to get student details in a single query.
    - Use selectinload for the course's teacher relationship to avoid N+1.

    Args:
        db:        Async database session (injected by FastAPI dependency).
        course_id: UUID of the course whose roster to fetch.

    Returns:
        CourseRosterResponse with course metadata and a list of enrolled students.

    Raises:
        ResourceNotFoundError: If the course_id does not exist.
    """
    # --- Step 1: Fetch the course (with teacher pre-loaded) ---
    course_query = (
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.teacher))  # Avoids separate query for teacher
    )
    result = await db.execute(course_query)
    course = result.scalar_one_or_none()

    if course is None:
        raise ResourceNotFoundError("Course", str(course_id))

    # --- Step 2: Fetch all enrolled students via a JOIN ---
    # This is a single efficient query: Enrollment JOIN User WHERE course_id = ?
    roster_query = (
        select(Enrollment, User)
        .join(User, Enrollment.student_id == User.id)
        .where(
            and_(
                Enrollment.course_id == course_id,
                User.is_active == True,   # noqa: E712  # Only active students
            )
        )
        .order_by(User.last_name, User.first_name)  # Alphabetical order
    )
    rows = await db.execute(roster_query)
    enrollment_user_pairs = rows.all()

    # --- Step 3: Build the response ---
    students = [
        RosterStudentEntry(
            enrollment_id=enrollment.id,
            student_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            enrolled_at=enrollment.enrolled_at,
        )
        for enrollment, user in enrollment_user_pairs
    ]

    teacher_name = course.teacher.full_name if course.teacher else None

    return CourseRosterResponse(
        course_id=course.id,
        course_name=course.name,
        course_code=course.code,
        semester=course.semester,
        year=course.year,
        teacher_name=teacher_name,
        student_count=len(students),
        students=students,
    )


# =============================================================================
# B. SUBMIT BULK ATTENDANCE
# =============================================================================

async def submit_bulk_attendance(
    db: AsyncSession,
    course_id: uuid.UUID,
    attendance_date: date,
    records: list[AttendanceEntry],
    recorded_by_id: uuid.UUID,
) -> BulkAttendanceResponse:
    """
    Records attendance for multiple students in a course on a specific date.

    Design decisions:
    - Uses UPSERT semantics: if attendance already exists for the same
      (enrollment_id, attendance_date), it is UPDATED (not re-inserted).
      This allows teachers to correct mistakes.
    - Validates that every student_id in `records` is actually enrolled
      in the course — prevents recording attendance for outsiders.
    - All records are inserted in a single transaction for atomicity.

    Args:
        db:               Async database session.
        course_id:        UUID of the course.
        attendance_date:  The class date.
        records:          List of AttendanceEntry objects (student_id + status).
        recorded_by_id:   UUID of the teacher/admin submitting this record.

    Returns:
        BulkAttendanceResponse with counts of created and updated records.

    Raises:
        ResourceNotFoundError:     If the course doesn't exist.
        BusinessRuleViolationError: If any student_id is not enrolled in the course.
    """
    # --- Step 1: Verify the course exists ---
    course = await db.get(Course, course_id)
    if course is None:
        raise ResourceNotFoundError("Course", str(course_id))

    # --- Step 2: Verify the recorder (teacher/admin) exists ---
    recorder = await db.get(User, recorded_by_id)
    if recorder is None:
        raise ResourceNotFoundError("User (recorder)", str(recorded_by_id))

    # --- Step 3: Load all enrollments for this course in ONE query ---
    # Build a lookup map: student_id → enrollment_id
    enrollment_query = select(Enrollment).where(Enrollment.course_id == course_id)
    result = await db.execute(enrollment_query)
    enrollments = result.scalars().all()
    enrollment_map: dict[uuid.UUID, uuid.UUID] = {
        e.student_id: e.id for e in enrollments
    }

    # --- Step 4: Validate all submitted student IDs are enrolled ---
    submitted_student_ids = {entry.student_id for entry in records}
    not_enrolled = submitted_student_ids - set(enrollment_map.keys())
    if not_enrolled:
        unenrolled_list = ", ".join(str(sid) for sid in not_enrolled)
        raise BusinessRuleViolationError(
            f"The following student(s) are not enrolled in course '{course.code}': "
            f"{unenrolled_list}"
        )

    # --- Step 5: Check for existing records (for upsert logic) ---
    enrollment_ids = list(enrollment_map.values())
    existing_query = select(AttendanceRecord).where(
        and_(
            AttendanceRecord.enrollment_id.in_(enrollment_ids),
            AttendanceRecord.attendance_date == attendance_date,
        )
    )
    existing_result = await db.execute(existing_query)
    existing_records = existing_result.scalars().all()
    # Map: enrollment_id → existing AttendanceRecord (for update)
    existing_map: dict[uuid.UUID, AttendanceRecord] = {
        r.enrollment_id: r for r in existing_records
    }

    # --- Step 6: Create or Update attendance records ---
    created_count = 0
    updated_count = 0

    for entry in records:
        enrollment_id = enrollment_map[entry.student_id]

        if enrollment_id in existing_map:
            # UPDATE existing record (teacher is correcting a mistake)
            existing = existing_map[enrollment_id]
            existing.status = entry.status
            existing.remarks = entry.remarks
            existing.recorded_by = recorded_by_id
            db.add(existing)
            updated_count += 1
        else:
            # CREATE new attendance record
            new_record = AttendanceRecord(
                enrollment_id=enrollment_id,
                attendance_date=attendance_date,
                status=entry.status,
                remarks=entry.remarks,
                recorded_by=recorded_by_id,
            )
            db.add(new_record)
            created_count += 1

    # --- Step 7: Flush to DB (within the transaction managed by get_db) ---
    try:
        await db.flush()  # Write to DB but don't commit yet (get_db handles commit)
    except IntegrityError as e:
        # Safety net — should be prevented by Step 4 & 5, but guards against
        # race conditions in concurrent requests
        raise DuplicateResourceError(
            f"Attendance conflict detected during flush: {e.orig}"
        ) from e

    return BulkAttendanceResponse(
        message="Attendance submitted successfully.",
        course_id=course_id,
        attendance_date=attendance_date,
        records_created=created_count,
        records_updated=updated_count,
    )


# =============================================================================
# C. GET STUDENT ATTENDANCE PERCENTAGE
# =============================================================================

async def get_student_attendance(
    db: AsyncSession,
    student_id: uuid.UUID,
    course_id: uuid.UUID | None = None,
) -> StudentAttendanceReport:
    """
    Calculates a student's attendance percentage for all their enrolled courses
    (or a specific course if course_id is provided).

    Calculation logic:
    - 'present' counts as attended.
    - 'late' also counts as attended (partial credit — configurable policy).
    - 'absent' does not count.
    - Percentage = (present + late) / total_classes * 100

    Args:
        db:         Async database session.
        student_id: UUID of the student.
        course_id:  Optional. If provided, only returns data for that course.

    Returns:
        StudentAttendanceReport with per-course breakdowns and an overall %.

    Raises:
        ResourceNotFoundError: If the student doesn't exist.
    """
    # --- Step 1: Verify the student exists ---
    student = await db.get(User, student_id)
    if student is None:
        raise ResourceNotFoundError("Student", str(student_id))
    if student.role != UserRole.student:
        raise BusinessRuleViolationError(
            f"User '{student_id}' is not a student (role: {student.role})."
        )

    # --- Step 2: Build the base query for enrollments + courses ---
    enrollment_query = (
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .options(
            selectinload(Enrollment.course).selectinload(Course.teacher),  # Pre-load course and its teacher
            selectinload(Enrollment.attendance_records),  # Pre-load all attendance records
        )
    )
    if course_id:
        enrollment_query = enrollment_query.where(Enrollment.course_id == course_id)

    result = await db.execute(enrollment_query)
    enrollments = result.scalars().all()

    if not enrollments:
        raise BusinessRuleViolationError(
            f"Student '{student_id}' has no enrollments"
            + (f" for course '{course_id}'." if course_id else ".")
        )

    # --- Step 3: Calculate per-course statistics ---
    course_summaries: list[CourseAttendanceSummary] = []
    total_attended_all = 0
    total_classes_all = 0

    for enrollment in enrollments:
        records = enrollment.attendance_records

        total = len(records)
        present = sum(1 for r in records if r.status == AttendanceStatus.present)
        late    = sum(1 for r in records if r.status == AttendanceStatus.late)
        absent  = sum(1 for r in records if r.status == AttendanceStatus.absent)

        # Late counts as attended in this policy
        attended = present + late
        percentage = (attended / total * 100) if total > 0 else 0.0

        total_attended_all += attended
        total_classes_all  += total

        course_summaries.append(
            CourseAttendanceSummary(
                course_id=enrollment.course.id,
                course_name=enrollment.course.name,
                course_code=enrollment.course.code,
                teacher_name=enrollment.course.teacher.full_name if enrollment.course.teacher else None,
                total_classes=total,
                present_count=present,
                absent_count=absent,
                late_count=late,
                attendance_percentage=round(percentage, 2),
            )
        )

    # --- Step 4: Overall weighted percentage ---
    overall_pct = (
        (total_attended_all / total_classes_all * 100)
        if total_classes_all > 0
        else 0.0
    )

    return StudentAttendanceReport(
        student_id=student.id,
        student_name=student.full_name,
        courses=course_summaries,
        overall_percentage=round(overall_pct, 2),
    )


# =============================================================================
# D. BUNK CALCULATOR
# =============================================================================

async def calculate_bunk_info(
    db: AsyncSession,
    student_id: uuid.UUID,
) -> BunkCalculatorResult:
    """
    Calculates how many classes a student can safely skip (if ≥75%)
    or must attend consecutively to reach 75% (if below threshold).

    Formulas (threshold P = 0.75, attended A, total T):
      If A/T >= P:  safe_to_bunk  = floor((A - P*T) / P)
      If A/T <  P:  must_attend   = ceil((P*T - A) / (1 - P))

    Raises:
        ResourceNotFoundError: If the student doesn't exist.
    """
    import math

    student = await db.get(User, student_id)
    if student is None:
        raise ResourceNotFoundError("Student", str(student_id))
    if student.role != UserRole.student:
        raise BusinessRuleViolationError(
            f"User '{student_id}' is not a student (role: {student.role})."
        )

    enrollment_query = (
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .options(selectinload(Enrollment.attendance_records))
    )
    result = await db.execute(enrollment_query)
    enrollments = result.scalars().all()

    total_classes = 0
    attended_classes = 0
    for enrollment in enrollments:
        records = enrollment.attendance_records
        total_classes += len(records)
        attended_classes += sum(
            1 for r in records
            if r.status in (AttendanceStatus.present, AttendanceStatus.late)
        )

    if total_classes == 0:
        return BunkCalculatorResult(
            student_id=student.id,
            student_name=student.full_name,
            overall_percentage=0.0,
            total_classes=0,
            attended_classes=0,
            status="no_data",
            safe_to_bunk=None,
            must_attend=None,
            message="No attendance records found yet.",
        )

    THRESHOLD = 0.75
    overall_pct = attended_classes / total_classes

    if overall_pct >= THRESHOLD:
        # How many more can be skipped and stay at or above 75%?
        # (A / (T + X)) >= P  →  X <= (A - P*T) / P
        safe_to_bunk = math.floor((attended_classes - THRESHOLD * total_classes) / THRESHOLD)
        return BunkCalculatorResult(
            student_id=student.id,
            student_name=student.full_name,
            overall_percentage=round(overall_pct * 100, 2),
            total_classes=total_classes,
            attended_classes=attended_classes,
            status="safe",
            safe_to_bunk=safe_to_bunk,
            must_attend=None,
            message=(
                f"You're at {round(overall_pct * 100, 1)}% — safe! "
                f"You can miss up to {safe_to_bunk} more class{'es' if safe_to_bunk != 1 else ''} "
                f"and still stay above 75%."
            ),
        )
    else:
        # How many consecutive classes must be attended to reach 75%?
        # ((A + N) / (T + N)) >= P  →  N >= (P*T - A) / (1 - P)
        must_attend = math.ceil(
            (THRESHOLD * total_classes - attended_classes) / (1 - THRESHOLD)
        )
        return BunkCalculatorResult(
            student_id=student.id,
            student_name=student.full_name,
            overall_percentage=round(overall_pct * 100, 2),
            total_classes=total_classes,
            attended_classes=attended_classes,
            status="critical",
            safe_to_bunk=None,
            must_attend=must_attend,
            message=(
                f"You're at {round(overall_pct * 100, 1)}% — below 75%! "
                f"Attend the next {must_attend} consecutive class{'es' if must_attend != 1 else ''} "
                f"to recover."
            ),
        )


# =============================================================================
# E. EXPORT COURSE ATTENDANCE
# =============================================================================

async def export_course_attendance_csv(
    db: AsyncSession,
    course_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> str:
    from app.models.attendance import AttendanceRecord
    
    course = await db.get(Course, course_id)
    if not course:
        raise ResourceNotFoundError("Course", str(course_id))

    roster_query = (
        select(Enrollment, User)
        .join(User, Enrollment.student_id == User.id)
        .where(
            and_(
                Enrollment.course_id == course_id,
                User.is_active == True,
            )
        )
        .order_by(User.last_name, User.first_name)
    )
    result = await db.execute(roster_query)
    enrollments_users = result.all()
    
    enrollment_ids = [e.id for e, u in enrollments_users]
    student_map = {e.id: u for e, u in enrollments_users}

    if not enrollment_ids:
        return "Student Name,Email,Attendance Date,Status,Remarks\n"

    attendance_query = select(AttendanceRecord).where(
        AttendanceRecord.enrollment_id.in_(enrollment_ids)
    )
    if start_date:
        attendance_query = attendance_query.where(AttendanceRecord.attendance_date >= start_date)
    if end_date:
        attendance_query = attendance_query.where(AttendanceRecord.attendance_date <= end_date)
        
    attendance_query = attendance_query.order_by(AttendanceRecord.attendance_date.desc())
    
    result = await db.execute(attendance_query)
    records = result.scalars().all()

    lines = ["Student Name,Email,Attendance Date,Status,Remarks\n"]
    for record in records:
        user = student_map[record.enrollment_id]
        remarks = (record.remarks or "").replace(",", " ")
        lines.append(f"{user.full_name},{user.email},{record.attendance_date},{record.status.value},{remarks}\n")
        
    return "".join(lines)
