"""
Unit tests for exception handlers.

Tests error response formatting and status code mapping.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError

from apuntador.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
)

# ===========================
# HTTP Exception Handler Tests
# ===========================


@pytest.mark.asyncio
async def test_http_exception_handler_400():
    """Test HTTP exception handler with 400 status."""
    # Arrange
    request = MagicMock(spec=Request)
    exc = HTTPException(
        status_code=400,
        detail="Invalid request parameters",
    )

    # Act
    response = await http_exception_handler(request, exc)

    # Assert
    assert response.status_code == 400
    # Response body should contain error details
    assert hasattr(response, "body")


@pytest.mark.asyncio
async def test_http_exception_handler_401():
    """Test HTTP exception handler with 401 unauthorized."""
    # Arrange
    request = MagicMock(spec=Request)
    exc = HTTPException(
        status_code=401,
        detail="Authentication required",
    )

    # Act
    response = await http_exception_handler(request, exc)

    # Assert
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_http_exception_handler_404():
    """Test HTTP exception handler with 404 not found."""
    # Arrange
    request = MagicMock(spec=Request)
    exc = HTTPException(
        status_code=404,
        detail="Resource not found",
    )

    # Act
    response = await http_exception_handler(request, exc)

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_http_exception_handler_500():
    """Test HTTP exception handler with 500 internal error."""
    # Arrange
    request = MagicMock(spec=Request)
    exc = HTTPException(
        status_code=500,
        detail="Internal server error",
    )

    # Act
    response = await http_exception_handler(request, exc)

    # Assert
    assert response.status_code == 500


# ===========================
# Validation Exception Handler Tests
# ===========================


@pytest.mark.asyncio
async def test_validation_exception_handler():
    """Test validation exception handler with request validation errors."""
    # Arrange
    request = MagicMock(spec=Request)

    # Create a simple validation error
    exc = RequestValidationError(errors=[])

    # Act
    response = await validation_exception_handler(request, exc)

    # Assert
    assert response.status_code == 422  # Unprocessable Entity
    # Response should contain validation error details


@pytest.mark.asyncio
async def test_validation_exception_handler_multiple_errors():
    """Test validation exception handler with multiple validation errors."""
    # Arrange
    request = MagicMock(spec=Request)

    # Create validation error with multiple issues
    exc = RequestValidationError(errors=[])

    # Act
    response = await validation_exception_handler(request, exc)

    # Assert
    assert response.status_code == 422
