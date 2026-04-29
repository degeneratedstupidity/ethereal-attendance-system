"""
seed_db.py
----------
Completely reseeds the database with realistic data for development/demo:

  - 3 Departments:  Computer Science, Mathematics, Physics
  - 3 Teachers:     one per department  (password: password123)
  - 1 Admin:        admin@college.edu   (password: password123)
  - 10 Courses:     mix of departments, semesters, credit hours
  - 50 Students:    spread across departments  (password: password123)
  - Enrollments:    each student in 3-5 random courses
  - Attendance:     30 past weekdays per course with realistic rates
                    ~70% of students safe (80-90%), ~30% critical (60-70%)
                    — designed to exercise the bunk calculator

Run from the backend directory:
    python seed_db.py
"""

import asyncio
import os
import random
from datetime import date, timedelta

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/attendance_db",
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_pw(plain: str) -> str:
    return pwd_context.hash(plain)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

DEPARTMENTS = [
    {"name": "Physics",          "code": "PHYS"},
    {"name": "Mathematics",      "code": "MATH"},
    {"name": "Chemistry",        "code": "CHEM"},
    {"name": "Biology",          "code": "BIO"},
]

TEACHERS = [
    {"email": "alice@college.edu",  "first": "Alice", "last": "Johnson", "dept": "PHYS"},
    {"email": "bob@college.edu",    "first": "Bob",   "last": "Williams","dept": "MATH"},
    {"email": "carol@college.edu",  "first": "Carol", "last": "Davis",   "dept": "CHEM"},
    {"email": "dave@college.edu",   "first": "Dave",  "last": "Miller",  "dept": "BIO"},
]

COURSES = [
    {"name": "Introductory Physics", "code": "PHYS101", "credits": 4, "dept": "PHYS", "semester": "Fall", "year": 2025, "teacher": "alice@college.edu"},
    {"name": "Calculus I",           "code": "MATH101", "credits": 4, "dept": "MATH", "semester": "Fall", "year": 2025, "teacher": "bob@college.edu"},
    {"name": "Organic Chemistry",    "code": "CHEM101", "credits": 4, "dept": "CHEM", "semester": "Fall", "year": 2025, "teacher": "carol@college.edu"},
    {"name": "General Biology",      "code": "BIO101",  "credits": 4, "dept": "BIO",  "semester": "Fall", "year": 2025, "teacher": "dave@college.edu"},
]

FIRST_NAMES = [
    "Aiden", "Bella", "Carlos", "Diana", "Ethan", "Fiona", "George", "Hannah",
    "Ivan", "Julia", "Kevin", "Laura", "Miguel", "Nadia", "Oscar", "Priya",
    "Quinn", "Rachel", "Samuel", "Tanya", "Uma", "Victor", "Wendy", "Xavier",
    "Yara", "Zach", "Amara", "Benjamin", "Chloe", "Daniel", "Elena", "Felix",
    "Grace", "Hassan", "Iris", "James", "Kira", "Leon", "Maya", "Noah",
    "Olivia", "Pablo", "Quinn", "Rosa", "Stefan", "Tara", "Umar", "Violet",
    "William", "Xena",
]

LAST_NAMES = [
    "Adams", "Baker", "Chen", "Davis", "Evans", "Foster", "Garcia", "Hall",
    "Ibrahim", "Jones", "Kim", "Lopez", "Miller", "Nguyen", "O'Brien", "Patel",
    "Quinn", "Rodriguez", "Smith", "Taylor", "Usman", "Vega", "Wang", "Xavier",
    "Young", "Zhang", "Anders", "Brown", "Clark", "Dixon", "Ellis", "Flynn",
    "Grant", "Harris", "Ishida", "Jensen", "Kapoor", "Lewis", "Moore", "Nash",
    "Okafor", "Park", "Qureshi", "Reed", "Santos", "Thomas", "Upton", "Vargas",
    "White", "Yamamoto",
]


def get_past_weekdays(n: int) -> list[date]:
    """Return the n most recent past weekdays (Mon–Fri), not including today."""
    days = []
    d = date.today() - timedelta(days=1)
    while len(days) < n:
        if d.weekday() < 5:  # 0=Mon … 4=Fri
            days.append(d)
        d -= timedelta(days=1)
    return days


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

