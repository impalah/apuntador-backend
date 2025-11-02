"""
Middleware to add trace_id to each request.

The trace_id allows tracking logs from the same HTTP request throughout
the entire application, facilitating debugging and observability.
"""

import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from apuntador.core.logging import logger
from apuntador.core.trace_context import trace_id_context


class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique trace_id to each request.

    The trace_id is stored in a context variable (contextvars)
    that is available in all logs during request processing.

    Flow:
    1. Request arrives → generates UUID as trace_id
    2. Stores trace_id in contextvars
    3. All logs automatically include the trace_id
    4. Response includes X-Trace-ID header
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Processes the request by adding trace_id.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            Response with X-Trace-ID header
        """
        # Generate unique trace_id for this request
        trace_id = str(uuid.uuid4())

        # Store in contextvars (available throughout the request)
        trace_id_context.set(trace_id)

        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"trace_id": trace_id},
        )

        try:
            # Process request
            response = await call_next(request)

            # Add trace_id to response headers
            response.headers["X-Trace-ID"] = trace_id

            # Log request completion
            logger.info(
                f"Request completed: {request.method} {request.url.path} - Status: {response.status_code}",  # noqa: E501
                extra={"trace_id": trace_id},
            )

            return response

        except Exception:
            # Log error with trace_id
            logger.exception(
                f"Request failed: {request.method} {request.url.path}",
                extra={"trace_id": trace_id},
            )
            raise

        finally:
            # Clean up context (important to avoid mixing trace_ids)
            trace_id_context.set(None)


# Export both middleware classes
from apuntador.middleware.mtls_validation import MTLSValidationMiddleware  # noqa: E402

__all__ = ["TraceIDMiddleware", "MTLSValidationMiddleware"]
