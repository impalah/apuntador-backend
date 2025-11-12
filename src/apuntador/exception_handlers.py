"""Global exception handlers for standardized error responses.

Implements RFC 7807 Problem Details for HTTP APIs.
Provides consistent error formatting across all endpoints.
"""

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from apuntador.core.logging import logger
from apuntador.models.errors import ProblemDetail, ValidationErrorDetail


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:  # noqa: ASYNC100
    """Handle HTTPException with RFC 7807 ProblemDetail response.

    Note: FastAPI requires exception handlers to be async even if they don't
    perform async operations. This is part of FastAPI's architecture.

    Args:
        request: The FastAPI request object.
        exc: The HTTPException that was raised.

    Returns:
        JSONResponse with ProblemDetail body.
    """
    logger.error(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url.path),
            "method": request.method,
        },
    )

    problem_detail = ProblemDetail(
        title="An error occurred",
        status=exc.status_code,
        detail=str(exc.detail),
        instance=str(request.url.path),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem_detail.model_dump(exclude_none=True),
    )


async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:  # noqa: ASYNC100
    """Handle unexpected exceptions with 500 Internal Server Error.

    Note: FastAPI requires exception handlers to be async even if they don't
    perform async operations. This is part of FastAPI's architecture.

    Args:
        request: The FastAPI request object.
        exc: The exception that was raised.

    Returns:
        JSONResponse with ProblemDetail body.
    """
    logger.exception(
        f"Unexpected error: {type(exc).__name__}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": str(request.url.path),
            "method": request.method,
        },
    )

    problem_detail = ProblemDetail(
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred. Please try again later.",
        instance=str(request.url.path),
    )

    return JSONResponse(
        status_code=500,
        content=problem_detail.model_dump(exclude_none=True),
    )


async def validation_exception_handler(  # noqa: ASYNC100
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors with detailed field-level information.

    Note: FastAPI requires exception handlers to be async even if they don't
    perform async operations. This is part of FastAPI's architecture.

    Args:
        request: The FastAPI request object.
        exc: The RequestValidationError from Pydantic validation.

    Returns:
        JSONResponse with ProblemDetail body including validation errors.
    """
    logger.warning(
        f"Validation error: {len(exc.errors())} errors",
        extra={
            "error_count": len(exc.errors()),
            "errors": exc.errors(),
            "path": str(request.url.path),
            "method": request.method,
        },
    )

    # Convert Pydantic errors to ValidationErrorDetail
    errors = [
        ValidationErrorDetail(
            type=error["type"],
            loc=tuple(str(loc) for loc in error["loc"]),
            msg=error["msg"],
            input=error.get("input"),
            ctx=(
                {k: str(v) for k, v in error.get("ctx", {}).items()}
                if error.get("ctx")
                else None
            ),
            url=error.get("url"),
        )
        for error in exc.errors()
    ]

    problem_detail = ProblemDetail(
        title="Validation Error",
        status=422,
        detail=f"One or more validation errors occurred ({len(errors)} errors).",
        instance=str(request.url.path),
        errors=errors,
    )

    return JSONResponse(
        status_code=422,
        content=problem_detail.model_dump(exclude_none=True),
    )
