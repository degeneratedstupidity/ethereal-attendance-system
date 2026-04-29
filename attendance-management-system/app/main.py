"""
app/main.py
-----------
FastAPI application entry point.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine
from app.exceptions import register_exception_handlers
from app.models import Base
from app.routers import attendance, users, auth, profile


# ---------------------------------------------------------------------------
# Static file directory for avatar uploads
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
AVATARS_DIR = os.path.join(STATIC_DIR, "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Lifespan: Startup & Shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables verified/created.")

    yield

    await engine.dispose()
    print("🛑 Database connections closed.")


# ---------------------------------------------------------------------------
# App Instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Attendance Management System API

A RESTful backend for managing student attendance in a college environment.

### Features
- 🔐 **JWT Authentication**: Role-based access (admin / teacher / student)
- 📋 **Class Roster**: Fetch all students enrolled in a course
- ✅ **Bulk Attendance**: Submit or update attendance for an entire class
- 📊 **Attendance Reports**: Per-student percentages with course breakdowns
- 🧮 **Bunk Calculator**: Know exactly how many classes you can miss (or must attend)
- 🖼️ **Profile Pictures**: Upload and serve user avatars
- 👥 **User Management**: Create students, teachers, and admin accounts (admin only)
- 📚 **Enrollments**: Manage student course enrollments
    """,
    contact={"name": "Attendance System Admin", "email": "admin@college.edu"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------

register_exception_handlers(app)


# ---------------------------------------------------------------------------
# Static Files — avatars served at /static/avatars/<filename>
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Routers — all under /api/v1 prefix
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"

app.include_router(auth.router,       prefix=API_PREFIX)
app.include_router(attendance.router, prefix=API_PREFIX)
app.include_router(users.router,      prefix=API_PREFIX)
app.include_router(profile.router,    prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"], summary="Health Check")
async def root():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"], summary="Detailed Health Check")
async def health():
    return {"status": "ok", "database": "connected", "version": settings.APP_VERSION}
