"""Health check response models."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="ok", description="Service status")
    version: str = Field(..., description="Backend version")
    message: str | None = Field(None, description="Optional status message")
