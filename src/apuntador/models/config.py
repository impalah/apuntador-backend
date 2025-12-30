"""
Configuration models for API responses.

These models define the structure of configuration data
returned to clients (web, mobile, desktop).
"""

from pydantic import BaseModel, ConfigDict, Field


class ProviderInfo(BaseModel):
    """
    Information about a single cloud provider.

    Attributes:
        enabled: Whether the provider is enabled on the backend.
        requires_mtls: Whether the provider requires mTLS authentication
                      (True for mobile/desktop, False for web).
    """

    enabled: bool = Field(description="Whether this provider is enabled on the backend")
    requires_mtls: bool = Field(
        default=True,
        description=(
            "Whether this provider requires mTLS authentication "
            "(True for mobile/desktop, False for web)"
        ),
    )


class CloudProviderConfig(BaseModel):
    """
    Cloud provider configuration response.

    This response tells clients which cloud providers are available
    and their configuration (mTLS requirements, etc.).

    Attributes:
        providers: Dictionary mapping provider IDs to their configuration.
        version: Backend API version.
        cache_ttl: Recommended cache time-to-live in seconds.

    Example:
        {
            "providers": {
                "googledrive": {"enabled": true, "requires_mtls": true},
                "dropbox": {"enabled": false, "requires_mtls": true}
            },
            "version": "1.0.0",
            "cache_ttl": 3600
        }
    """

    providers: dict[str, ProviderInfo] = Field(
        description="Dictionary of provider configurations"
    )
    version: str = Field(description="Backend API version")
    cache_ttl: int = Field(
        default=3600, description="Recommended cache TTL in seconds (1 hour)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "providers": {
                    "googledrive": {"enabled": True, "requires_mtls": True},
                    "dropbox": {"enabled": True, "requires_mtls": True},
                    "onedrive": {"enabled": False, "requires_mtls": True},
                },
                "version": "1.0.0",
                "cache_ttl": 3600,
            }
        }
    )
