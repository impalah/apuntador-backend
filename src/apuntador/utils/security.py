"""
Security utilities for token signing and OAuth state management.

Provides cryptographically secure functions for:
- Generating random state parameters for OAuth flows
- Signing data with timestamps for tamper detection
- Verifying signed data with expiration checking
"""

import secrets
from typing import Any

from itsdangerous import BadSignature, URLSafeTimedSerializer

from apuntador.config import get_settings


def generate_state() -> str:
    """
    Generate a cryptographically secure random state for OAuth.

    Returns:
        str: URL-safe random string (256 bits of entropy)
    """
    return secrets.token_urlsafe(32)


def create_serializer() -> URLSafeTimedSerializer:
    """
    Create a URLSafeTimedSerializer with the application secret key.

    Returns:
        URLSafeTimedSerializer: Configured serializer for signing/verifying data
    """
    settings = get_settings()
    return URLSafeTimedSerializer(settings.secret_key)


def sign_data(data: dict[str, Any], max_age: int = 600) -> str:
    """
    Sign data with timestamp for tamper detection.

    Creates a signed token that includes the data and a timestamp,
    ensuring data integrity and freshness. The token can only be
    verified if it hasn't been tampered with and hasn't expired.

    Args:
        data: Dictionary to sign (will be JSON-serialized)
        max_age: Maximum validity time in seconds (default: 600 = 10 minutes)

    Returns:
        str: Signed token (URL-safe base64 string)

    Example:
        >>> token = sign_data({"user_id": 123, "action": "login"})
        >>> # Token can be verified within 10 minutes
    """
    serializer = create_serializer()
    return serializer.dumps(data)


def verify_signed_data(token: str, max_age: int = 600) -> dict[str, Any] | None:
    """
    Verify and deserialize signed data.

    Checks the signature and timestamp of a signed token. Returns
    None if the token has been tampered with or has expired.

    Args:
        token: Signed token from sign_data()
        max_age: Maximum validity time in seconds (default: 600 = 10 minutes)

    Returns:
        dict | None: Deserialized data if valid, None if signature invalid or expired

    Example:
        >>> data = verify_signed_data(token)
        >>> if data:
        >>>     print(f"Valid data: {data}")
        >>> else:
        >>>     print("Invalid or expired token")
    """
    serializer = create_serializer()
    try:
        data: dict[str, Any] = serializer.loads(token, max_age=max_age)
        return data
    except BadSignature:
        return None
