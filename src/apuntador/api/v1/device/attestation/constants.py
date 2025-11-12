"""Shared constants for device attestation module."""

# Error messages
INTERNAL_SERVER_ERROR_ATTESTATION = (
    "Internal server error during attestation verification"
)

# Device ID validation
DEVICE_ID_DESCRIPTION = "Unique device identifier"
DEVICE_ID_PATTERN = r"^[a-zA-Z0-9_-]{8,64}$"

# Verification status descriptions
VERIFICATION_STATUS_DESCRIPTION = "Verification status (valid/invalid/failed)"
DEVICE_IDENTIFIER_DESCRIPTION = "Device identifier"
VERIFICATION_TIMESTAMP_DESCRIPTION = "Verification timestamp"
ERROR_MESSAGE_DESCRIPTION = "Error message if verification failed"
