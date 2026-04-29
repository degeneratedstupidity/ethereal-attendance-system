"""
tests/test_roster.py
---------------------
Integration tests for the GET /api/v1/courses/{course_id}/roster endpoint.

Tests:
  1. A valid course ID returns a 200 with correct student count and shape.
  2. The response includes the correct fields for each student entry.
  3. A non-existent course ID returns a structured 404 response.
  4. A malformed (non-UUID) course ID returns a 422 Unprocessable Entity.
"""

import uuid


class TestGetClassRoster:
    """Happy-path tests for the class roster endpoint."""

    async def test_roster_returns_200_for_valid_course(self, client, seeded):
        """A valid course_id returns HTTP 200 with the expected response shape."""
        response = await client.get(f"/api/v1/courses/{seeded['course_id']}/roster")

        assert response.status_code == 200
        data = response.json()

        # Top-level fields must be present and correct
        assert data["course_id"] == str(seeded["course_id"])
        assert data["course_code"] == seeded["course_code"]
        assert data["course_name"] == "Algorithms and Data Structures"
        assert data["semester"] == "Spring"
        assert data["year"] == 2026
        assert data["teacher_name"] == "Jane Smith"

    async def test_roster_returns_correct_student_count(self, client, seeded):
        """The roster must list all 3 enrolled students."""
        response = await client.get(f"/api/v1/courses/{seeded['course_id']}/roster")
        data = response.json()

        assert data["student_count"] == 3
        assert len(data["students"]) == 3

    async def test_roster_student_entries_have_required_fields(self, client, seeded):
        """Every student entry in the roster must contain the expected fields."""
        response = await client.get(f"/api/v1/courses/{seeded['course_id']}/roster")
        students = response.json()["students"]

        required_fields = {"enrollment_id", "student_id", "first_name", "last_name", "email", "enrolled_at"}
        for student_entry in students:
            missing = required_fields - set(student_entry.keys())
            assert not missing, f"Student entry missing fields: {missing}"

    async def test_roster_student_ids_match_seeded_data(self, client, seeded):
        """The student_ids returned in the roster must match the seeded UUIDs."""
        response = await client.get(f"/api/v1/courses/{seeded['course_id']}/roster")
        returned_ids = {s["student_id"] for s in response.json()["students"]}
        expected_ids = {str(sid) for sid in seeded["student_ids"]}

        assert returned_ids == expected_ids

    async def test_roster_is_sorted_alphabetically_by_last_name(self, client, seeded):
        """The roster must be sorted by last name (A→Z), then first name."""
        response = await client.get(f"/api/v1/courses/{seeded['course_id']}/roster")
        last_names = [s["last_name"] for s in response.json()["students"]]

        # Seeded: Anderson, Baker, Chen → already alphabetical
        assert last_names == sorted(last_names), "Students are not sorted alphabetically by last name"


class TestGetClassRosterFailures:
    """Error-path tests for the class roster endpoint."""

    async def test_nonexistent_course_returns_404(self, client, seeded):
        """
        A UUID that does not correspond to any course must return HTTP 404
        with a structured error body containing 'NOT_FOUND'.
        """
        nonexistent_id = uuid.uuid4()  # Guaranteed to not exist
        response = await client.get(f"/api/v1/courses/{nonexistent_id}/roster")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NOT_FOUND"
        assert data["resource"] == "Course"
        # The missing ID should be mentioned in the message
        assert str(nonexistent_id) in data["message"]

    async def test_malformed_course_id_returns_422(self, client):
        """
        A non-UUID string in the path parameter must return HTTP 422
        (FastAPI's automatic request validation).
        """
        response = await client.get("/api/v1/courses/not-a-valid-uuid/roster")
        assert response.status_code == 422
