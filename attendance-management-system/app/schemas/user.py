"""
app/schemas/user.py
-------------------
Pydantic schemas for user creation and responses.

NOTE: password_hash is NEVER included in response schemas.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Request body for creating a new user (admin only)."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Plain-text password — hashed server-side.")
    first_name: str = Field(..., max_length=80)
    last_name: str = Field(..., max_length=80)
    role: UserRole
    department_id: Optional[uuid.UUID] = None


class UserOut(BaseModel):
    """Safe user representation — excludes password_hash."""
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    profile_picture_url: Optional[str] = None

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response body for a successful login."""
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    role: UserRole
    full_name: str
    email: str
    profile_picture_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Request body for POST /auth/change-password."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class EnrollmentCreate(BaseModel):
    """Request body for enrolling a student in a course."""
    student_id: uuid.UUID
    course_id: uuid.UUID


class EnrollmentOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    enrolled_at: datetime

    model_config = {"from_attributes": True}
