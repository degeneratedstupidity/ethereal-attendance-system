"""
tests/test_attendance.py
------------------------
Integration tests for the POST /api/v1/attendance/bulk endpoint.

Tests cover:
  Happy Paths:
    1. Submitting valid attendance for all enrolled students → 201
    2. Re-submitting attendance for the same date → 201 (UPSERT, records_updated > 0)

  Failure Paths:
    3. Sending a student_id that is NOT enrolled in the course → 422
    4. Sending a date in the future → 422 (Pydantic validator)
    5. Sending an empty records list → 422 (Pydantic min_length)
    6. Submitting with a recorder (teacher) ID that doesn't exist → 404
    7. Submitting to a course that doesn't exist → 404
    8. Sending duplicate student_ids in the same payload → 422
"""

import uuid
from datetime import date, timedelta


# Shared test date: yesterday (always valid, never in the future)
YESTERDAY = (date.today() - timedelta(days=10)).isoformat()
TOMORROW  = (date.today() + timedelta(days=1)).isoformat()


def _bulk_payload(seeded: dict, date_str: str, status: str = "present") -> dict:
    """
    Helper: build a valid BulkAttendanceRequest payload for all seeded students.
    Makes test setup concise and avoids repetition.
    """
    return {
        "course_id": str(seeded["course_id"]),
        "attendance_date": date_str,
        "records": [
            {"student_id": str(sid), "status": status}
            for sid in seeded["student_ids"]
        ],
    }


class TestBulkAttendanceSuccess:
    """Happy-path tests for bulk attendance submission."""

    async def test_submit_bulk_attendance_returns_201(self, client, seeded):
        """
        Submitting valid attendance for all enrolled students must return
        HTTP 201 Created with a well-formed success body.
        """
        payload = _bulk_payload(seeded, YESTERDAY)
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )

        assert response.status_code == 201, response.text
        data = response.json()

        assert data["message"] == "Attendance submitted successfully."
        assert data["course_id"] == str(seeded["course_id"])
        assert data["attendance_date"] == YESTERDAY
        # All 3 students are new records; none are updates on first submission
        assert data["records_created"] == 3
        assert data["records_updated"] == 0

    async def test_submit_with_mixed_statuses(self, client, seeded):
        """All three status values (present, absent, late) are accepted."""
        payload = {
            "course_id": str(seeded["course_id"]),
            "attendance_date": YESTERDAY,
            "records": [
                {"student_id": str(seeded["student_ids"][0]), "status": "present"},
                {"student_id": str(seeded["student_ids"][1]), "status": "absent"},
                {"student_id": str(seeded["student_ids"][2]), "status": "late"},
            ],
        }
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )
        # Either 201 (all new) or 201 (upsert) — both are acceptable
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["records_created"] + data["records_updated"] == 3

    async def test_upsert_resubmission_updates_existing_records(self, client, seeded):
        """
        Re-submitting attendance for the SAME date must UPSERT (update, not fail).
        records_updated must equal the number of students on the second call.

        Business rule: teachers can correct mistakes after initial submission.
        """
        # First submission: everyone is "present"
        payload = _bulk_payload(seeded, YESTERDAY, status="present")
        r1 = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )
        assert r1.status_code == 201

        # Second submission for the SAME date: change everyone to "absent"
        payload["records"] = [
            {"student_id": str(sid), "status": "absent"}
            for sid in seeded["student_ids"]
        ]
        r2 = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )
        assert r2.status_code == 201, r2.text
        data = r2.json()

        # All records should be UPDATED, none created afresh
        assert data["records_updated"] == 3
        assert data["records_created"] == 0

    async def test_submit_with_remarks(self, client, seeded):
        """Optional 'remarks' field is accepted and does not cause errors."""
        payload = {
            "course_id": str(seeded["course_id"]),
            "attendance_date": YESTERDAY,
            "records": [
                {
                    "student_id": str(seeded["student_ids"][0]),
                    "status": "absent",
                    "remarks": "Medical leave — submitted hospital certificate.",
                },
                {"student_id": str(seeded["student_ids"][1]), "status": "present"},
                {"student_id": str(seeded["student_ids"][2]), "status": "present"},
            ],
        }
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )
        assert response.status_code == 201, response.text


