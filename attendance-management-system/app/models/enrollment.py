"""
app/models/enrollment.py
------------------------
ORM model for the `enrollments` junction table.

Each row represents one student enrolled in one course.
The UNIQUE constraint on (student_id, course_id) prevents duplicate enrollments.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        # Database-level unique constraint — mirrors the SQL schema
        UniqueConstraint("student_id", "course_id", name="uq_enrollment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- Relationships ---
    student: Mapped["User"] = relationship("User", back_populates="enrollments")  # noqa: F821
    course: Mapped["Course"] = relationship("Course", back_populates="enrollments")  # noqa: F821
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(  # noqa: F821
        "AttendanceRecord", back_populates="enrollment"
    )

    def __repr__(self) -> str:
        return f"<Enrollment student={self.student_id} course={self.course_id}>"
