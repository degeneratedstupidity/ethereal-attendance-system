"""
app/core/database.py
--------------------
Async SQLAlchemy engine and session factory.

Key design decisions:
- Uses `asyncpg` driver for high-performance async PostgreSQL access.
- `AsyncSession` with `expire_on_commit=False` prevents lazy-load errors
  after commits in async context.
- `get_db()` is a FastAPI dependency that yields a session per request and
  guarantees cleanup (commit on success, rollback on error, always close).
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# echo=True logs all SQL statements — useful for development, disable in prod.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,        # Max connections kept in pool
    max_overflow=20,     # Extra connections allowed beyond pool_size under load
    pool_pre_ping=True,  # Verify connections before use (handles stale connections)
)

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoids MissingGreenlet errors in async context
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# FastAPI Dependency: get_db
# ---------------------------------------------------------------------------
async def get_db() -> AsyncSession:
    """
    Yields an async database session for use in FastAPI route handlers.

    Usage in a router:
        @router.get("/...")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically committed on success and rolled back on
    any unhandled exception, then closed regardless.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Context Manager: for use outside of FastAPI (scripts, tests, etc.)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def get_db_context():
    """
    Async context manager for database sessions outside of FastAPI's
    dependency injection system (e.g., CLI scripts, seeding, testing).

    Usage:
        async with get_db_context() as db:
            result = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
