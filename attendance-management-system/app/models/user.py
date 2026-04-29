"""
app/models/user.py
------------------
ORM model for the `users` table.

Supports three roles: admin, teacher, student.
Password storage: only the bcrypt hash is persisted — never plaintext.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    """
    Maps to the PostgreSQL `user_role` ENUM type.
    Inheriting from `str` allows direct JSON serialization.
    """
    admin   = "admin"
    teacher = "teacher"
    student = "student"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )

    # --- Relationships ---
    department: Mapped["Department"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Department", back_populates="users"
    )
    # Courses taught by this user (if teacher)
    courses_taught: Mapped[list["Course"]] = relationship(  # noqa: F821
        "Course", back_populates="teacher", foreign_keys="Course.teacher_id"
    )
    # Enrollments (if student)
    enrollments: Mapped[list["Enrollment"]] = relationship(  # noqa: F821
        "Enrollment", back_populates="student"
    )
    # Attendance records marked by this user (if teacher/admin)
    recorded_attendance: Mapped[list["AttendanceRecord"]] = relationship(  # noqa: F821
        "AttendanceRecord", back_populates="recorder",
        foreign_keys="AttendanceRecord.recorded_by"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User email={self.email!r} role={self.role!r}>"
