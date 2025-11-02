"""OAuth Response Models."""

from pydantic import BaseModel, Field


class OAuthAuthorizeResponse(BaseModel):
    """Response with authorization URL."""

    authorization_url: str = Field(..., description="OAuth authorization URL")
    state: str = Field(..., description="State for validation")


class OAuthTokenResponse(BaseModel):
    """Response with access tokens."""

    access_token: str = Field(..., description="Access token")
    refresh_token: str | None = Field(None, description="Refresh token")
    expires_in: int = Field(..., description="Expiration time in seconds")
    token_type: str = Field(default="Bearer", description="Token type")


class OAuthRevokeResponse(BaseModel):
    """Token revocation response."""

    success: bool = Field(..., description="Whether revocation was successful")
    message: str | None = Field(None, description="Optional message")
