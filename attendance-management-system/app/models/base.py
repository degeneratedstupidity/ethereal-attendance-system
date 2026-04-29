"""
app/models/base.py
------------------
SQLAlchemy declarative base for all ORM models.
Using the newer 2.0-style DeclarativeBase.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    All models must inherit from this class.
    """
    pass
