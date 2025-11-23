"""Tests for OpenAPI schema customization."""

from fastapi import FastAPI

from apuntador.openapi import custom_openapi


def test_custom_openapi_generates_schema():
    """Test that custom_openapi generates a valid OpenAPI schema."""
    app = FastAPI(version="1.0.0")

    # Add a sample endpoint to ensure paths exist
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    schema = custom_openapi(app)

    assert schema is not None
    assert isinstance(schema, dict)
    assert "openapi" in schema
    assert "info" in schema


def test_custom_openapi_caches_schema():
    """Test that custom_openapi caches the schema after first generation."""
    app = FastAPI(version="1.0.0")

    # Add a sample endpoint
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    # First call
    schema1 = custom_openapi(app)

    # Second call should return cached version
    schema2 = custom_openapi(app)

    # Should be the same object (cached)
    assert schema1 is schema2


def test_custom_openapi_returns_existing_schema():
    """Test that custom_openapi returns existing schema if already set."""
    app = FastAPI()
    existing_schema = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
    }
    app.openapi_schema = existing_schema

    schema = custom_openapi(app)

    # Should return the existing schema without modification
    assert schema is existing_schema


def test_custom_openapi_adds_error_responses():
    """Test that custom_openapi adds 422 and 500 error responses to endpoints."""
    app = FastAPI(version="1.0.0")

    # Add an endpoint with responses to trigger error response addition
    @app.get("/test", responses={200: {"description": "Success"}})
    async def test_endpoint():
        return {"message": "test"}

    schema = custom_openapi(app)

    # Check that paths exist and error responses were added
    assert "paths" in schema
    assert "/test" in schema["paths"]

    test_path = schema["paths"]["/test"]
    assert "get" in test_path

    responses = test_path["get"]["responses"]
    assert "422" in responses
    assert "500" in responses
    assert responses["422"]["description"] == "Validation Error"
    assert responses["500"]["description"] == "Internal Server Error"
