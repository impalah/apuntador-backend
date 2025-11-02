"""
API v1 endpoints.

Route prefix constants for consistent API versioning.
"""

# Base API prefix for all v1 endpoints
API_V1_PREFIX: str = "/api"

# Module-specific prefixes
OAUTH_PREFIX: str = f"{API_V1_PREFIX}/oauth"
DEVICE_PREFIX: str = f"{API_V1_PREFIX}/device"
DEVICE_ATTESTATION_PREFIX: str = f"{DEVICE_PREFIX}/attest"

__all__ = [
    "API_V1_PREFIX",
    "OAUTH_PREFIX",
    "DEVICE_PREFIX",
    "DEVICE_ATTESTATION_PREFIX",
]
