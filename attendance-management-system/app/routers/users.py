"""
app/routers/users.py
---------------------
FastAPI router for user management and enrollment endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_teacher
from app.models.course import Course
from app.schemas.user import EnrollmentCreate, EnrollmentOut, UserCreate, UserOut
from app.services import course_service

router = APIRouter(tags=["Users & Enrollment"])


@router.post(
    "/users/",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Create a new user (admin, teacher, or student). Admin only. Password is bcrypt-hashed server-side.",
    responses={
        201: {"description": "User created successfully."},
        401: {"description": "Not authenticated."},
        403: {"description": "Admin access required."},
        409: {"description": "Email already registered."},
    },
)
async def create_user(
    user_data: UserCreate,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await course_service.create_user(db=db, user_data=user_data)
    return user


@router.post(
    "/enrollments/",
    response_model=EnrollmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll Student in Course",
    description="Enroll a student in a specific active course. Admin only.",
    responses={
        201: {"description": "Student enrolled successfully."},
        403: {"description": "Admin access required."},
        404: {"description": "Student or course not found."},
        409: {"description": "Student already enrolled in this course."},
        422: {"description": "Business rule violation (e.g., course is inactive)."},
    },
)
async def enroll_student(
    data: EnrollmentCreate,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    enrollment = await course_service.enroll_student(db=db, data=data)
    return enrollment


@router.get(
    "/courses/",
    summary="List All Courses",
    description="Returns all active courses. Requires authentication.",
)
async def list_courses(
    current_user=Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    courses = await course_service.list_courses(db=db)
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "code": c.code,
            "credit_hours": c.credit_hours,
            "semester": c.semester,
            "year": c.year,
        }
        for c in courses
    ]


@router.get(
    "/teachers/me/courses",
    summary="Get My Courses",
    description="Returns the courses taught by the currently authenticated teacher.",
)
async def get_my_courses(
    current_user=Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Course)
        .where(Course.teacher_id == current_user.id, Course.is_active == True)  # noqa: E712
        .order_by(Course.year.desc(), Course.semester, Course.code)
    )
    result = await db.execute(query)
    courses = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "code": c.code,
            "credit_hours": c.credit_hours,
            "semester": c.semester,
            "year": c.year,
        }
        for c in courses
    ]
