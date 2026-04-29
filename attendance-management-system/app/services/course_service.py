"""
app/services/course_service.py
------------------------------
Business logic for user management and enrollment operations.
"""

import uuid

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateResourceError, ResourceNotFoundError, BusinessRuleViolationError
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, EnrollmentCreate

# ---------------------------------------------------------------------------
# Password hashing context (bcrypt)
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt. Never store plain passwords."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# User Creation
# ---------------------------------------------------------------------------

async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """
    Creates a new user with a hashed password.

    Raises:
        DuplicateResourceError: If the email is already registered.
    """
    # Hash the password before storage — NEVER store plaintext
    hashed = hash_password(user_data.password)

    new_user = User(
        email=user_data.email,
        password_hash=hashed,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        department_id=user_data.department_id,
    )

    db.add(new_user)
    try:
        await db.flush()
    except IntegrityError:
        raise DuplicateResourceError(
            f"A user with email '{user_data.email}' already exists."
        )

    return new_user


# ---------------------------------------------------------------------------
# Course Listing
# ---------------------------------------------------------------------------

async def list_courses(db: AsyncSession, active_only: bool = True) -> list[Course]:
    """Returns all courses, optionally filtered to active ones only."""
    query = select(Course)
    if active_only:
        query = query.where(Course.is_active == True)  # noqa: E712
    query = query.order_by(Course.year.desc(), Course.semester, Course.code)
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Student Enrollment
# ---------------------------------------------------------------------------

async def enroll_student(db: AsyncSession, data: EnrollmentCreate) -> Enrollment:
    """
    Enrolls a student in a course.

    Validates:
    - Student exists and has the 'student' role.
    - Course exists and is active.
    - Student is not already enrolled (UNIQUE constraint).

    Raises:
        ResourceNotFoundError:     If student or course not found.
        BusinessRuleViolationError: If user is not a student or course is inactive.
        DuplicateResourceError:    If already enrolled.
    """
    # Validate student
    student = await db.get(User, data.student_id)
    if student is None:
        raise ResourceNotFoundError("Student", str(data.student_id))
    if student.role != UserRole.student:
        raise BusinessRuleViolationError(
            f"User '{data.student_id}' has role '{student.role}' — only students can be enrolled."
        )

    # Validate course
    course = await db.get(Course, data.course_id)
    if course is None:
        raise ResourceNotFoundError("Course", str(data.course_id))
    if not course.is_active:
        raise BusinessRuleViolationError(
            f"Course '{course.code}' is not active and cannot accept enrollments."
        )

    # Check for duplicate enrollment
    existing_query = select(Enrollment).where(
        Enrollment.student_id == data.student_id,
        Enrollment.course_id == data.course_id,
    )
    existing = (await db.execute(existing_query)).scalar_one_or_none()
    if existing:
        raise DuplicateResourceError(
            f"Student '{data.student_id}' is already enrolled in course '{course.code}'."
        )

    enrollment = Enrollment(
        student_id=data.student_id,
        course_id=data.course_id,
    )
    db.add(enrollment)

    try:
        await db.flush()
    except IntegrityError:
        # Race condition safety net
        raise DuplicateResourceError(
            f"Student is already enrolled in this course (concurrent request)."
        )

    return enrollment
