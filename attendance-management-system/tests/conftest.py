"""
tests/conftest.py
-----------------
Shared pytest fixtures for the entire test suite.

Strategy:
- Use SQLite (in-memory) as the test database via aiosqlite.
  This avoids any external dependency on a running PostgreSQL instance,
  making tests fast, hermetic, and CI-friendly.
- A single in-memory DB is created for the session; SQLAlchemy drops and
  recreates all tables between test modules via module-scoped fixtures.
- The FastAPI `get_db` dependency is overridden to yield a test session that
  shares its connection with the seeded data — critical for ensuring the
  service layer can see the rows seeded in the fixture.
- All data created in each test is rolled back after the test completes.
"""

import uuid
from datetime import date, timedelta
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import get_db
from app.main import app
from app.models import (
    Base,
    AttendanceRecord,
    AttendanceStatus,
    Course,
    Department,
    Enrollment,
    User,
    UserRole,
)

# ---------------------------------------------------------------------------
# Test database: SQLite in-memory, reset per test module
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Creates a single async SQLite in-memory engine for the entire test session.
    All tables are created once and the engine is disposed at the end.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        # Required for SQLite to allow multi-threaded access in async contexts.
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True to see all SQL in test output
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def TestSessionFactory(test_engine):
    """Session factory bound to the test engine, reused across the session."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@pytest_asyncio.fixture(scope="session")
async def seeded(TestSessionFactory) -> dict:
    """
    Seeds the in-memory test database ONCE for the entire session.

    Creates:
      - 1 Department
      - 1 Teacher (admin/recorder)
      - 1 Course linked to the teacher
      - 3 Students enrolled in the course
      - 3 days of attendance (today-1, today-2, today-3) with mixed statuses

    Returns a dict of all created entity IDs for use in tests.
    """
    async with TestSessionFactory() as session:
        # --- Department ---
        dept = Department(name="Test Computer Science", code="TCS")
        session.add(dept)
        await session.flush()

        # --- Teacher (also serves as recorder for attendance) ---
        teacher = User(
            email="jane.smith@test.edu",
            password_hash="$2b$12$testhashvalue",
            first_name="Jane",
            last_name="Smith",
            role=UserRole.teacher,
            department_id=dept.id,
        )
        session.add(teacher)
        await session.flush()

        # --- Course ---
        course = Course(
            name="Algorithms and Data Structures",
            code="CS-TEST-301",
            credit_hours=3,
            department_id=dept.id,
            teacher_id=teacher.id,
            semester="Spring",
            year=2026,
        )
        session.add(course)
        await session.flush()

        # --- 3 Students ---
        students = []
        student_info = [
            ("alice", "Alice", "Anderson"),
            ("bob",   "Bob",   "Baker"),
            ("carol", "Carol", "Chen"),
        ]
        for slug, first, last in student_info:
            s = User(
                email=f"{slug}@test.edu",
                password_hash="$2b$12$testhashvalue",
                first_name=first,
                last_name=last,
                role=UserRole.student,
                department_id=dept.id,
            )
            session.add(s)
            students.append(s)
        await session.flush()

        # --- Enroll all students ---
        enrollments = []
        for student in students:
            enr = Enrollment(student_id=student.id, course_id=course.id)
            session.add(enr)
            enrollments.append(enr)
        await session.flush()

        # --- Attendance: 3 past class days ---
        statuses_by_student = [
            # alice: 3 present — should be 100%
            [AttendanceStatus.present, AttendanceStatus.present, AttendanceStatus.present],
            # bob: 2 present, 1 absent — ~66.7%
            [AttendanceStatus.present, AttendanceStatus.absent,  AttendanceStatus.present],
            # carol: 1 present, 1 late, 1 absent — 66.7% (late counts as attended)
            [AttendanceStatus.late,    AttendanceStatus.absent,  AttendanceStatus.present],
        ]
        today = date.today()
        for day_offset in range(1, 4):  # Days: today-1, today-2, today-3
            att_date = today - timedelta(days=day_offset)
            for i, enr in enumerate(enrollments):
                rec = AttendanceRecord(
                    enrollment_id=enr.id,
                    attendance_date=att_date,
                    status=statuses_by_student[i][day_offset - 1],
                    recorded_by=teacher.id,
                )
                session.add(rec)

        await session.commit()

    return {
        "dept_id":      dept.id,
        "teacher_id":   teacher.id,
        "course_id":    course.id,
        "course_code":  course.code,
        "student_ids":  [s.id for s in students],
        "enrollment_ids": [e.id for e in enrollments],
    }


@pytest_asyncio.fixture()
async def db_session(TestSessionFactory) -> AsyncGenerator[AsyncSession, None]:
    """
    Yields a fresh database session per test.
    Uses SAVEPOINT (nested transaction) so that changes within a test are
    rolled back cleanly without touching committed seed data.
    """
    async with TestSessionFactory() as session:
        await session.begin_nested()  # Creates a SAVEPOINT
        yield session
        await session.rollback()     # Rolls back to SAVEPOINT after the test


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Yields an httpx AsyncClient wired to the FastAPI app.

    Overrides the `get_db` dependency to inject the test's database session,
    ensuring the API routes see exactly the same DB state as the test setup.
    """
    async def _override_get_db():
        yield db_session  # Same session used by the test — sees seeded data

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
