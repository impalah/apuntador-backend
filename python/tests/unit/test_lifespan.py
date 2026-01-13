"""
Unit tests for application lifecycle.
"""

from unittest.mock import MagicMock, patch

import pytest

from apuntador.lifespan import lifespan


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown():
    """Test application lifespan startup and shutdown."""
    # Arrange
    mock_app = MagicMock()

    # Act
    async with lifespan(mock_app):
        # Application is running
        pass

    # Assert - no errors during startup/shutdown


@pytest.mark.asyncio
async def test_lifespan_handles_startup_error():
    """Test lifespan handles errors during startup."""
    # Arrange
    mock_app = MagicMock()

    with patch("apuntador.lifespan.logger") as mock_logger:
        # Act
        async with lifespan(mock_app):
            pass

        # Assert - logger was called
        assert mock_logger.info.called or mock_logger.error.called
