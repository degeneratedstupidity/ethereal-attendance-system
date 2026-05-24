# Ethereal Attendance System

A web app for colleges to track student attendance. Teachers can mark who showed up, students can see their attendance percentage and figure out how many more classes they can skip (or must attend), and admins get a full overview of everything.

**Live demo accounts are included — no signup needed.**

---

## What it does

| Who | What they can do |
|---|---|
| **Admin** | See all courses and every student's attendance across the college |
| **Teacher** | Mark attendance for their classes, download attendance reports as Excel-friendly CSV files |
| **Student** | Check their own attendance per course, use the bunk calculator to see if they're safe or at risk |

---

## Run it on your computer (Docker — recommended)

This is the easiest way. Docker bundles everything the app needs so you don't have to install Python, PostgreSQL, or Node.js separately.

### Step 1 — Install Docker Desktop

Download and install it from the official site:
- **Windows / Mac:** https://www.docker.com/products/docker-desktop/
- **Linux:** https://docs.docker.com/engine/install/

Once installed, open Docker Desktop and make sure it's running (you'll see the whale icon in your taskbar/menu bar).

---

### Step 2 — Download this project

Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux) and run:

```bash
git clone https://github.com/degeneratedstupidity/ethereal-attendance-system.git
cd ethereal-attendance-system
```

> Don't have Git? Download it from https://git-scm.com/downloads, then retry the commands above.

---

### Step 3 — Start the app

```bash
docker compose up --build
```

This will download everything needed and start the app. It takes **2–5 minutes the first time**. You'll know it's ready when you see lines like:

```
✅ Database tables verified/created.
🚀 Starting Attendance Management System
```

> If you see an error about the database not being ready, just run `docker compose up` again (without `--build`) — it fixes itself on the second run.

---

### Step 4 — Load the demo data

Open a **new terminal window** (keep the first one running) and run:

```bash
cd ethereal-attendance-system
docker compose exec backend python seed_db.py
```

This fills the database with 50 fake students, 10 courses, and 30 days of attendance history so you have something to explore.

---

### Step 5 — Open the app

Go to this address in your browser:

```
http://localhost
```

That's it. The app is running.

---

## Login with demo accounts

All accounts use the same password: **`password123`**

| Account type | Email to use |
|---|---|
| Admin | `admin@college.edu` |
| Teacher (Physics) | `alice@college.edu` |
| Teacher (Maths) | `bob@college.edu` |
| Teacher (Chemistry) | `carol@college.edu` |
| Student | `student01@college.edu` (or student02, student03 … up to student50) |

---

## Stopping the app

Press `Ctrl + C` in the terminal where the app is running, then:

```bash
docker compose down
```

To start it again later (without rebuilding everything from scratch):

```bash
docker compose up
```

---

## Explore the API (for developers)

The backend exposes fully documented API endpoints that you can test directly in the browser:

- **http://localhost:8000/docs** — Interactive API explorer (Swagger UI)
- **http://localhost:8000/redoc** — Alternate API reference

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 (3NF schema) |
| Auth | JWT (HS256) · bcrypt password hashing |
| Frontend | React 18 · TypeScript · TailwindCSS · Vite |
| Infrastructure | Docker · Docker Compose · Nginx |

---

## Project layout

```
ethereal-attendance-system/
├── docker-compose.yml
├── attendance-management-system/   ← Python / FastAPI backend
│   ├── app/
│   │   ├── core/        (config, database, JWT security)
│   │   ├── models/      (SQLAlchemy ORM models)
│   │   ├── schemas/     (Pydantic request/response shapes)
│   │   ├── services/    (business logic)
│   │   └── routers/     (API endpoints)
│   ├── sql/schema.sql   (raw PostgreSQL schema)
│   ├── seed_db.py       (demo data loader)
│   └── requirements.txt
└── attendance-frontend/            ← React / TypeScript frontend
    ├── src/
    │   ├── pages/       (Login, TeacherDashboard, StudentDashboard)
    │   └── components/  (AttendanceEntry, StudentReport, CourseExport …)
    └── nginx.conf
```

---

## Running without Docker (manual setup)

Only follow this if you prefer not to use Docker and are comfortable with the terminal.

**You'll need:** Python 3.11+, Node.js 18+, and PostgreSQL installed.

**Backend:**

```bash
cd attendance-management-system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Open .env and update DATABASE_URL with your PostgreSQL credentials

psql -U postgres -c "CREATE DATABASE attendance_db;"
uvicorn app.main:app --reload --port 8000
```

In a new terminal, load the demo data:

```bash
cd attendance-management-system
source venv/bin/activate
python seed_db.py
```

**Frontend:**

```bash
cd attendance-frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## License

MIT
