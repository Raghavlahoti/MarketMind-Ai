# ============================================================================
# MARKETMIND AI - EXCEPTION HANDLING ARCHITECTURE
# ============================================================================

from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base exception class for all custom application errors."""
    def __init__(self, message: str, status_code: int = 500, details: Any = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class EntityNotFoundError(AppException):
    """Raised when a requested resource (e.g. stock, user) does not exist."""
    def __init__(self, message: str = "Requested resource not found", details: Any = None):
        super().__init__(message=message, status_code=404, details=details)


class AuthenticationError(AppException):
    """Raised for login failures, expired tokens, or unauthorized sessions."""
    def __init__(self, message: str = "Could not validate credentials", details: Any = None):
        super().__init__(message=message, status_code=401, details=details)


class AuthorizationError(AppException):
    """Raised when permissions restrict access to a Resource."""
    def __init__(self, message: str = "Access forbidden", details: Any = None):
        super().__init__(message=message, status_code=403, details=details)


class ValidationError(AppException):
    """Raised for business logic rule violations."""
    def __init__(self, message: str = "Validation failed", details: Any = None):
        super().__init__(message=message, status_code=400, details=details)


def register_exception_handlers(app: FastAPI) -> None:
    """Binds global exception handlers to the FastAPI app instance."""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        content = {
            "error": exc.__class__.__name__,
            "message": exc.message
        }
        if exc.details:
            content["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def global_fallback_handler(request: Request, exc: Exception) -> JSONResponse:
        # Prevent details leakage in prod
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected server error occurred."
            }
        )
