"""
app/routers/auth.py
--------------------
Authentication endpoints: login, current-user profile, password change.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    verify_password,
    hash_password,
)
from app.schemas.user import ChangePasswordRequest, LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with email and password. Returns a JWT access token.",
    responses={
        200: {"description": "Login successful — JWT returned."},
        401: {"description": "Invalid email or password."},
        403: {"description": "Account is inactive."},
    },
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    from app.models.user import User

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact an administrator.",
        )

    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
        email=user.email,
        profile_picture_url=getattr(user, "profile_picture_url", None),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get Current User",
    description="Returns the profile of the currently authenticated user.",
)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.post(
    "/change-password",
    summary="Change Password",
    description="Allows an authenticated user to change their own password.",
    responses={
        200: {"description": "Password changed successfully."},
        400: {"description": "Current password is incorrect."},
    },
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)
    await db.flush()

    return {"message": "Password changed successfully."}
