"""
API v1 endpoints.

Route prefix constants for consistent API versioning.
"""

# Base API prefix - removed "/api" since domain is already api.apuntador.io
API_V1_PREFIX: str = ""

# Module-specific prefixes
OAUTH_PREFIX: str = f"{API_V1_PREFIX}/oauth"
DEVICE_PREFIX: str = f"{API_V1_PREFIX}/device"
DEVICE_ATTESTATION_PREFIX: str = f"{DEVICE_PREFIX}/attest"
CONFIG_PREFIX: str = f"{API_V1_PREFIX}/config"

__all__ = [
    "API_V1_PREFIX",
    "OAUTH_PREFIX",
    "DEVICE_PREFIX",
    "DEVICE_ATTESTATION_PREFIX",
    "CONFIG_PREFIX",
]
