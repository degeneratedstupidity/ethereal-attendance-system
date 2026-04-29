"""
app/models/attendance.py
------------------------
ORM model for the `attendance_records` fact table.

Each row records one student's attendance status for one specific date in one course.
The composite UNIQUE constraint on (enrollment_id, attendance_date) is the critical
integrity guarantee — it prevents duplicate submissions for the same class day.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AttendanceStatus(str, enum.Enum):
    """
    Maps to the PostgreSQL `attendance_status` ENUM type.
    'late' counts as a separate state — the service layer decides
    whether to count it as present or absent for percentage calculations.
    """
    present = "present"
    absent  = "absent"
    late    = "late"


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        # Prevents double-submission for same student on same date
        UniqueConstraint("enrollment_id", "attendance_date", name="uq_attendance_per_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status"), nullable=False
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # --- Relationships ---
    enrollment: Mapped["Enrollment"] = relationship(  # noqa: F821
        "Enrollment", back_populates="attendance_records"
    )
    recorder: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="recorded_attendance",
        foreign_keys=[recorded_by]
    )

    def __repr__(self) -> str:
        return (
            f"<AttendanceRecord enrollment={self.enrollment_id} "
            f"date={self.attendance_date} status={self.status!r}>"
        )
