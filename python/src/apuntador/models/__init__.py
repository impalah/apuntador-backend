"""
Models package.

Contains shared Pydantic models used across multiple modules.
Module-specific models are located in their respective module directories.
"""

# Shared models (used by multiple modules)
# Import error models (RFC 7807)
from apuntador.models.errors import ProblemDetail, ValidationErrorDetail
from apuntador.models.shared import ErrorResponse, HealthResponse

__all__ = [
    # Shared
    "ErrorResponse",
    "HealthResponse",
    # RFC 7807 Error models
    "ProblemDetail",
    "ValidationErrorDetail",
]
