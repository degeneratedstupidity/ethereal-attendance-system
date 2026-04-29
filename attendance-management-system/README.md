# Attendance Management System

> A production-quality college Attendance Management System built with **PostgreSQL** (3NF schema) and **FastAPI** (async Python).

---

## 🏗️ Architecture Overview

```
attendance-management-system/
├── app/
│   ├── main.py                    # FastAPI app entrypoint (lifespan, routers, middleware)
│   ├── exceptions.py              # Custom domain exceptions + FastAPI handlers
│   ├── core/
│   │   ├── config.py              # Pydantic Settings (env vars)
│   │   └── database.py            # Async engine, session factory, get_db dependency
│   ├── models/                    # SQLAlchemy 2.0 ORM models (mirror DB schema)
│   │   ├── base.py
│   │   ├── department.py
│   │   ├── user.py                # UserRole enum: admin | teacher | student
│   │   ├── course.py
│   │   ├── enrollment.py          # Junction table (student ↔ course)
│   │   └── attendance.py          # Fact table (AttendanceStatus: present|absent|late)
│   ├── schemas/                   # Pydantic v2 request/response models
│   │   ├── attendance.py
│   │   ├── course.py
│   │   └── user.py
│   ├── services/                  # Business logic (keeps routers clean)
│   │   ├── attendance_service.py  # ← Core logic for all 3 required operations
│   │   └── course_service.py      # User creation, enrollment, course listing
│   └── routers/
│       ├── attendance.py          # API endpoints (roster, bulk submit, report)
│       └── users.py               # User + enrollment endpoints
├── sql/
│   └── schema.sql                 # Raw PostgreSQL DDL (standalone, fully annotated)
├── requirements.txt
└── .env.example
```

---

## 🗄️ Database Schema (3NF)

### Tables

| Table | Purpose |
|---|---|
| `departments` | College departments (CS, Math, etc.) |
| `users` | All principals: admin, teacher, student |
| `courses` | Course/subject offerings per semester |
| `enrollments` | Junction: student ↔ course (prevents duplicates) |
| `attendance_records` | Fact table: one row per student per class date |

### Key Integrity Constraints

| Constraint | Location | Effect |
|---|---|---|
| `UNIQUE(student_id, course_id)` | `enrollments` | No double-enrollment |
| `UNIQUE(enrollment_id, attendance_date)` | `attendance_records` | No duplicate attendance per day |
| `FK enrollment_id → enrollments` | `attendance_records` | Only enrolled students get attendance |
| `CHECK credit_hours BETWEEN 1 AND 6` | `courses` | Data sanity |
| `ON DELETE CASCADE` | `enrollments`, `attendance_records` | Clean cascade deletes |

### Why 3NF?

- **1NF**: Atomic attributes only, no repeating groups
- **2NF**: No partial dependencies — `attendance_records.enrollment_id` is a full FK to the junction, not a partial composite key
- **3NF**: No transitive dependencies — `teacher` info lives in `users`, not `courses`; `department` name is in its own table, not duplicated

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+

### 1. Clone & Install
```bash
cd attendance-management-system
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 3. Create the PostgreSQL Database
```bash
psql -U postgres -c "CREATE DATABASE attendance_db;"
```

### 4. Run the Server
```bash
uvicorn app.main:app --reload --port 8000
```

The server auto-creates all tables on first startup.

### 5. Open Interactive API Docs
```
http://localhost:8000/docs   ← Swagger UI
http://localhost:8000/redoc  ← ReDoc
```

---

## 📡 API Endpoints

### Core Attendance Endpoints

#### `GET /api/v1/courses/{course_id}/roster`
Fetch the full class roster for a course.

**Response:**
```json
{
  "course_id": "uuid",
  "course_name": "Data Structures",
  "course_code": "CS301",
  "semester": "Spring",
  "year": 2026,
  "teacher_name": "Dr. Jane Smith",
  "student_count": 3,
  "students": [
    {
      "enrollment_id": "uuid",
      "student_id": "uuid",
      "first_name": "Alice",
      "last_name": "Kumar",
      "email": "alice@college.edu",
      "enrolled_at": "2026-01-10T09:00:00Z"
    }
  ]
}
```

---

#### `POST /api/v1/attendance/bulk?recorded_by={teacher_uuid}`
Submit attendance for an entire class.

**Request Body:**
```json
{
  "course_id": "uuid",
  "attendance_date": "2026-04-24",
  "records": [
    { "student_id": "uuid-1", "status": "present" },
    { "student_id": "uuid-2", "status": "absent",  "remarks": "Medical leave" },
    { "student_id": "uuid-3", "status": "late" }
  ]
}
```

**Response (201):**
```json
{
  "message": "Attendance submitted successfully.",
  "course_id": "uuid",
  "attendance_date": "2026-04-24",
  "records_created": 3,
  "records_updated": 0
}
```

> 💡 **UPSERT behavior**: Re-submitting for the same date updates existing records instead of failing.

---

#### `GET /api/v1/students/{student_id}/attendance?course_id={optional}`
Get a student's attendance report.

**Response:**
```json
{
  "student_id": "uuid",
  "student_name": "Alice Kumar",
  "courses": [
    {
      "course_id": "uuid",
      "course_name": "Data Structures",
      "course_code": "CS301",
      "total_classes": 20,
      "present_count": 16,
      "absent_count": 2,
      "late_count": 2,
      "attendance_percentage": 90.0
    }
  ],
  "overall_percentage": 90.0
}
```

> 📌 **Policy**: `late` counts as attended in the percentage calculation.

---

### Supporting Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/users/` | Create a user (password is bcrypt-hashed) |
| `POST` | `/api/v1/enrollments/` | Enroll student in course |
| `GET` | `/api/v1/courses/` | List all active courses |
| `GET` | `/health` | Health check |

---

## ⚠️ Error Handling

All errors return structured JSON responses:

| HTTP Code | Error Key | Trigger |
|---|---|---|
| `404` | `NOT_FOUND` | Course/student UUID doesn't exist |
| `409` | `CONFLICT` | Duplicate enrollment or attendance record |
| `422` | `BUSINESS_RULE_VIOLATION` | Student not enrolled, future date, etc. |
| `409` | `DATABASE_CONSTRAINT_VIOLATION` | DB-level unique constraint hit (safety net) |

Example error response:
```json
{
  "error": "CONFLICT",
  "message": "Student 'uuid' is already enrolled in course 'CS301'."
}
```

---

## 🔐 Security Notes

- Passwords are **never stored in plaintext** — bcrypt via `passlib` is used.
- In production: replace the `recorded_by` query param with **JWT token extraction**.
- Restrict `CORS allow_origins` to your frontend domain.
- Use **Alembic** for schema migrations instead of `create_all` in production.

---

## 🧪 Testing Flow (via Swagger UI)

1. `POST /api/v1/users/` — Create a teacher and 3 students
2. `POST /api/v1/users/` — Create a course (or seed the DB)
3. `POST /api/v1/enrollments/` — Enroll each student
4. `GET /api/v1/courses/{course_id}/roster` — Verify roster
5. `POST /api/v1/attendance/bulk` — Submit attendance
6. `GET /api/v1/students/{student_id}/attendance` — View report
