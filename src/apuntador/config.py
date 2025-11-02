"""
Application configuration and environment variables.

This module unifies configuration using pydantic-settings.
Variables can come from:
1. .env file
2. System environment variables (have priority)
3. Default values

Naming convention:
- In Python code: snake_case (google_client_id)
- In .env or ENV vars: UPPER_CASE (GOOGLE_CLIENT_ID)
- Pydantic automatically converts between both
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Unified application configuration.

    All variables can be defined in:
    - .env file: VARIABLE_NAME=value
    - Environment variables: export VARIABLE_NAME=value

    Example:
        # In .env or as environment variable:
        PROJECT_NAME=Apuntador Backend
        DEBUG=true
        LOG_LEVEL=INFO
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # Allows using uppercase or lowercase
        extra="ignore",  # Ignores extra variables in .env
    )

    # ============================================================================
    # PROJECT SETTINGS
    # ============================================================================
    project_name: str = Field(
        default="Apuntador OAuth Backend", description="Project name"
    )
    project_description: str = Field(
        default="Unified backend for OAuth 2.0 with multiple cloud providers",
        description="Project description",
    )
    project_version: str = Field(default="1.0.0", description="Project version")

    # ============================================================================
    # SERVER SETTINGS
    # ============================================================================
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    enable_docs: bool = Field(
        default=False, description="Enable API documentation (Swagger/ReDoc)"
    )
    secret_key: str = Field(
        default="dev-secret-key-change-in-production-min-32-chars",
        description="Secret key for signing tokens (must be 32+ chars in production)",
    )

    # ============================================================================
    # LOGGING SETTINGS
    # ============================================================================
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    log_format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | trace_id={extra[trace_id]} | {name}:{function}:{line} - {message}",  # noqa: E501
        description="Log format",
    )
    logger_name: str = Field(default="apuntador", description="Logger name")
    logger_enqueue: bool = Field(
        default=False, description="Enqueue logs using multiprocessing"
    )

    # ============================================================================
    # CORS SETTINGS
    # ============================================================================
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,capacitor://localhost,tauri://localhost",
        description="Allowed origins for CORS (comma-separated)",
    )
    cors_allowed_methods: str = Field(
        default="GET,POST,OPTIONS", description="Allowed HTTP methods for CORS"
    )
    cors_allowed_headers: str = Field(
        default="Content-Type,Authorization,X-Client-Cert,X-Device-ID",
        description="Allowed headers for CORS",
    )

    # ============================================================================
    # DATABASE SETTINGS (for future use)
    # ============================================================================
    initialize_database: bool = Field(
        default=True, description="Initialize database on startup"
    )
    healthcheck_database: bool = Field(
        default=False,
        description="Include database verification in health check",
    )

    # ============================================================================
    # INFRASTRUCTURE SETTINGS (mTLS Certificate Management)
    # ============================================================================
    infrastructure_provider: str = Field(
        default="local",
        description="Infrastructure provider (local, aws, azure)",
    )
    infrastructure_base_dir: str = Field(
        default="./.credentials",
        description="Base directory for local infrastructure storage (credentials, CA keys, etc.)",
    )

    # AWS Infrastructure Configuration
    aws_region: str = Field(default="eu-west-1", description="AWS region")
    aws_dynamodb_table: str = Field(
        default="apuntador-certificates",
        description="DynamoDB table name for certificate metadata",
    )
    aws_s3_bucket: str = Field(
        default="apuntador-cert-storage",
        description="S3 bucket name for certificate storage",
    )
    aws_secrets_prefix: str = Field(
        default="apuntador",
        description="Prefix for secrets in AWS Secrets Manager",
    )
    auto_create_resources: bool = Field(
        default=False,
        description="Auto-create AWS resources (DynamoDB table, S3 bucket) if missing",
    )

    # ============================================================================
    # AUTH SETTINGS (for future use with AWS Cognito)
    # ============================================================================
    user_pool_id: str = Field(default="", description="Cognito User Pool ID")
    token_verification_disabled: bool = Field(
        default=False,
        description="Disable token verification (development only)",
    )

    # ============================================================================
    # OBSERVABILITY SETTINGS (OpenTelemetry)
    # ============================================================================
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry")
    otel_service_name: str = Field(
        default="apuntador-backend",
        description="Service name for OpenTelemetry",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="http://otel-collector:4317",
        description="OpenTelemetry collector endpoint",
    )

    # ============================================================================
    # OAUTH PROVIDERS SETTINGS
    # ============================================================================

    # Google Drive OAuth
    google_client_id: str = Field(default="", description="Google OAuth Client ID")
    google_client_secret: str = Field(
        default="", description="Google OAuth Client Secret"
    )
    google_redirect_uri: str = Field(
        default="https://apuntador.ngrok.app/api/oauth/callback/googledrive",
        description="Google OAuth Redirect URI",
    )

    # Dropbox OAuth
    dropbox_client_id: str = Field(default="", description="Dropbox OAuth Client ID")
    dropbox_client_secret: str = Field(
        default="", description="Dropbox OAuth Client Secret"
    )
    dropbox_redirect_uri: str = Field(
        default="https://apuntador.ngrok.app/api/oauth/callback/dropbox",
        description="Dropbox OAuth Redirect URI",
    )

    # OneDrive OAuth (optional)
    onedrive_client_id: str = Field(default="", description="OneDrive OAuth Client ID")
    onedrive_client_secret: str = Field(
        default="", description="OneDrive OAuth Client Secret"
    )
    onedrive_redirect_uri: str = Field(
        default="https://apuntador.ngrok.app/api/oauth/callback/onedrive",
        description="OneDrive OAuth Redirect URI",
    )

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def get_allowed_origins(self) -> list[str]:
        """
        Get list of allowed origins for CORS.

        Returns:
            list[str]: List of allowed origin URLs.
        """
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    def get_cors_allowed_methods(self) -> list[str]:
        """
        Get list of allowed HTTP methods for CORS.

        Returns:
            list[str]: List of allowed HTTP methods. Returns ["*"] if all methods are allowed.
        """
        if self.cors_allowed_methods == "*":
            return ["*"]
        return [method.strip() for method in self.cors_allowed_methods.split(",")]

    def get_cors_allowed_headers(self) -> list[str]:
        """
        Get list of allowed headers for CORS.

        Returns:
            list[str]: List of allowed headers. Returns ["*"] if all headers are allowed.
        """
        if self.cors_allowed_headers == "*":
            return ["*"]
        return [header.strip() for header in self.cors_allowed_headers.split(",")]


# ============================================================================
# SINGLETON PATTERN - Global settings instance
# ============================================================================


@lru_cache
def get_settings() -> Settings:
    """
    Get application settings (LRU cached).

    This function is cached, so the .env file is only read once.
    To refresh the configuration, clear the cache:
        get_settings.cache_clear()

    Usage:
        # In FastAPI endpoints (dependency injection):
        def my_endpoint(settings: Settings = Depends(get_settings)):
            print(settings.project_name)

        # In normal code (outside FastAPI):
        from apuntador.config import get_settings
        settings = get_settings()
        print(settings.project_name)

    Returns:
        Settings: Application configuration instance.
    """
    return Settings()


# Create global instance for use outside FastAPI
# This is the recommended way to access settings in non-endpoint modules
settings = get_settings()
