# Attendify — Attendance Management System

## Overview

A full-stack attendance management platform for colleges, built with **FastAPI + PostgreSQL** on the backend and **React + TailwindCSS** on the frontend. The system supports three user roles (admin, teacher, student) with JWT-based authentication and a student-facing bunk calculator.

---

## Repository Layout

```
projects/
├── attendance-management-system/   # FastAPI backend
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic settings (env vars / .env)
│   │   │   ├── database.py         # Async SQLAlchemy engine + session
│   │   │   └── security.py         # JWT, bcrypt, FastAPI dependencies
│   │   ├── models/
│   │   │   ├── user.py             # User + UserRole enum
│   │   │   ├── course.py           # Course
│   │   │   ├── department.py       # Department
│   │   │   ├── enrollment.py       # Enrollment (student ↔ course junction)
│   │   │   └── attendance.py       # AttendanceRecord + AttendanceStatus enum
│   │   ├── schemas/
│   │   │   ├── user.py             # UserCreate, UserOut, LoginRequest, TokenResponse, ChangePasswordRequest
│   │   │   ├── attendance.py       # BulkAttendanceRequest/Response, StudentAttendanceReport, BunkCalculatorResult
│   │   │   └── course.py           # CourseRosterResponse, RosterStudentEntry
│   │   ├── routers/
│   │   │   ├── auth.py             # POST /auth/login, GET /auth/me, POST /auth/change-password
│   │   │   ├── attendance.py       # Roster, bulk submit, student report, bunk calculator, CSV export
│   │   │   ├── users.py            # User creation (admin), enrollment, course listing
│   │   │   └── profile.py          # Avatar upload, profile GET
│   │   ├── services/
│   │   │   ├── attendance_service.py  # Business logic for all attendance operations + bunk calculator
│   │   │   └── course_service.py      # User creation, enrollment, course listing
│   │   ├── exceptions.py           # Custom exception types + FastAPI handlers
│   │   └── main.py                 # App factory, middleware, router registration, static files
│   ├── static/
│   │   └── avatars/                # Uploaded profile pictures (served at /static/avatars/<file>)
│   ├── seed_db.py                  # Full database seeder (4 depts, 4 teachers, 50 students, 4 courses)
│   ├── requirements.txt
│   └── venv/                       # Python virtual environment (uv-managed)
│
└── attendance-frontend/            # React frontend
    └── src/
        ├── api/
        │   └── client.ts           # API_BASE constant + authFetch() wrapper
        ├── context/
        │   └── AuthContext.tsx     # AuthProvider, useAuth hook, login/logout/updateUser
        ├── components/
        │   ├── Sidebar.tsx         # Teacher sidebar + cn() utility export
        │   ├── ProtectedRoute.tsx  # Role-based route guard
        │   ├── AvatarUpload.tsx    # Circular avatar preview + upload
        │   ├── AttendanceEntry.tsx # Teacher mark-attendance form
        │   └── StudentReport.tsx   # Teacher-facing student attendance report
        ├── pages/
            ├── LoginPage.tsx       # Glassmorphism login UI + confetti on login
            ├── TeacherDashboard.tsx# Three-tab teacher dashboard (Attendance / Reports / Profile)
            └── StudentDashboard.tsx# Student dashboard with bunk calculator widget
    └── utils/
        └── confetti.ts             # Pure-JS confetti animation (no npm dependency)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend language | Python 3.12 |
| API framework | FastAPI |
| ORM | SQLAlchemy 2.0 async |
| Database | PostgreSQL (asyncpg driver) |
| Validation | Pydantic v2 |
| Auth | python-jose (JWT HS256) + passlib bcrypt |
| File uploads | python-multipart |
| Package manager | uv |
| Frontend framework | React 18 + TypeScript |
| Styling | TailwindCSS |
| Routing | react-router-dom v6 |
| Icons | lucide-react |
| Build tool | Vite |

---

## Database Schema

```
departments
  id (UUID PK)
  name, code

