"""
app/exceptions.py
-----------------
Custom exception classes and FastAPI exception handlers.

These translate domain-level errors into appropriate HTTP responses,
keeping routers clean of try/except boilerplate.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


# ---------------------------------------------------------------------------
# Custom Exception Classes
# ---------------------------------------------------------------------------

class AttendanceSystemException(Exception):
    """Base exception for all application-level errors."""
    pass


class ResourceNotFoundError(AttendanceSystemException):
    """Raised when a requested resource does not exist in the database."""
    def __init__(self, resource: str, identifier: str):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} with id '{identifier}' not found.")


class DuplicateResourceError(AttendanceSystemException):
    """
    Raised when a unique constraint would be violated.
    Example: enrolling a student twice, or submitting attendance twice for same day.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BusinessRuleViolationError(AttendanceSystemException):
    """
    Raised when an operation violates a business rule.
    Example: marking attendance for a student not enrolled in the course.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UnauthorizedError(AttendanceSystemException):
    """Raised when a user attempts an action outside their role permissions."""
    def __init__(self, message: str = "You are not authorized to perform this action."):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# FastAPI Exception Handlers
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers all custom exception handlers on the FastAPI application instance.
    Call this once during app startup in main.py.
    """

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": "NOT_FOUND",
                "message": str(exc),
                "resource": exc.resource,
            },
        )

    @app.exception_handler(DuplicateResourceError)
    async def duplicate_resource_handler(request: Request, exc: DuplicateResourceError):
        return JSONResponse(
            status_code=409,  # 409 Conflict
            content={
                "error": "CONFLICT",
                "message": exc.message,
            },
        )

    @app.exception_handler(BusinessRuleViolationError)
    async def business_rule_handler(request: Request, exc: BusinessRuleViolationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "BUSINESS_RULE_VIOLATION",
                "message": exc.message,
            },
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError):
        return JSONResponse(
            status_code=403,
            content={
                "error": "FORBIDDEN",
                "message": exc.message,
            },
        )

    @app.exception_handler(IntegrityError)
    async def sqlalchemy_integrity_handler(request: Request, exc: IntegrityError):
        """
        Catch-all for SQLAlchemy IntegrityError (constraint violations).
        This is a safety net; ideally the service layer raises DuplicateResourceError
        before this is ever hit.
        """
        # Extract the original DB error message for logging
        detail = str(exc.orig) if exc.orig else str(exc)
        return JSONResponse(
            status_code=409,
            content={
                "error": "DATABASE_CONSTRAINT_VIOLATION",
                "message": "A database constraint was violated. This record may already exist.",
                "detail": detail,
            },
        )
