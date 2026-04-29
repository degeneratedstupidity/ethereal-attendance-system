-- =============================================================================
-- Attendance Management System — PostgreSQL Schema
-- Normalization: 3NF
-- Author: Senior Database Architect
-- =============================================================================

-- Enable the pgcrypto extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- ENUMS
-- =============================================================================

-- User roles: strictly controlled via an enum to prevent invalid data
CREATE TYPE user_role AS ENUM ('admin', 'teacher', 'student');

-- Attendance status: Present / Absent / Late
CREATE TYPE attendance_status AS ENUM ('present', 'absent', 'late');


-- =============================================================================
-- TABLE: departments
-- Purpose: Organizes users and courses into college departments.
--          Extracted into its own table to satisfy 3NF — avoids repeating
--          department name/code in both Users and Courses.
-- =============================================================================

CREATE TABLE departments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(120) NOT NULL UNIQUE,   -- e.g., "Computer Science"
    code        VARCHAR(10)  NOT NULL UNIQUE    -- e.g., "CS"
);


-- =============================================================================
-- TABLE: users
-- Purpose: Single table for all system principals (admin, teacher, student).
--          Role-based access control is handled at the application/API layer.
--
--  3NF note: department_id is a FK, NOT a denormalized dept name string.
--            This removes any transitive dependency (id → dept_id → dept_name).
-- =============================================================================

CREATE TABLE users (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,      -- Login identifier
    password_hash   VARCHAR(255) NOT NULL,              -- bcrypt hash; NEVER store plaintext
    first_name      VARCHAR(80)  NOT NULL,
    last_name       VARCHAR(80)  NOT NULL,
    role            user_role    NOT NULL,              -- 'admin' | 'teacher' | 'student'
    department_id   UUID         REFERENCES departments(id) ON DELETE SET NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE, -- Soft-disable accounts
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Index: fast lookup by role (e.g., "give me all students")
CREATE INDEX idx_users_role ON users(role);
-- Index: fast lookup for login flows
CREATE INDEX idx_users_email ON users(email);


-- =============================================================================
-- TABLE: courses
-- Purpose: Represents a single offered course/subject in a semester.
--
--  3NF note: teacher info is not duplicated here — only teacher_id FK is stored.
--            department_id avoids repeating department details inside courses.
-- =============================================================================

CREATE TABLE courses (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(150) NOT NULL,              -- e.g., "Data Structures"
    code            VARCHAR(20)  NOT NULL UNIQUE,       -- e.g., "CS301"
    credit_hours    SMALLINT     NOT NULL CHECK (credit_hours BETWEEN 1 AND 6),
    department_id   UUID         NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    teacher_id      UUID         REFERENCES users(id) ON DELETE SET NULL,  -- nullable: course may be unassigned
    semester        VARCHAR(20)  NOT NULL,              -- e.g., "Spring", "Fall"
    year            SMALLINT     NOT NULL CHECK (year > 2000),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- A course code is globally unique; but the same code cannot repeat in same semester+year
    CONSTRAINT uq_course_semester UNIQUE (code, semester, year)
);

-- Index: teachers quickly query their own courses
CREATE INDEX idx_courses_teacher ON courses(teacher_id);
CREATE INDEX idx_courses_dept    ON courses(department_id);


-- =============================================================================
-- TABLE: enrollments
-- Purpose: Junction / association table linking students ↔ courses.
--          Represents "Student X is enrolled in Course Y."
--          This is a classic many-to-many bridge in 3NF — no non-key attributes
--          depend on just one part of the composite candidate key.
-- =============================================================================

CREATE TABLE enrollments (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id       UUID        NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    enrolled_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- A student can only be enrolled ONCE per course
    CONSTRAINT uq_enrollment UNIQUE (student_id, course_id)
);

-- Composite index — critical for roster queries: "all students in course X"
CREATE INDEX idx_enrollments_course   ON enrollments(course_id);
CREATE INDEX idx_enrollments_student  ON enrollments(student_id);


-- =============================================================================
-- TABLE: attendance_records
-- Purpose: Core fact table. One row = one student's attendance for one class day.
--
--  Design decisions:
--   - References enrollment_id (NOT raw student_id + course_id) to ensure
--     attendance can only be recorded for officially enrolled students.
--     This is a key integrity guarantee.
--   - The UNIQUE constraint on (enrollment_id, attendance_date) prevents
--     double-submission for the same student on the same day.
--   - recorded_by FK links to the teacher/admin who submitted the record
--     (audit trail).
-- =============================================================================

CREATE TABLE attendance_records (
    id              UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id   UUID             NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    attendance_date DATE             NOT NULL,
    status          attendance_status NOT NULL,          -- 'present' | 'absent' | 'late'
    remarks         TEXT,                                -- Optional: "left early", "medical leave"
    recorded_at     TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    recorded_by     UUID             NOT NULL REFERENCES users(id) ON DELETE RESTRICT,  -- audit trail

    -- CRITICAL: Prevents duplicate attendance entries for the same student on the same date
    CONSTRAINT uq_attendance_per_day UNIQUE (enrollment_id, attendance_date)
);

-- Composite index: most common query pattern — all records for a given enrollment
CREATE INDEX idx_attendance_enrollment ON attendance_records(enrollment_id);
-- Allows filtering attendance by date range efficiently
CREATE INDEX idx_attendance_date       ON attendance_records(attendance_date);
-- Allows finding all records marked by a specific teacher
CREATE INDEX idx_attendance_recorder   ON attendance_records(recorded_by);


-- =============================================================================
-- TRIGGER: auto-update `updated_at` on users table
-- =============================================================================

CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_user_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_timestamp();


-- =============================================================================
-- SEED DATA (for development/testing)
-- =============================================================================

-- Departments
INSERT INTO departments (name, code) VALUES
    ('Computer Science', 'CS'),
    ('Mathematics',      'MATH'),
    ('Physics',          'PHY');

-- Admin user (password: 'admin123' — replace with real bcrypt hash in prod)
INSERT INTO users (email, password_hash, first_name, last_name, role) VALUES
    ('admin@college.edu',
     '$2b$12$EXAMPLEHASHadminXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
     'System', 'Admin', 'admin');
