"""Trace id context variable for logging"""

import contextvars

# Create a context variable to store the trace_id
trace_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)
