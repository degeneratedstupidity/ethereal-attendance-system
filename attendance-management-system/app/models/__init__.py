"""
app/models/__init__.py
----------------------
Exposes all ORM models from a single import point.
Ensures all models are registered with SQLAlchemy's metadata
before any table creation or migration commands are run.
"""

from app.models.base import Base
from app.models.department import Department
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.attendance import AttendanceRecord, AttendanceStatus

__all__ = [
    "Base",
    "Department",
    "User",
    "UserRole",
    "Course",
    "Enrollment",
    "AttendanceRecord",
    "AttendanceStatus",
]
