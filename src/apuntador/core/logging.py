"""
Loguru configuration for the application.

This module configures loguru with:
- Automatic Trace ID in each log
- Configurable format from settings (JSON or human-readable)
- Redirection of standard library logs to loguru
- Support for colorization in development
"""

import json
import logging
import sys
from typing import Any, TextIO

from loguru import logger

from apuntador.config import settings
from apuntador.core.trace_context import trace_id_context

# OpenTelemetry integration (optional, only if telemetry is configured)
try:
    from apuntador.core.telemetry import get_current_span_id, get_current_trace_id

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

    def get_current_trace_id() -> str:
        return "N/A"

    def get_current_span_id() -> str:
        return "N/A"


class JsonSink:
    """
    Custom sink for JSON-formatted logs.

    This sink formats log records as JSON objects with structured fields
    suitable for ingestion by logging services (CloudWatch, Datadog, etc.).
    """

    def __init__(self, stream: TextIO = sys.stderr):
        """
        Initialize the JSON sink.

        Args:
            stream: Output stream (default: stderr)
        """
        self.stream = stream

    def write(self, message: Any) -> None:
        """
        Process and write a log record in JSON format.

        Args:
            message: Loguru message object (has .record attribute)
        """
        record = message.record

        # Extract timestamp
        timestamp = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Build structured log object
        log_data = {
            "timestamp": timestamp,
            "level": record["level"].name,
            "trace_id": record["extra"].get("trace_id", "N/A"),
            "span_id": record["extra"].get("span_id", "N/A"),
            "name": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }

        # Add exception info if present
        if record["exception"] is not None:
            exc_type, exc_value, exc_traceback = record["exception"]

            # Get full traceback as string (includes newlines)
            import traceback
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            full_traceback = "".join(tb_lines)

            log_data["exception"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "value": str(exc_value) if exc_value else "",
                "traceback": full_traceback,  # json.dumps will escape newlines automatically
            }

        # Write JSON to stream (json.dumps automatically escapes \n as \\n)
        json_str = json.dumps(log_data, ensure_ascii=False)
        self.stream.write(json_str + "\n")
        self.stream.flush()


def add_trace_id(record: dict[str, Any]) -> bool:
    """
    Adds the trace_id to the log record.

    The trace_id is obtained from OpenTelemetry context if available,
    otherwise falls back to the legacy context variable.
    This allows tracking of logs from the same request and correlating
    them with distributed traces in AWS X-Ray / CloudWatch.

    Args:
        record: Loguru record

    Returns:
        True to indicate that the filter passed
    """
    # Try to get trace_id from OpenTelemetry first
    if OTEL_AVAILABLE:
        otel_trace_id = get_current_trace_id()
        otel_span_id = get_current_span_id()
        if otel_trace_id != "N/A":
            record["extra"]["trace_id"] = otel_trace_id
            record["extra"]["span_id"] = otel_span_id
            return True

    # Fallback to legacy context variable
    trace_id = trace_id_context.get()
    record["extra"]["trace_id"] = trace_id if trace_id else "N/A"
    record["extra"]["span_id"] = "N/A"
    return True


def get_log_format() -> str:
    """
    Returns the appropriate log format based on settings.

    Returns:
        Format string for human-readable logs (includes trace_id
        and span_id for OpenTelemetry)
    """
    if OTEL_AVAILABLE:
        return (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "trace={extra[trace_id]} span={extra[span_id]} | "
            "{name}:{function}:{line} - {message}"
        )
    return (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "trace_id={extra[trace_id]} | "
        "{name}:{function}:{line} - {message}"
    )


def configure_logger() -> None:
    """
    Configures loguru with application settings.

    This function:
    1. Removes default loguru handlers
    2. Adds handler to stderr with custom configuration
    3. Configures level, format, colorization, etc.
    4. Uses JSON serialization if configured
    """
    # Remove default configuration
    logger.remove()

    # Determine if we're using JSON format
    use_json = settings.log_format.lower() == "json"

    if use_json:
        # JSON format: use custom sink
        json_sink = JsonSink(sys.stderr)
        logger.add(
            sink=json_sink.write,
            level=settings.log_level.upper(),
            format="{message}",  # Minimal format, actual formatting in sink
            filter=add_trace_id,
            colorize=False,
            backtrace=True,
            diagnose=True,
            enqueue=settings.logger_enqueue,
        )
    else:
        # Human-readable format
        logger.add(
            sink=sys.stderr,
            level=settings.log_level.upper(),
            format=get_log_format(),
            filter=add_trace_id,
            colorize=False,
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
