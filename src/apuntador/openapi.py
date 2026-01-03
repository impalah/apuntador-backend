"""OpenAPI schema customization for Apuntador Backend API."""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Generate customized OpenAPI schema for the API.

    Args:
        app: The FastAPI application instance.

    Returns:
        Customized OpenAPI schema dictionary.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Apuntador Backend API",
        version=app.version,
        description="""
# Apuntador Backend API

OAuth proxy and mTLS authentication backend for the Apuntador teleprompter application.

## Features

- **OAuth 2.0 with PKCE**: Secure authentication for Google Drive and Dropbox
- **mTLS Authentication**: Client certificate authentication with HSM support
- **Device Enrollment**: Automated certificate signing and renewal
- **Device Attestation**: Hardware-backed key verification (SafetyNet, DeviceCheck)
- **Short-lived Certificates**: 7-30 day certificate validity with auto-renewal

## Authentication

### OAuth Flow (Google Drive, Dropbox)

1. **Authorization**: Request authorization URL with PKCE challenge
2. **Callback**: Exchange authorization code for access/refresh tokens
3. **Refresh**: Renew expired access tokens
4. **Revoke**: Invalidate tokens when needed

### mTLS Device Enrollment

1. **Generate Key Pair**: Client generates key pair (in HSM if mobile)
2. **Create CSR**: Client creates Certificate Signing Request
3. **Enroll Device**: Backend validates attestation and signs CSR
4. **Store Certificate**: Client stores certificate with private key
5. **Auto-renewal**: Certificate renews automatically before expiration

## API Endpoints

### Health Check
- `GET /health` - Basic health check
- `GET /health/public` - Public health check (no mTLS)

### OAuth
- `POST /oauth/authorize/{provider}` - Get authorization URL
- `GET /oauth/callback/{provider}` - OAuth callback endpoint
- `POST /oauth/token/refresh/{provider}` - Refresh access token
- `POST /oauth/token/revoke/{provider}` - Revoke access token

### Device Enrollment (mTLS)
- `POST /device/enroll` - Enroll new device with CSR
- `POST /device/renew` - Renew device certificate
- `POST /device/revoke` - Revoke device certificate
- `GET /device/status/{device_id}` - Get certificate status
- `GET /device/ca-certificate` - Get CA certificate for pinning

### Device Attestation
- `POST /device/attest/android` - Verify Android SafetyNet
- `POST /device/attest/ios` - Verify iOS DeviceCheck
- `POST /device/attest/desktop` - Verify desktop device
- `POST /device/attest/clear-cache` - Clear attestation cache

## Security

- **PKCE**: Required for all OAuth flows (no client secrets)
- **State Parameter**: CSRF protection via signed state tokens
- **Certificate Pinning**: CA certificate available for client pinning
- **Hardware Security**: HSM/TEE/Secure Enclave support for mobile devices
- **Short-lived Certificates**: Minimizes impact of certificate compromise

## Error Handling

All errors follow
[RFC 7807 Problem Details](https://datatracker.ietf.org/doc/html/rfc7807)
format:

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc7231#section-6.5.1",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more validation errors occurred (2 errors).",
  "instance": "/oauth/authorize/googledrive",
  "errors": [
    {
      "type": "missing",
      "loc": ["body", "code_challenge"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

## Platform Support

- **Web**: OAuth 2.0 + PKCE (no mTLS)
- **Android**: mTLS with Android Keystore (TEE/StrongBox)
- **iOS**: mTLS with Secure Enclave
- **Desktop**: mTLS with encrypted file storage
        """,
        routes=app.routes,
        contact={
            "name": "Apuntador Team",
            "url": "https://github.com/impalah/apuntador",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    # Add custom tags metadata
    openapi_schema["tags"] = [
        {
            "name": "Health",
            "description": "Health check endpoints for monitoring",
        },
        {
            "name": "OAuth",
            "description": (
                "OAuth 2.0 authentication with PKCE "
                "for cloud storage providers"
            ),
        },
        {
            "name": "Device Enrollment",
            "description": "mTLS certificate enrollment, renewal, and revocation",
        },
        {
            "name": "Device Attestation",
            "description": (
                "Hardware-backed device verification "
                "(SafetyNet, DeviceCheck)"
            ),
        },
    ]

    # Ensure components exists before adding security schemes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "mTLS": {
            "type": "mutualTLS",
            "description": "Client certificate authentication (Android, iOS, Desktop)",
        },
        "OAuth2": {
            "type": "oauth2",
            "description": "OAuth 2.0 with PKCE (Web browsers)",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "/oauth/authorize/{provider}",
                    "tokenUrl": "/oauth/callback/{provider}",
                    "refreshUrl": "/oauth/token/refresh/{provider}",
                    "scopes": {
                        "drive.file": "Google Drive file access",
                        "files.content.read": "Dropbox file read access",
                        "files.content.write": "Dropbox file write access",
                    },
                }
            },
        },
    }

    # Add error response schemas to components
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    # Add ProblemDetail schema
    openapi_schema["components"]["schemas"]["ProblemDetail"] = {
        "type": "object",
        "title": "ProblemDetail",
        "description": "RFC 7807 Problem Details for HTTP APIs",
        "required": ["title", "status"],
        "properties": {
            "type": {
                "type": "string",
                "description": "URI reference to the problem type",
                "example": "https://datatracker.ietf.org/doc/html/rfc7231#section-6.5.1",
            },
            "title": {
                "type": "string",
                "description": "Short, human-readable summary",
                "example": "Bad Request",
            },
            "status": {
                "type": "integer",
                "description": "HTTP status code",
                "example": 400,
            },
            "detail": {
                "type": "string",
                "description": (
                    "Human-readable explanation specific to this occurrence"
                ),
                "example": (
                    "The request could not be understood due to "
                    "malformed syntax."
                ),
            },
            "instance": {
                "type": "string",
                "description": "URI reference identifying the specific occurrence",
                "example": "/oauth/authorize/googledrive",
            },
            "errors": {
                "type": "array",
                "description": "List of validation errors (for 422 responses)",
                "items": {"$ref": "#/components/schemas/ValidationErrorDetail"},
            },
        },
    }

    # Add ValidationErrorDetail schema
    openapi_schema["components"]["schemas"]["ValidationErrorDetail"] = {
        "type": "object",
        "title": "ValidationErrorDetail",
        "description": "Validation error detail for a specific field",
        "required": ["type", "loc", "msg", "input"],
        "properties": {
            "type": {
                "type": "string",
                "description": "Error type",
                "example": "missing",
            },
            "loc": {
                "type": "array",
                "description": "Error location in request",
                "items": {"type": "string"},
                "example": ["body", "code_challenge"],
            },
            "msg": {
                "type": "string",
                "description": "Human-readable error message",
                "example": "Field required",
            },
            "input": {
                "description": "Invalid input value",
                "example": {},
            },
            "ctx": {
                "type": "object",
                "description": "Additional error context",
                "additionalProperties": True,
            },
            "url": {
                "type": "string",
                "description": "Error documentation URL",
            },
        },
    }

    # Add RFC 7807 error response to all endpoints
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            if isinstance(operation, dict) and "responses" in operation:
                operation["responses"]["422"] = {
                    "description": "Validation Error",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ProblemDetail"}
                        }
                    },
                }
                operation["responses"]["500"] = {
                    "description": "Internal Server Error",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ProblemDetail"}
                        }
                    },
                }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def configure_openapi(app: FastAPI) -> None:
    """Configure the FastAPI app to use custom OpenAPI schema.

    Args:
        app: The FastAPI application instance.
    """
    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]
