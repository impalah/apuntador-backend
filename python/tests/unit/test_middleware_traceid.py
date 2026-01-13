"""
Additional unit tests for TraceIDMiddleware.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import Request, Response

from apuntador.core.trace_context import trace_id_context
from apuntador.middleware import TraceIDMiddleware


@pytest.fixture
def middleware():
    """Create middleware instance."""
    return TraceIDMiddleware(app=AsyncMock())


@pytest.mark.asyncio
async def test_trace_id_middleware_adds_header(middleware):
    """Test middleware adds X-Trace-ID header."""
    # Arrange
    request = AsyncMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"

    response = Response(content="test", status_code=200)
    call_next = AsyncMock(return_value=response)

    # Act
    result = await middleware.dispatch(request, call_next)

    # Assert
    assert "X-Trace-ID" in result.headers
    assert len(result.headers["X-Trace-ID"]) > 0


@pytest.mark.asyncio
async def test_trace_id_middleware_sets_context_var(middleware):
    """Test middleware sets trace_id in context."""
    # Arrange
    request = AsyncMock(spec=Request)
    request.method = "POST"
    request.url.path = "/test"

    response = Response()

    async def call_next_with_check(req):  # noqa: ASYNC100
        # Verify context var is set during request
        # Note: This callback must be async to match middleware signature
        trace_id = trace_id_context.get()
        assert trace_id is not None
        return response

    # Act
    await middleware.dispatch(request, call_next_with_check)

    # Assert passed inside call_next_with_check


@pytest.mark.asyncio
async def test_trace_id_middleware_handles_exception(middleware):
    """Test middleware handles exceptions in request processing."""
    # Arrange
    request = AsyncMock(spec=Request)
    request.method = "GET"
    request.url.path = "/error"

    async def call_next_raises(req):  # noqa: ASYNC100
        # Note: This callback must be async to match middleware signature
        raise ValueError("Test error")

    # Act & Assert
    with pytest.raises(ValueError, match="Test error"):
        await middleware.dispatch(request, call_next_raises)


@pytest.mark.asyncio
async def test_trace_id_middleware_unique_ids(middleware):
    """Test middleware generates unique trace IDs."""
    # Arrange
    request1 = AsyncMock(spec=Request)
    request1.method = "GET"
    request1.url.path = "/test1"

    request2 = AsyncMock(spec=Request)
    request2.method = "GET"
    request2.url.path = "/test2"

    response1 = Response()
    response2 = Response()

    call_next1 = AsyncMock(return_value=response1)
    call_next2 = AsyncMock(return_value=response2)

    # Act
    result1 = await middleware.dispatch(request1, call_next1)
    result2 = await middleware.dispatch(request2, call_next2)

    # Assert
    assert result1.headers["X-Trace-ID"] != result2.headers["X-Trace-ID"]
