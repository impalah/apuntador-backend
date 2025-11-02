"""
Loguru configuration for the application.

This module configures loguru with:
- Automatic Trace ID in each log
- Configurable format from settings
- Redirection of standard library logs to loguru
- Support for colorization in development
"""

import logging
import sys
from typing import Any

from loguru import logger

from apuntador.config import settings
from apuntador.core.trace_context import trace_id_context


def add_trace_id(record: dict[str, Any]) -> bool:
    """
    Adds the trace_id to the log record.

    The trace_id is obtained from the current request context,
    allowing tracking of logs from the same request.

    Args:
        record: Loguru record

    Returns:
        True to indicate that the filter passed
    """
    trace_id = trace_id_context.get()
    record["extra"]["trace_id"] = trace_id if trace_id else "N/A"
    return True


def configure_logger() -> None:
    """
    Configures loguru with application settings.

    This function:
    1. Removes default loguru handlers
    2. Adds handler to stderr with custom configuration
    3. Configures level, format, colorization, etc.
    """
    # Remove default configuration
    logger.remove()

    # Add configured handler
    logger.add(
        sink=sys.stderr,
        level=settings.log_level.upper(),
        format=settings.log_format,
        filter=add_trace_id,
        colorize=True,
        serialize=False,
        backtrace=True,
        diagnose=True,
        enqueue=settings.logger_enqueue,
    )


# Configure logger when importing the module
configure_logger()


__all__ = ["logger", "InterceptHandler"]


class InterceptHandler(logging.Handler):
    """
    Handler to redirect standard logging logs to loguru.

    This allows capturing logs from libraries that use standard logging
    (like uvicorn, httpx, sqlalchemy) and process them with loguru.

    Usage:
        import logging
        from apuntador.core.logging import InterceptHandler

        logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)
        logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    """

    def emit(self, record: logging.LogRecord) -> None:
        """
        Redirects a standard logging record to loguru.

        Args:
            record: logging.LogRecord record
        """
        # Get loguru logger with appropriate depth
        loguru_logger = logger.opt(depth=6, exception=record.exc_info)

        # Redirect the log to loguru
        loguru_logger.log(record.levelname, record.getMessage())


def intercept_standard_logging() -> None:
    """
    Configures redirection of standard logging to loguru.

    Intercepts logs from:
    - uvicorn (ASGI server)
    - uvicorn.access (request logs)
    - uvicorn.error (error logs)
    - httpx (HTTP client)

    Call this function in main.py when initializing the app.
    """
    # Configure basic logging
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)

    # Intercept specific loggers
    for logger_name in [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "httpx",
        "fastapi",
    ]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False


# Optional: Uncomment to intercept SQLAlchemy logs
# def intercept_sqlalchemy_logging():
#     """Configures redirection of SQLAlchemy logs to loguru."""
#     for logger_name in [
#         "sqlalchemy.engine",
#         "sqlalchemy.pool",
#         "sqlalchemy.dialects",
#         "sqlalchemy.orm",
#     ]:
#         logging_logger = logging.getLogger(logger_name)
#         logging_logger.handlers = [InterceptHandler()]
#         logging_logger.setLevel(logging.INFO)
#         logging_logger.propagate = False