users
  id (UUID PK)
  email (UNIQUE)
  password_hash          -- bcrypt, never plaintext
  first_name, last_name
  role                   -- ENUM: admin | teacher | student
  department_id (FK → departments)
  is_active
  profile_picture_url    -- nullable, path like /static/avatars/<uuid>.jpg
  created_at, updated_at

courses
  id (UUID PK)
  name, code (UNIQUE)
  credit_hours, semester, year
  department_id (FK → departments)
  teacher_id (FK → users, nullable)
  is_active

enrollments
  id (UUID PK)
  student_id (FK → users)
  course_id  (FK → courses)
  enrolled_at
  UNIQUE (student_id, course_id)

attendance_records
  id (UUID PK)
  enrollment_id (FK → enrollments)
  attendance_date (DATE)
  status          -- ENUM: present | absent | late
  remarks         -- nullable text
  recorded_at, recorded_by (FK → users)
  UNIQUE (enrollment_id, attendance_date)
```

---

## API Reference

All routes are prefixed `/api/v1`. Protected routes require `Authorization: Bearer <JWT>`.

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | Public | Login with email + password. Returns JWT + user info. |
| GET | `/auth/me` | Any | Returns the authenticated user's profile. |
| POST | `/auth/change-password` | Any | Change own password (requires current password). |

**Login request:**
```json
{ "email": "alice@college.edu", "password": "password123" }
```

**Login response:**
```json
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "user_id": "<uuid>",
  "role": "teacher",
  "full_name": "Alice Johnson",
  "email": "alice@college.edu",
  "profile_picture_url": null
}
```

JWT payload includes `sub` (user UUID) and `role` — both are embedded at token creation.

---

### Attendance

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/courses/{id}/roster` | Teacher (own course) | Returns enrolled students for a course. |
| POST | `/attendance/bulk` | Teacher (own course) | Submit / upsert attendance for a full class. Recorder taken from JWT — no query param. |
| GET | `/students/{id}/attendance` | Student (own) / Teacher+Admin (any) | Per-course attendance breakdown + overall %. |
| GET | `/students/{id}/bunk-calculator` | Student (own) / Teacher+Admin (any) | Bunk calculator result. |
| GET | `/students/{id}/attendance/export` | Student (own) / Teacher+Admin (any) | Download attendance as CSV. |

**Course ownership rule:** Teachers can only access the roster and submit attendance for courses where `course.teacher_id == current_user.id`. Admins bypass this check.

**Bulk attendance request:**
```json
{
  "course_id": "<uuid>",
  "attendance_date": "2025-04-24",
  "records": [
    { "student_id": "<uuid>", "status": "present" },
    { "student_id": "<uuid>", "status": "absent", "remarks": "medical" }
  ]
}
```

**Bunk calculator response:**
```json
{
  "student_id": "<uuid>",
  "student_name": "Aiden Adams",
  "overall_percentage": 87.78,
  "total_classes": 90,
  "attended_classes": 79,
  "threshold": 75.0,
  "status": "safe",
  "safe_to_bunk": 15,
  "must_attend": null,
  "message": "You're at 87.8% — safe! You can miss up to 15 more classes and still stay above 75%."
}
```

**Bunk calculator formulas** (threshold P = 0.75, attended A, total T):
- If `A/T ≥ P`: `safe_to_bunk = floor((A − P·T) / P)`
- If `A/T < P`: `must_attend = ceil((P·T − A) / (1 − P))`

---

### Users & Enrollment

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/users/` | Admin only | Create a new user (any role). Password hashed server-side. |
| POST | `/enrollments/` | Admin only | Enroll a student in a course. |
| GET | `/courses/` | Teacher / Admin | List all active courses. |
| GET | `/teachers/me/courses` | Teacher / Admin | List courses taught by the authenticated teacher. |

---

### Profile & Avatars

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/profile/me` | Any | Full profile of current user including avatar URL. |
| POST | `/profile/avatar` | Any | Upload profile picture (JPEG/PNG/GIF/WebP, max 5 MB). |

