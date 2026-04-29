# Goal Description

The goal is to revamp the Attendance Management System's UI/UX to be immersive, mobile-responsive, and vibrant using an NES color palette. We will add dynamic animations to icons and fix the submit button bug. Additionally, we will introduce new backend and frontend features:
- Teachers can export attendance reports for any day/month/year for their courses.
- Students can see their assigned teacher's name for each course.
- Admins can view all courses and student reports.
- Rename "Attendify" to "suupyTulip University" globally.
- Create a `project_overview.txt` with updated requirements.

## User Review Required

> [!IMPORTANT]
> - **NES Color Palette:** We will replace the current 'Salmon' theme with vibrant, 8-bit style colors characteristic of the NES (bright reds, deep blues, vivid greens, yellows).
> - **Global Rename:** The app's name will change from "Attendify" to "suupyTulip University" across all UI headers and page titles.
> - **Admin Access:** The existing `TeacherDashboard` will be used for Admins as well, but modified so Admins can see *all* courses in the system instead of just their assigned ones.

## Open Questions

> [!WARNING]
> - For the "teachers to be able to export any day or months or years report", I plan to add a new section in the Teacher Dashboard where teachers select a course and a date range (Start Date to End Date) to download a CSV. Is this format acceptable?

## Proposed Changes

### Backend Implementation

#### [MODIFY] app/schemas/attendance.py
- Add `teacher_name: str | None = None` to the `CourseAttendanceSummary` schema.

#### [MODIFY] app/services/attendance_service.py
- Update `get_student_attendance` to preload `Course.teacher` and populate the `teacher_name` field for the student's dashboard.
- Create a new function `export_course_attendance_csv(db, course_id, start_date, end_date)` that fetches all attendance records for a course within the given date range and formats them as a CSV string.

#### [MODIFY] app/routers/attendance.py
- Add a new endpoint `GET /courses/{course_id}/attendance/export` that accepts `start_date` and `end_date` query parameters, verifies course ownership (unless admin), and returns a StreamingResponse of the CSV.

### Frontend Implementation

#### [MODIFY] tailwind.config.js & index.css
- Update `tailwind.config.js` to include NES colors: `nes-red` (#E52521), `nes-blue` (#0043C6), `nes-green` (#008F39), `nes-yellow` (#FAD100).
- Add custom keyframes in `tailwind.config.js` for bouncing, pulsing, and shimmering effects.
- Ensure global styles support mobile responsiveness.

#### [MODIFY] Components (Globally)
- **Rename:** Replace all instances of "Attendify" with "suupyTulip University".
- **Animations:** Add classes like `hover:animate-pulse`, `hover:-translate-y-1`, and transitions to all Lucide icons and buttons to create an immersive experience.
- **Bug Fix:** Locate the problematic submit button (likely in `AttendanceEntry.tsx` or `LoginPage.tsx`) and ensure its default background color is explicitly set and visible without hovering.

#### [MODIFY] src/pages/TeacherDashboard.tsx & src/components/AttendanceEntry.tsx & src/components/StudentReport.tsx
- **Admin View:** Conditionally fetch `/courses/` (all courses) if the user is an admin, and `/teachers/me/courses` if the user is a teacher.
- **New Export UI:** Add a new tab or section for "Course Reports" where the teacher/admin can pick a course, select a Start Date and End Date, and click an "Export CSV" button.

#### [MODIFY] src/pages/StudentDashboard.tsx
- Update the UI to display the `teacher_name` returned from the API next to each enrolled course.
- Refine the layout using the new NES color palette and animations.

#### [NEW] project_overview.txt
- Create this file at the project root, copy the contents of `PROJECT_OVERVIEW.md`, and append the new requirements implemented in this session.

## Verification Plan

### Automated Tests
- Run backend with `uvicorn app.main:app --reload` and check that the new `/courses/{course_id}/attendance/export` endpoint works.

### Manual Verification
- Log in as **Admin** (`admin@college.edu`) and verify all courses are visible and reports can be generated.
- Log in as **Teacher** (`alice@college.edu`) and export a date-filtered report for a specific course.
- Log in as **Student** (`student01@college.edu`) and verify the assigned teacher's name appears on the dashboard.
- Shrink the browser window to mobile size and ensure the UI adapts correctly (hamburger menus, stacked columns).
- Verify the NES colors and animations make the application feel highly dynamic and engaging.
- Ensure the submit buttons are visible without hovering.
