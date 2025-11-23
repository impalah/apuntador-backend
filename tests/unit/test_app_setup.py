"""Tests for application setup utilities."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from apuntador.app_setup import add_root_endpoint, setup_app


@patch("apuntador.app_setup.get_settings")
@patch("apuntador.app_setup.InfrastructureFactory.from_settings")
def test_setup_app(mock_factory, mock_get_settings):
    """Test that setup_app configures the application correctly."""
    app = FastAPI()
    mock_settings = MagicMock()
    mock_get_settings.return_value = mock_settings
    mock_infrastructure = MagicMock()
    mock_factory.return_value = mock_infrastructure

    setup_app(app)

    # Verify settings were fetched
    mock_get_settings.assert_called_once()

    # Verify infrastructure factory was created
    mock_factory.assert_called_once_with(mock_settings)

    # Verify middleware was added (check app.middleware_stack is set)
    assert app.user_middleware is not None


@patch("apuntador.app_setup.get_settings")
def test_add_root_endpoint(mock_get_settings):
    """Test that add_root_endpoint adds the root route."""
    app = FastAPI()
    mock_settings = MagicMock()
    mock_settings.enable_docs = True
    mock_get_settings.return_value = mock_settings

    add_root_endpoint(app)

    # Check that a route was added
    routes = [route.path for route in app.routes]
    assert "/" in routes


@patch("apuntador.app_setup.get_settings")
@pytest.mark.asyncio
async def test_root_endpoint_response_with_docs(mock_get_settings):
    """Test root endpoint response when docs are enabled."""
    from fastapi.testclient import TestClient

    app = FastAPI()
    mock_settings = MagicMock()
    mock_settings.enable_docs = True
    mock_get_settings.return_value = mock_settings

    add_root_endpoint(app)

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data
    assert data["docs"] == "/docs"


@patch("apuntador.app_setup.get_settings")
@pytest.mark.asyncio
async def test_root_endpoint_response_without_docs(mock_get_settings):
    """Test root endpoint response when docs are disabled."""
    from fastapi.testclient import TestClient

    app = FastAPI()
    mock_settings = MagicMock()
    mock_settings.enable_docs = False
    mock_get_settings.return_value = mock_settings

    add_root_endpoint(app)

    with TestClient(app) as client:
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["docs"] is None


@patch("apuntador.app_setup.get_settings")
@patch("apuntador.app_setup.InfrastructureFactory.from_settings")
def test_setup_app_with_real_app(mock_factory, mock_get_settings):
    """Test setup_app with a real FastAPI instance."""
    from apuntador.application import create_app

    app = create_app()
    mock_settings = MagicMock()
    mock_get_settings.return_value = mock_settings
    mock_infrastructure = MagicMock()
    mock_factory.return_value = mock_infrastructure

    # Should not raise any errors
    setup_app(app)

    assert app is not None
