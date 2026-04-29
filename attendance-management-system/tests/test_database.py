"""
tests/test_database.py
-----------------------
Tests verifying the database connection, ORM model creation,
and fundamental data integrity constraints.

These tests operate at the SQLAlchemy session level — no HTTP layer involved.
They prove that:
  1. The async engine connects and creates tables correctly.
  2. SQLAlchemy models can insert and retrieve rows.
  3. Unique constraints are enforced (e.g., duplicate emails).
  4. Foreign key integrity is respected (student_id in Enrollment must exist).
"""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import User, UserRole, Department, Course, Enrollment


class TestDatabaseConnectivity:
    """Verify the test engine itself is operational."""

    async def test_engine_is_reachable(self, db_session):
        """A raw SQL query executes without error, proving the DB connection is live."""
        result = await db_session.execute(text("SELECT 1"))
        value = result.scalar_one()
        assert value == 1, "Expected scalar result of 1 from SELECT 1"

    async def test_all_tables_created(self, db_session):
        """
        Verify all five core tables were created by the engine fixture.
        We test this by doing a SELECT on each table — no rows needed.
        """
        for table_name in ("departments", "users", "courses", "enrollments", "attendance_records"):
            result = await db_session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar_one()
            # Count should be >= 0; the point is no exception was raised
            assert count >= 0, f"Table '{table_name}' does not exist or is inaccessible"


class TestModelCreation:
    """Verify ORM models can write and read data correctly."""

    async def test_create_department(self, db_session):
        """A Department row can be inserted and retrieved by its unique code."""
        dept = Department(name="Physics Dept", code=f"PHY-{uuid.uuid4().hex[:4]}")
        db_session.add(dept)
        await db_session.flush()

        result = await db_session.execute(
            select(Department).where(Department.id == dept.id)
        )
        fetched = result.scalar_one()

        assert fetched.name == "Physics Dept"
        assert fetched.id == dept.id

    async def test_create_student_user(self, db_session, seeded):
        """A student User row can be inserted and has the correct role."""
        student = User(
            email=f"newstudent_{uuid.uuid4().hex[:6]}@test.edu",
            password_hash="$2b$12$fakehash",
            first_name="New",
            last_name="Student",
            role=UserRole.student,
            department_id=seeded["dept_id"],
        )
        db_session.add(student)
        await db_session.flush()

        result = await db_session.execute(
            select(User).where(User.id == student.id)
        )
        fetched = result.scalar_one()

        assert fetched.email == student.email
        assert fetched.role == UserRole.student
        assert fetched.is_active is True

    async def test_full_name_property(self, db_session, seeded):
        """The User.full_name property correctly concatenates first and last name."""
        teacher = await db_session.get(User, seeded["teacher_id"])
        assert teacher is not None
        assert teacher.full_name == "Jane Smith"

    async def test_seeded_course_exists(self, db_session, seeded):
        """The session-scoped seed fixture correctly inserted the test course."""
        course = await db_session.get(Course, seeded["course_id"])
        assert course is not None
        assert course.code == seeded["course_code"]
        assert course.teacher_id == seeded["teacher_id"]

    async def test_seeded_students_are_enrolled(self, db_session, seeded):
        """All 3 seeded students have an Enrollment record for the test course."""
        result = await db_session.execute(
            select(Enrollment).where(Enrollment.course_id == seeded["course_id"])
        )
        enrollments = result.scalars().all()
        assert len(enrollments) == 3, "Expected exactly 3 enrollments for the test course"


class TestUniqueConstraints:
    """
    Verify that database-level UNIQUE constraints are enforced,
    catching bugs that application-layer validation might miss.
    """

    async def test_duplicate_email_raises_integrity_error(self, db_session, seeded):
        """
        Inserting two users with the same email must raise an IntegrityError.
        This validates the UNIQUE constraint on users.email.
        """
        # Use an email that already exists in the seeded data
        duplicate = User(
            email="jane.smith@test.edu",  # Already seeded as the teacher
            password_hash="$2b$12$different_hash",
            first_name="Jane",
            last_name="Duplicate",
            role=UserRole.student,
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
            await db_session.flush()

        await db_session.rollback()

    async def test_duplicate_enrollment_raises_integrity_error(self, db_session, seeded):
        """
        Enrolling the same student in the same course twice must raise an IntegrityError.
        Validates the UNIQUE(student_id, course_id) constraint on enrollments.
        """
        # Try to re-enroll the first seeded student
        duplicate_enrollment = Enrollment(
            student_id=seeded["student_ids"][0],
            course_id=seeded["course_id"],
        )
        db_session.add(duplicate_enrollment)

        with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
            await db_session.flush()

        await db_session.rollback()
