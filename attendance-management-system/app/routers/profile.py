"""
app/routers/profile.py
-----------------------
Profile management: avatar upload and profile retrieval.
"""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.user import UserOut

router = APIRouter(prefix="/profile", tags=["Profile"])

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "avatars")


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get My Profile",
    description="Returns the full profile of the currently authenticated user, including avatar URL.",
)
async def get_my_profile(current_user=Depends(get_current_user)):
    return current_user


@router.post(
    "/avatar",
    summary="Upload Avatar",
    description=(
        "Upload a profile picture (JPEG, PNG, GIF, or WebP). Max 5 MB. "
        "Saves to static/avatars/ and updates the user's profile_picture_url."
    ),
    responses={
        200: {"description": "Avatar uploaded and profile updated."},
        400: {"description": "Invalid file type or file too large."},
    },
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: JPEG, PNG, GIF, WebP.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is 5 MB.",
        )

    ext = file.content_type.split("/")[-1].replace("jpeg", "jpg")
    filename = f"{current_user.id}.{ext}"
    filepath = os.path.join(STATIC_DIR, filename)

    os.makedirs(STATIC_DIR, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(contents)

    avatar_url = f"/static/avatars/{filename}"
    current_user.profile_picture_url = avatar_url
    db.add(current_user)
    await db.flush()

    return {"profile_picture_url": avatar_url, "message": "Avatar updated successfully."}
