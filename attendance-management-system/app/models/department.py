"""
app/models/department.py
------------------------
ORM model for the `departments` table.
"""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)

    # Relationships (back-references populated by child models)
    users: Mapped[list["User"]] = relationship("User", back_populates="department")
    courses: Mapped[list["Course"]] = relationship("Course", back_populates="department")

    def __repr__(self) -> str:
        return f"<Department name={self.name!r} code={self.code!r}>"
