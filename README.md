# Ethereal Attendance System

A full-stack college attendance management platform with JWT authentication, role-based dashboards, and a student bunk calculator.

**Stack:** FastAPI · PostgreSQL · React 18 · TypeScript · TailwindCSS · Docker

---

## Features

| Role | Capabilities |
|---|---|
| **Admin** | View all courses and student reports across the system |
| **Teacher** | Take attendance, export date-range CSV reports per course |
| **Student** | View attendance per course, bunk calculator (safe vs. critical) |

- JWT-based authentication with role-based access control
- Bulk attendance submission with upsert (re-submitting a day updates, not duplicates)
- Per-student attendance report with present/absent/late breakdown and percentage
- Date-range CSV export for course attendance
- Avatar upload and profile management
- 3NF PostgreSQL schema with async SQLAlchemy 2.0

---

## Quickstart with Docker

> Requires [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd projects
```

### 2. Start all services

```bash
docker compose up --build
```

This starts three containers:
- `db` — PostgreSQL 15 on port `5432`
- `backend` — FastAPI on port `8000`
- `frontend` — React (nginx) on port `80`

> **First-run note:** If the backend exits immediately on first boot, Postgres may not have finished initializing. Run `docker compose up` again — it will succeed on the second attempt.

### 3. Seed demo data

In a second terminal, run the seed script to populate the database with realistic demo data (50 students, 10 courses, 30 days of attendance history):

```bash
docker compose exec backend python seed_db.py
```

### 4. Open the app

```
http://localhost
```

---

## Demo Accounts

All demo accounts use the password: **`password123`**

| Role | Email |
|---|---|
| Admin | `admin@college.edu` |
| Teacher (Physics) | `alice@college.edu` |
| Teacher (Mathematics) | `bob@college.edu` |
| Teacher (Chemistry) | `carol@college.edu` |
| Student | `student01@college.edu` … `student50@college.edu` |

---

## API Documentation

The FastAPI backend auto-generates interactive API docs:

| URL | Interface |
|---|---|
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |

---

## Project Structure

```
projects/
├── docker-compose.yml
├── attendance-management-system/     # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # App entrypoint, lifespan, middleware
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings (env vars)
│   │   │   ├── database.py           # Async engine + session factory
│   │   │   └── security.py           # JWT creation/decoding, auth dependencies
│   │   ├── models/                   # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/                  # Pydantic v2 request/response models
│   │   ├── services/                 # Business logic layer
│   │   └── routers/                  # API route handlers
│   ├── sql/schema.sql                # Raw PostgreSQL DDL
│   ├── seed_db.py                    # Demo data seeder
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
└── attendance-frontend/              # React + TypeScript frontend
    ├── src/
    │   ├── api/client.ts             # Fetch wrapper with JWT injection
    │   ├── context/AuthContext.tsx   # Global auth state
    │   ├── pages/                    # LoginPage, TeacherDashboard, StudentDashboard
    │   └── components/               # AttendanceEntry, StudentReport, CourseExport, …
    ├── nginx.conf
    ├── vite.config.ts
    └── Dockerfile
```

---

## Running Locally Without Docker

### Backend

**Requirements:** Python 3.11+, PostgreSQL 14+

```bash
cd attendance-management-system

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL to your local Postgres instance

# Create the database
psql -U postgres -c "CREATE DATABASE attendance_db;"

# Start the server (auto-creates tables on startup)
uvicorn app.main:app --reload --port 8000

# Seed demo data (optional, in a second terminal)
python seed_db.py
```

### Frontend

**Requirements:** Node.js 18+

```bash
cd attendance-frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173`. It calls the backend at `http://localhost:8000`.

---

## Environment Variables

Copy `attendance-management-system/.env.example` to `.env` and adjust:

| Variable | Default (dev) | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@db:5432/attendance_db` | Async PostgreSQL connection string |
| `SECRET_KEY` | `change-me-in-production` | JWT signing secret — **change this in any real deployment** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `DEBUG` | `True` | FastAPI debug mode |

---

## Database Schema (3NF)

| Table | Purpose |
|---|---|
| `departments` | College departments |
| `users` | All users: admin, teacher, student |
| `courses` | Course offerings per semester |
| `enrollments` | Junction: student ↔ course (prevents duplicates) |
| `attendance_records` | One row per student per class date |

Key constraints: unique enrollment per student/course, unique attendance per enrollment/date, cascade deletes, bcrypt-hashed passwords.

---

## License

MIT
