"""Error response models following RFC 7807 Problem Details."""

from typing import Any

from pydantic import BaseModel, Field, model_validator

# RFC status code to section mapping (simplified for Apuntador)
status_to_section: dict[int, str] = {
    400: "6.5.1",
    401: "https://datatracker.ietf.org/doc/html/rfc7235#section-3.1",
    403: "6.5.3",
    404: "6.5.4",
    405: "6.5.5",
    422: "https://datatracker.ietf.org/doc/html/rfc4918#section-11.2",
    429: "https://datatracker.ietf.org/doc/html/rfc6585#section-4",
    500: "6.6.1",
    502: "6.6.3",
    503: "6.6.4",
}


def get_rfc_section_url(status: int) -> str:
    """Get the RFC section URL for a given HTTP status code.

    Args:
        status: The HTTP status code.

    Returns:
        The URL to the corresponding section in the RFC.
    """
    base_url = "https://datatracker.ietf.org/doc/html/rfc7231#section-"
    section = status_to_section.get(status)
    if section is None:
        return f"{base_url}6.6.1"  # Default to 500 Internal Server Error
    if section.startswith("https://"):
        return section
    return f"{base_url}{section}"


class ValidationErrorDetail(BaseModel):
    """Validation error detail for a specific field.

    Attributes:
        type: Error type (e.g., "value_error", "missing").
        loc: Location of the error in the request (e.g., ["body", "email"]).
        msg: Human-readable error message.
        input: The invalid input value that caused the error.
        ctx: Additional context about the error (optional).
        url: URL to error documentation (optional).
    """

    type: str = Field(..., description="Error type")
    loc: tuple[str, ...] = Field(..., description="Error location in request")
    msg: str = Field(..., description="Human-readable error message")
    input: Any = Field(..., description="Invalid input value")
    ctx: dict[str, Any] | None = Field(None, description="Additional error context")
    url: str | None = Field(None, description="Error documentation URL")


class ProblemDetail(BaseModel):
    """Problem Detail response as defined in RFC 7807.

    Provides standardized error responses across all API endpoints.

    Attributes:
        type: URI reference to the problem type (auto-generated from status).
        title: Short, human-readable summary of the problem type.
        status: HTTP status code.
        detail: Human-readable explanation specific to this occurrence.
        instance: URI reference identifying the specific occurrence.
        errors: List of validation errors (for 422 responses).

    Example:
        ```python
        problem = ProblemDetail(
            title="Validation Error",
            status=422,
            detail="Invalid OAuth provider specified",
            instance="/oauth/authorize/invalid",
            errors=[...]
        )
        ```
    """

    type: str | None = Field(
        default=None,
        description="URI reference to the problem type (RFC 7807)",
        json_schema_extra={
            "example": "https://datatracker.ietf.org/doc/html/rfc7231#section-6.5.1"
        },
    )
    title: str = Field(
        ...,
        description="Short, human-readable summary",
        json_schema_extra={"example": "Bad Request"},
    )
    status: int = Field(
        ...,
        description="HTTP status code",
        json_schema_extra={"example": 400},
    )
    detail: str | None = Field(
        default=None,
        description="Human-readable explanation",
        json_schema_extra={"example": "The request is missing required parameters"},
    )
    instance: str | None = Field(
        default=None,
        description="URI reference identifying this occurrence",
        json_schema_extra={"example": "/oauth/authorize/googledrive"},
    )
    errors: list[ValidationErrorDetail] | None = Field(
        default=None,
        description="Validation errors (for 422 responses)",
        json_schema_extra={
            "example": [
                {
                    "type": "value_error",
                    "loc": ["body", "code_challenge"],
                    "msg": "Field required",
                    "input": {},
                }
            ]
        },
    )

    @model_validator(mode="before")
    @classmethod
    def set_default_type(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Set the default type based on the status if not provided.

        Args:
            values: The model values.

        Returns:
            Updated values with type set.
        """
        if "type" not in values or values["type"] is None:
            status = values.get("status", 500)
            values["type"] = get_rfc_section_url(status)
        return values

    def add_extension(self, key: str, value: Any) -> None:
        """Add an extension field to the ProblemDetail.

        Args:
            key: Extension field name.
            value: Extension field value.
        """
        self.__setattr__(key, value)