Uploaded avatars are saved to `static/avatars/<user_id>.<ext>` and served at `/static/avatars/<file>`. The full URL to prepend is `http://127.0.0.1:8000`.

---

## Security Design

- **JWT:** HS256, signed with `SECRET_KEY` from settings. Expires in 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`). Payload contains `sub` (user UUID) and `role`.
- **Passwords:** bcrypt via passlib. Plain text is never stored or logged.
- **Role guards (FastAPI dependencies):**
  - `get_current_user` — any authenticated user
  - `get_current_teacher` — role must be `teacher` or `admin`
  - `get_current_admin` — role must be `admin`
- **Course ownership check:** On roster fetch and bulk attendance submit, the service verifies `course.teacher_id == current_user.id` (admins bypass).
- **Student data isolation:** Students can only query their own attendance and bunk calculator; attempting another student's ID returns 403.

---

## Frontend Architecture

### Auth flow

1. User visits `/` → `RootRedirect` checks `AuthContext` → redirects to `/login` if not authenticated.
2. `LoginPage` calls `POST /auth/login`, stores `token` + `user` in `localStorage` and React state.
3. On reload, `AuthContext` hydrates from `localStorage` automatically.
4. `ProtectedRoute` wraps each dashboard and enforces both authentication and role. Wrong role redirects to the correct dashboard.
5. `authFetch(path, options)` in `src/api/client.ts` auto-attaches the Bearer token to every request. It skips `Content-Type: application/json` when the body is `FormData` (for avatar upload).

### Routing

```
/login          → LoginPage (public)
/teacher/*      → TeacherDashboard (requires role: teacher | admin)
/student        → StudentDashboard (requires role: student)
/               → RootRedirect (to /login, /teacher, or /student based on auth state)
*               → redirects to /
```

### Teacher Dashboard tabs

- **Mark Attendance** — course picker (own courses only via `/teachers/me/courses`), date picker, student roster, status buttons (Present / Absent / Late), "Mark All Present" one-click button, submit.
- **View Reports** — pick course → pick student → view attendance breakdown with progress bars + CSV export button.
- **My Profile** — avatar upload (click circle to open file picker), change password form.

### Student Dashboard

- Header: avatar, full name, email, overall % badge.
- **Bunk Calculator widget** (hero): animated SVG circular progress ring showing current %, large number showing classes safe to skip or classes to attend to recover, attendance stats (attended / missed / total).
- Per-course breakdown: progress bars colored green/amber/red, P/L/A counts, below-75% warning badge.
- Top bar: Export CSV button, Sign Out.

### Key frontend files

| File | Purpose |
|---|---|
| `src/api/client.ts` | `API_BASE` constant, `authFetch()` — Bearer token auto-attach |
| `src/context/AuthContext.tsx` | `AuthProvider`, `useAuth()`, `login()`, `logout()`, `updateUser()` |
| `src/components/Sidebar.tsx` | Teacher sidebar nav + `cn()` className utility (imported by other components) |
| `src/components/ProtectedRoute.tsx` | Route guard: redirects unauthenticated users and wrong-role users |
| `src/components/AvatarUpload.tsx` | Circular avatar with hover overlay, file input, upload progress |

---

## Running the Project

### Backend

```bash
cd attendance-management-system
source venv/bin/activate
uvicorn app.main:app --reload   # http://localhost:8000
# Swagger UI: http://localhost:8000/docs
```

Install dependencies (if needed):
```bash
uv pip install -r requirements.txt
```

### Frontend

```bash
cd attendance-frontend
npm install
npm run dev   # http://localhost:5173
```

### Seeding the database

```bash
cd attendance-management-system
source venv/bin/activate
python seed_db.py
```

This will **wipe all existing data** and re-seed with:
- **4 departments:** Physics, Mathematics, Chemistry, Biology
- **4 teachers:** one per department (alice, bob, carol, dave)
- **1 admin**, 50 students, 4 courses
- Each student enrolled in 3–4 random courses
- 30 past weekdays of attendance per enrollment (~30% of students in critical <75% zone)

> **Tip:** If `source venv/bin/activate` is lost between terminal sessions, use the full path:
> ```bash
> /home/cb/AntiGravity/projects/attendance-management-system/venv/bin/python seed_db.py
> ```

### Environment variables

Configured via `.env` in the backend root or actual environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5432/attendance_db` | Async PostgreSQL connection string |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — **change in production** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |

---

## Test Credentials

All seeded accounts use the password: **`password123`**

| Role | Email | Subject |
|---|---|---|
| Admin | `admin@college.edu` | All courses |
| Teacher | `alice@college.edu` | Physics (PHYS101) |
| Teacher | `bob@college.edu` | Mathematics (MATH101) |
| Teacher | `carol@college.edu` | Chemistry (CHEM101) |
| Teacher | `dave@college.edu` | Biology (BIO101) |
| Student | `student01@college.edu` … `student50@college.edu` | — |

Students with critically low attendance (for testing bunk calculator "must attend" path): roughly students 06, 14, 22, 30, 38, 45 — varies per seed run due to random generation. Check with:
```bash
# Find critical students
curl -s -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/api/v1/students/<id>/bunk-calculator
```

---

## Implementation Phases

### Phase 1 — JWT Authentication & Role-Based Access

- Created `app/core/security.py`: password hashing, JWT creation/decoding, `get_current_user` / `get_current_teacher` / `get_current_admin` FastAPI dependencies.
- Created `app/routers/auth.py`: login, /me, change-password endpoints.
- Updated `app/schemas/user.py`: added `LoginRequest`, `TokenResponse`, `ChangePasswordRequest`; updated `UserOut` with `profile_picture_url`.
- Updated `app/routers/attendance.py`: JWT guards on all endpoints, course ownership check (`_require_course_access`), removed `recorded_by` query param (now from JWT).
- Updated `app/routers/users.py`: admin guard on user creation and enrollment, added `GET /teachers/me/courses`.
- Updated `app/main.py`: registered auth and profile routers, mounted `StaticFiles` at `/static`.

### Phase 2 — Profile Pictures

- Added `profile_picture_url: Mapped[str | None]` column to `app/models/user.py`.
- Created `app/routers/profile.py`: avatar upload (multipart, MIME-validated, 5 MB max, saved to `static/avatars/`) and profile GET.
- `seed_db.py` handles `ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture_url` for live databases.

### Phase 3 — Bunk Calculator

- Added `BunkCalculatorResult` schema to `app/schemas/attendance.py`.
- Added `calculate_bunk_info()` to `app/services/attendance_service.py` with the two formulas.
- Added `GET /students/{id}/bunk-calculator` and `GET /students/{id}/attendance/export` (CSV) to `app/routers/attendance.py`.

### Phase 4 — Frontend Rebuild

- Installed `react-router-dom`.
- Created `src/api/client.ts`: `authFetch()` wrapper.
- Created `src/context/AuthContext.tsx`: auth state, login/logout, localStorage persistence.
- Rewrote `src/components/Sidebar.tsx`: auth-aware sidebar with user avatar/name footer; exports `cn()` utility.
- Created `src/components/ProtectedRoute.tsx`: redirects unauthenticated/wrong-role users.
- Created `src/components/AvatarUpload.tsx`: circular avatar with hover camera icon, file upload.
- Created `src/pages/LoginPage.tsx`: glassmorphism card, gradient background, role-based redirect.
- Created `src/pages/TeacherDashboard.tsx`: three-tab layout (Mark Attendance / View Reports / My Profile).
- Created `src/pages/StudentDashboard.tsx`: bunk calculator widget with SVG circular progress ring, per-course breakdown.
- Updated `src/components/AttendanceEntry.tsx`: removed `RECORDED_BY_ID`, uses `authFetch`, fetches teacher's own courses, added "Mark All Present" button.
- Updated `src/components/StudentReport.tsx`: uses `authFetch`, fetches teacher's own courses, added CSV export button.
- Updated `src/App.tsx`: `BrowserRouter` + `AuthProvider` + typed routes with `ProtectedRoute`.

### Phase 5 — Heavy Seeding

- Rewrote `seed_db.py`: wipes all tables in FK-safe order, runs `ALTER TABLE` for the new column, seeds 3 departments / 3 teachers / 1 admin / 10 courses / 50 students / ~200 enrollments / 6030 attendance records with realistic attendance distributions.

---

## Known Limitations & Future Work

- **No token refresh:** JWT expires after 60 minutes and the user must log in again. A refresh token flow (httpOnly cookie + `/auth/refresh` endpoint) would fix this.
- **Local file storage:** Avatars are stored on disk. For production, replace with S3 or similar object storage.
- **No Alembic migrations:** Schema changes are handled via `ALTER TABLE` in the seed script and `create_all` on startup. Add Alembic for production use.
- **CORS is open:** `allow_origins=["*"]` is set for development. Restrict to the frontend origin in production.
- **SECRET_KEY is a placeholder:** Must be replaced with a strong random value before any real deployment.
- **No rate limiting on login:** The `/auth/login` endpoint has no brute-force protection. Consider adding `slowapi` or a similar rate limiter.


---

## UI/UX Revamp Session — Implementation Status

### Confirmed Decisions (from user)
- App name: **"Ethereal Paranatellon University"** (replaces "Attendify" / "suupyTulip University")
- Rate limiter on `/auth/login` (slowapi): **explicitly dropped from scope**
- NES dark palette as the primary theme: **confirmed**
- Hamburger drawer for mobile sidebar: **confirmed**
- Date-range course export tab: **confirmed**

---

### ✅ COMPLETED — Backend (all done, no further changes needed)

| File | Notes |
|---|---|
| `app/schemas/attendance.py` | `teacher_name: str \| None = None` on `CourseAttendanceSummary` |
| `app/services/attendance_service.py` | `get_student_attendance` preloads `Course.teacher`; `export_course_attendance_csv()` present |
| `app/routers/attendance.py` | `GET /courses/{course_id}/attendance/export` with `start_date`/`end_date` query params |

---

### ✅ COMPLETED — Frontend infrastructure & full rewrites

| File | What changed |
|---|---|
| `attendance-frontend/tsconfig.json` | **NEW** — was missing entirely; created standard Vite+React+TS config |
| `attendance-frontend/tsconfig.node.json` | **NEW** — was missing; covers `vite.config.ts` |
| `attendance-frontend/index.html` | Title → "Ethereal Paranatellon University" |
| `attendance-frontend/tailwind.config.js` | Added `nes.card: '#1e1e1e'`; `gradientShift` + `fadeSlideUp` keyframes; `animate-gradient` + `animate-fade-slide-up` animations; `pulseGlow` recoloured to blue |
| `attendance-frontend/src/index.css` | `.glass-panel` → dark (`bg-nes-card border border-white/10`); `.animated-gradient` CSS utility added |
| `attendance-frontend/src/App.tsx` | Dropped unused `React` import; wrapped with `ToastProvider` |
| `attendance-frontend/src/context/ToastContext.tsx` | **NEW FILE** — `ToastProvider` + `useToast()` hook; auto-dismiss after 4 s; `success`/`error`/`warning` types; NES-coloured dark toast cards |
| `attendance-frontend/src/pages/LoginPage.tsx` | Renamed; fixed button hover bug (`hover:bg-nes-light0` → `hover:bg-blue-700`); `GraduationCap` gets `animate-bounce-icon`; background → `animated-gradient`; icon box → `animate-pulse-glow` |
| `attendance-frontend/src/components/Sidebar.tsx` | Full rewrite: `bg-nes-dark`; fixed hamburger button top-left on mobile; slide-in overlay drawer + backdrop; active items get `nes-blue` left bar + `bg-nes-blue/15`; role badge (yellow=admin, blue=teacher); icon hover scale/lift via `group-hover` |
| `attendance-frontend/src/pages/TeacherDashboard.tsx` | Dark `ProfileTab` (dark inputs, NES colours); removed `mt-[140px]` hack → `pt-16 md:pt-8`; admin `ShieldCheck` badge in Profile tab |
| `attendance-frontend/src/pages/StudentDashboard.tsx` | Full dark revamp; SVG ring → NES green/red with `drop-shadow` glow; bunk calc dark tinted backgrounds; per-course bars use inline NES hex; teacher name in `nes-yellow`; dropped unused `React` import |
| `attendance-frontend/src/components/StudentReport.tsx` | Dark selects + cards; NES `border-l-4` stat accents; NES-coloured P/L/A badges; inline hex progress bars |
| `attendance-frontend/src/components/CourseExport.tsx` | Dark inputs/select; full `bg-nes-blue` export button with glow; bouncing `Download` icon during export |
| `attendance-frontend/src/components/AvatarUpload.tsx` | Dark avatar placeholder; `ring-nes-blue/20`; dark "Change Photo" button; dropped unused `React` import |
| `attendance-frontend/src/components/Layout.tsx` | **DELETED** — was a stale unused component causing type errors |

**Build status after these changes:** `npm run build` passes cleanly (verified). Dev server runs on port 5174.

---

### ✅ COMPLETED — Toast integration, Quick Stats, Page Transitions

**Build status:** `npx tsc --noEmit` → zero errors. `npm run build` → clean.

| File | What changed |
|---|---|
| `src/components/AttendanceEntry.tsx` | Toast integration complete: submit success/error → `toast()`; load errors remain inline; `success` state removed |
| `src/pages/TeacherDashboard.tsx` (ProfileTab) | Toast integration complete (done by user): password change success/error → `toast()`; `pwError`/`pwSuccess` states removed |
| `src/components/AvatarUpload.tsx` | Toast integration complete: upload success/error → `toast()`; `error`/`success` states and inline text removed |
| `src/components/CourseExport.tsx` | Toast integration complete: export success/error → `toast()`; load error kept inline as `loadError`; export error now also fires success toast on download |
| `src/pages/TeacherDashboard.tsx` (main) | Quick stats greeting header added (time-of-day greeting + user name + role badge, no API call needed); tab content wrapped in `<div key={currentView} className="animate-fade-slide-up">` for page transitions |

---

### ✅ COMPLETED — Visual Redesign (session 2)

NES retro palette fully discarded. New indigo/violet/emerald theme applied to every file.

**New colour tokens** (in `tailwind.config.js`):

| Token | Hex | Role |
|---|---|---|
| `primary` | `#6366F1` | Indigo — main actions, active nav, CTA buttons |
| `accent` | `#8B5CF6` | Violet — secondary highlights / aurora orb |
| `success` | `#22C55E` | Emerald — safe attendance, present, success toasts |
| `danger` | `#EF4444` | Red — critical attendance, absent, error states |
| `warn` | `#F59E0B` | Amber — late, teacher names, admin accents |
| `info` | `#06B6D4` | Cyan — informational / aurora orb |
| `surface-dark` | `#0F1117` | Sidebar, top bars |
| `surface` | `#161B27` | Card / panel backgrounds |
| `surface-light` | `#1E2538` | Elevated surfaces |
| `background` | `#080B12` | Page background |

**Login page aurora background (`LoginPage.tsx`):**
- 5 oversized blurred radial orbs (indigo, violet, cyan, rose, emerald) positioned absolutely
- Each uses `animate-float-1/2/3` keyframes (18–25 s loops) with staggered `animationDelay` for independent drift
- Subtle 60 px CSS grid overlay at 2.5% opacity adds depth
- Login card: `bg-surface/80 backdrop-blur-2xl` glassmorphism + `shadow-[0_25px_80px_rgba(0,0,0,0.6)]`
- Icon box: `animate-pulse-glow` recoloured to indigo glow

**Transitions added across all interactive elements:**
- Primary buttons: `hover:-translate-y-0.5 active:translate-y-0` lift + indigo shadow intensification
- Student course cards: `hover:-translate-y-0.5` lift
- Avatar ring: `ring-primary/20 → ring-primary/40` on hover
- Input fields: `hover:border-white/25` brightening on hover
- `Mark All Present` button: green hover lift

**Toast redesign (`ToastContext.tsx`):** `bg-surface` dark cards with a 4 px coloured left accent bar (indigo/red/amber) replacing the old tinted backgrounds.

**Files changed in this session:**
`tailwind.config.js`, `src/index.css`, `src/pages/LoginPage.tsx`, `src/pages/TeacherDashboard.tsx`, `src/pages/StudentDashboard.tsx`, `src/components/Sidebar.tsx`, `src/components/AttendanceEntry.tsx`, `src/components/StudentReport.tsx`, `src/components/CourseExport.tsx`, `src/components/AvatarUpload.tsx`, `src/context/ToastContext.tsx`

**Build status:** `npm run build` passes cleanly. Zero TypeScript errors.

---

### ❌ NOT DONE — End-to-end manual verification

Everything compiles and the dev server runs on **port 5174**. The following tests should be run manually against the live backend (`uvicorn app.main:app --reload` on port 8000, seeded DB).

| Test | What to verify |
|---|---|
| Admin login | `admin@college.edu` / `password123` — greeting shows amber "Administrator" badge; all courses visible in all 3 tabs |
| Teacher login | `alice@college.edu` / `password123` — greeting shows indigo "Teacher" badge; only Alice's courses appear; date-range CSV export downloads correctly |
| Student login | `student01@college.edu` / `password123` — teacher names appear in amber under each course; bunk calculator hero renders with correct glow colour |
| Login aurora | Login background should show slowly drifting coloured orbs (indigo, violet, cyan, rose, emerald) |
| Toasts | Submit attendance → indigo-accent success toast; change password → toast; upload avatar → toast; export CSV → success toast |
| Mobile | Narrow to <768 px — hamburger (☰) top-left appears; tap opens sidebar drawer; nav item click closes it |
| Tab transitions | Switch between TeacherDashboard tabs — content fades and slides up on each switch |
| Submit button | Mark Attendance — "Submit Attendance" is solid indigo and lifts on hover when all students are marked |

---

### Architecture Notes for Next Model

- **`glass-panel` CSS class**: `bg-surface border border-white/10 shadow-lg rounded-xl`. Do NOT revert to white backgrounds.
- **Input styling convention**: `bg-white/8 border border-white/15 text-white placeholder-white/30 focus:ring-primary/50 focus:border-primary/50 hover:border-white/25`.
- **Select `option` elements** need `className="bg-surface-dark text-white"` so the browser dropdown doesn't render white-on-dark.
- **Sidebar layout**: sidebar is `position: fixed` always. `TeacherDashboard` main area uses `md:ml-64 pt-16 md:pt-8`. Do not restore `flex-col md:flex-row` or `mt-[140px]`.
- **Toast convention**: `toast(msg, 'error')` for action failures, `toast(msg, 'success')` for completions. Keep inline error `<div>`s only for initial data-load failures (persistent, not transient).
- **Colour reference** (from `tailwind.config.js`):
  - `primary: #6366F1` — indigo, main actions
  - `accent: #8B5CF6` — violet, secondary
  - `success: #22C55E` — emerald, safe/present
  - `danger: #EF4444` — red, critical/absent
  - `warn: #F59E0B` — amber, late/teacher/admin
  - `info: #06B6D4` — cyan, informational
  - `surface-dark: #0F1117` — sidebar/bars
  - `surface: #161B27` — cards/panels
  - `background: #080B12` — page background
- **Login aurora**: 5 floating orbs with `animate-float-1/2/3`. Keyframes defined in `tailwind.config.js`. Do not replace with a static gradient.

---

## Phase 7 — UX Enhancements, Business Rules & Bug Fixes

### Backend

#### `seed_db.py` — Refactored for 4-Subject Constraint
- **Reduced to 4 departments:** Physics, Mathematics, Chemistry, Biology.
- **4 teachers** — one per department:
  - `alice@college.edu` → Physics (PHYS101)
  - `bob@college.edu` → Mathematics (MATH101)
  - `carol@college.edu` → Chemistry (CHEM101)
  - `dave@college.edu` → Biology (BIO101)
- **Fixed `KeyError: 'CS'`** — admin was being assigned to the removed CS department; now defaults to PHYS.
- **Fixed `ValueError: Sample larger than population`** — enrollment sampling now caps at `min(randint(3,5), len(course_list))` since there are only 4 courses.

#### `app/schemas/attendance.py` — Validation Rule Change
- **Removed** the future-date restriction entirely — teachers can mark attendance for any date.
- **Added weekend validator** (`date_cannot_be_weekend`): attendance on Saturday (`weekday() == 5`) or Sunday (`weekday() == 6`) is rejected with a descriptive error message.

### Frontend

#### `src/utils/confetti.ts` — New file (pure-JS confetti)
- Created a zero-dependency confetti animation utility using DOM `<div>` elements + CSS `@keyframes`.
- Replaces the `canvas-confetti` npm package which was imported but never installed (causing the blank page crash).
- `fireConfetti(count)` creates coloured particles that fall and self-clean after ~3.5 s.

#### `src/pages/LoginPage.tsx`
- Swapped `import confetti from 'canvas-confetti'` → `import { fireConfetti } from '../utils/confetti'`.
- Fires `fireConfetti(150)` on successful login.

#### `src/components/AttendanceEntry.tsx`
- **Confetti**: swapped canvas-confetti → `fireConfetti(100)` on successful bulk submission.
- **Student dropdown**: replaced free-text search `<input>` with a `<select>` dropdown listing all students by full name.
- **Email removed**: roster rows now display First + Last Name only (no email address).
- **Date-aware pre-fill**: merged the two `useEffect` hooks (course change + date change) into one that fires on both. When course or date changes:
  1. Fetches the roster.
  2. Calls `GET /courses/{id}/attendance/export?start_date={date}&end_date={date}` to retrieve existing records.
  3. Pre-populates the attendance state from CSV response — so re-submitting the same date works without re-marking everyone.
- **Weekend detection** (client-side, instant):
  - Parses selected date with `new Date(yyyy, mm-1, dd)` (local time, not UTC) to avoid off-by-one bugs.
  - Shows an amber `warn` banner: *"It's Saturday/Sunday — no classes today! Attendance cannot be marked on weekends."*
  - Disables the Submit button on weekends.
- **Error message fix**: FastAPI Pydantic validation errors return `detail` as an array; the frontend now extracts `.msg` from each item instead of rendering `[object Object]`.

---

## Known Limitations & Future Work (updated)

- **No JWT refresh** — token expires after 60 min; user must log in again.
- **Local avatar storage** — replace with S3/cloud in production.
- **No Alembic migrations** — schema changes via `ALTER TABLE` in seed_db.py.
- **CORS open** — restrict `allow_origins` to frontend domain in production.
- **SECRET_KEY is a placeholder** — replace before any real deployment.
- **Attendance pre-fill uses CSV export** — a dedicated JSON endpoint per student+course+date would be more efficient.
- **No login rate limiting** — consider `slowapi` in production.