async def seed():
    from app.models.department import Department
    from app.models.user import User, UserRole
    from app.models.course import Course
    from app.models.enrollment import Enrollment
    from app.models.attendance import AttendanceRecord, AttendanceStatus

    async with engine.begin() as conn:
        # --- Add profile_picture_url if the column doesn't exist yet ---
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(500)"
        ))

        # --- Wipe existing data in FK-safe order ---
        print("🗑  Clearing existing data...")
        await conn.execute(text("DELETE FROM attendance_records"))
        await conn.execute(text("DELETE FROM enrollments"))
        await conn.execute(text("DELETE FROM courses"))
        await conn.execute(text("DELETE FROM users"))
        await conn.execute(text("DELETE FROM departments"))

    hashed_pw = hash_pw("password123")
    class_days = get_past_weekdays(30)

    async with AsyncSessionLocal() as db:
        print("🏢  Creating departments...")
        dept_map: dict[str, Department] = {}
        for d in DEPARTMENTS:
            dept = Department(name=d["name"], code=d["code"])
            db.add(dept)
            await db.flush()
            dept_map[d["code"]] = dept

        print("👤  Creating admin account...")
        admin = User(
            email="admin@college.edu",
            password_hash=hashed_pw,
            first_name="System",
            last_name="Admin",
            role=UserRole.admin,
            department_id=dept_map["PHYS"].id,
        )
        db.add(admin)
        await db.flush()

        print("🧑‍🏫  Creating teachers...")
        teacher_map: dict[str, User] = {}
        for t in TEACHERS:
            teacher = User(
                email=t["email"],
                password_hash=hashed_pw,
                first_name=t["first"],
                last_name=t["last"],
                role=UserRole.teacher,
                department_id=dept_map[t["dept"]].id,
            )
            db.add(teacher)
            await db.flush()
            teacher_map[t["email"]] = teacher

        print("📚  Creating courses...")
        course_list: list[Course] = []
        for c in COURSES:
            course = Course(
                name=c["name"],
                code=c["code"],
                credit_hours=c["credits"],
                department_id=dept_map[c["dept"]].id,
                teacher_id=teacher_map[c["teacher"]].id,
                semester=c["semester"],
                year=c["year"],
                is_active=True,
            )
            db.add(course)
            await db.flush()
            course_list.append(course)

        print("🎓  Creating 50 students...")
        students: list[User] = []
        dept_codes = list(dept_map.keys())
        for i in range(50):
            student = User(
                email=f"student{i + 1:02d}@college.edu",
                password_hash=hashed_pw,
                first_name=FIRST_NAMES[i % len(FIRST_NAMES)],
                last_name=LAST_NAMES[i % len(LAST_NAMES)],
                role=UserRole.student,
                department_id=dept_map[dept_codes[i % 4]].id,
            )
            db.add(student)
            await db.flush()
            students.append(student)

        print("📋  Enrolling students (3–5 courses each)...")
        # Track which (student, course) pairs are enrolled for attendance generation
        enrollment_pairs: list[tuple[User, Course, Enrollment]] = []

        for student in students:
            num_courses = min(random.randint(3, 5), len(course_list))
            chosen_courses = random.sample(course_list, num_courses)
            for course in chosen_courses:
                enr = Enrollment(student_id=student.id, course_id=course.id)
                db.add(enr)
                await db.flush()
                enrollment_pairs.append((student, course, enr))

        print("✅  Generating 30 days of attendance records...")
        records_created = 0
        for student, course, enr in enrollment_pairs:
            # Decide attendance rate: ~30% of students are "critical" (<75%)
            if random.random() < 0.30:
                present_rate = random.uniform(0.60, 0.73)   # critical zone
            else:
                present_rate = random.uniform(0.80, 0.95)   # safe zone

            for day in class_days:
                roll = random.random()
                if roll < present_rate:
                    # Present, with a small chance of 'late'
                    status = AttendanceStatus.late if random.random() < 0.10 else AttendanceStatus.present
                else:
                    status = AttendanceStatus.absent

                # Find the teacher for this course
                recorder_id = course.teacher_id

                record = AttendanceRecord(
                    enrollment_id=enr.id,
                    attendance_date=day,
                    status=status,
                    recorded_by=recorder_id,
                )
                db.add(record)
                records_created += 1

        await db.commit()

    print()
    print("=" * 60)
    print("✅  Seeding complete!")
    print(f"   Departments : {len(DEPARTMENTS)}")
    print(f"   Teachers    : {len(TEACHERS)}  (+ 1 admin)")
    print(f"   Courses     : {len(COURSES)}")
    print(f"   Students    : 50")
    print(f"   Enrollments : {len(enrollment_pairs)}")
    print(f"   Attendance  : {records_created} records ({len(class_days)} days per enrollment)")
    print()
    print("Login credentials (all passwords: password123):")
    print("  Admin   → admin@college.edu")
    print("  Teacher → alice@college.edu  (PHYS courses)")
    print("  Teacher → bob@college.edu    (MATH courses)")
    print("  Teacher → carol@college.edu  (CHEM courses)")
    print("  Teacher → dave@college.edu   (BIO courses)")
    print("  Student → student01@college.edu … student50@college.edu")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