class TestBulkAttendanceFailures:
    """Error-path tests — verifying the API correctly rejects invalid requests."""

    async def test_unenrolled_student_returns_422(self, client, seeded):
        """
        CRITICAL BUSINESS RULE:
        If any student_id in the payload is NOT enrolled in the specified course,
        the entire request must be rejected with HTTP 422 and a BUSINESS_RULE_VIOLATION.

        This prevents attendance being recorded for students who don't belong to the class.
        """
        random_outsider_id = uuid.uuid4()  # This UUID is not enrolled in any course
        payload = {
            "course_id": str(seeded["course_id"]),
            "attendance_date": YESTERDAY,
            "records": [
                # Mix of valid enrolled students and one outsider
                {"student_id": str(seeded["student_ids"][0]), "status": "present"},
                {"student_id": str(random_outsider_id), "status": "present"},  # ← Invalid
            ],
        }
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )

        assert response.status_code == 422, response.text
        data = response.json()
        assert data["error"] == "BUSINESS_RULE_VIOLATION"
        # The error message should identify the problematic student ID
        assert str(random_outsider_id) in data["message"]

    async def test_future_date_returns_422(self, client, seeded):
        """
        Pydantic validator rejects attendance dates in the future.
        A teacher cannot pre-submit attendance for a class that hasn't happened.
        """
        payload = _bulk_payload(seeded, TOMORROW)
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )

        assert response.status_code == 422, response.text
        # FastAPI returns Pydantic validation errors as 422 with a 'detail' list
        data = response.json()
        assert "detail" in data or data.get("error") == "BUSINESS_RULE_VIOLATION"

    async def test_empty_records_list_returns_422(self, client, seeded):
        """
        The 'records' list must have at least 1 entry (enforced by Pydantic min_length=1).
        An empty list should be rejected before reaching any business logic.
        """
        payload = {
            "course_id": str(seeded["course_id"]),
            "attendance_date": YESTERDAY,
            "records": [],  # ← Violates min_length=1
        }
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )
        assert response.status_code == 422, response.text

    async def test_invalid_status_value_returns_422(self, client, seeded):
        """
        An unrecognised status string (not 'present'/'absent'/'late') must be rejected
        by Pydantic schema validation with HTTP 422.
        """
        payload = {
            "course_id": str(seeded["course_id"]),
            "attendance_date": YESTERDAY,
            "records": [
                {"student_id": str(seeded["student_ids"][0]), "status": "excused"},  # ← Invalid enum
            ],
        }
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )
        assert response.status_code == 422, response.text

    async def test_nonexistent_recorder_id_returns_404(self, client, seeded):
        """
        The recorded_by query parameter must be a valid user UUID in the database.
        An unknown UUID must return HTTP 404 (ResourceNotFoundError for 'User (recorder)').
        """
        fake_teacher_id = uuid.uuid4()
        payload = _bulk_payload(seeded, YESTERDAY)
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={fake_teacher_id}",
            json=payload,
        )

        assert response.status_code == 404, response.text
        data = response.json()
        assert data["error"] == "NOT_FOUND"

    async def test_nonexistent_course_id_returns_404(self, client, seeded):
        """
        Submitting attendance to a course that does not exist must return HTTP 404.
        """
        fake_course_id = uuid.uuid4()
        payload = {
            "course_id": str(fake_course_id),  # ← Does not exist
            "attendance_date": YESTERDAY,
            "records": [
                {"student_id": str(seeded["student_ids"][0]), "status": "present"},
            ],
        }
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )

        assert response.status_code == 404, response.text
        data = response.json()
        assert data["error"] == "NOT_FOUND"
        assert data["resource"] == "Course"

    async def test_duplicate_student_ids_in_payload_returns_422(self, client, seeded):
        """
        Sending the same student_id twice in one bulk payload must be rejected.
        This is caught by Pydantic's custom 'no_duplicate_students' validator.
        """
        dup_id = str(seeded["student_ids"][0])
        payload = {
            "course_id": str(seeded["course_id"]),
            "attendance_date": YESTERDAY,
            "records": [
                {"student_id": dup_id, "status": "present"},
                {"student_id": dup_id, "status": "absent"},  # ← Same student twice
            ],
        }
        response = await client.post(
            f"/api/v1/attendance/bulk?recorded_by={seeded['teacher_id']}",
            json=payload,
        )
        assert response.status_code == 422, response.text
