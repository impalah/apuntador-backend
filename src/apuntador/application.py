"""
FastAPI application factory.

Creates and configures the FastAPI application with all middleware,
routers, and exception handlers.
"""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from apuntador import __version__
from apuntador.config import get_settings
from apuntador.core.logging import logger
from apuntador.exception_handlers import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from apuntador.lifespan import lifespan
from apuntador.middleware import TraceIDMiddleware
from apuntador.openapi import configure_openapi
from apuntador.routes import register_routes


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    # Configure docs URLs based on settings
    # Must be set BEFORE creating FastAPI instance
    docs_url = "/docs" if settings.enable_docs else None
    redoc_url = "/redoc" if settings.enable_docs else None
    openapi_url = "/openapi.json" if settings.enable_docs else None

    app = FastAPI(
        title="Apuntador Backend",
        description="OAuth proxy and mTLS authentication backend for Apuntador",
        version=__version__,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    # Register exception handlers (RFC 7807 Problem Details)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Add middleware
    app.add_middleware(TraceIDMiddleware)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins(),  # Use helper method to get list
        allow_credentials=True,
        allow_methods=settings.get_cors_allowed_methods(),
        allow_headers=settings.get_cors_allowed_headers(),
    )

    # Register routes
    register_routes(app)

    # Configure custom OpenAPI schema
    configure_openapi(app)

    logger.info(f" FastAPI application created (v{__version__})")
    logger.info(" Exception handlers registered (RFC 7807 Problem Details)")
    logger.info(" OpenAPI documentation customized")
    logger.info(f"CORS origins: {settings.get_allowed_origins()}")

    return app
