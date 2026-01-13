"""
mTLS (Mutual TLS) validation middleware.

Validates client certificates for physical devices (Android, iOS, Desktop).
Web clients are exempt from mTLS and use OAuth 2.0 + CORS instead.

Flow:
1. Extract client certificate from request headers (API Gateway style)
2. Parse and validate certificate
3. Check serial number against whitelist in repository
4. Verify certificate is not expired or revoked
5. Allow or deny request based on validation results
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from fastapi import Request, Response, status
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from apuntador.infrastructure import InfrastructureFactory


class MTLSValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate mTLS client certificates.

    Validates certificates for physical devices (Android, iOS, Desktop).
    Web clients bypass mTLS validation and use OAuth + CORS.

    Certificate validation steps:
    1. Extract certificate from headers (X-Client-Cert, X-SSL-Client-Cert)
    2. Parse X.509 certificate
    3. Check serial number is whitelisted
    4. Verify certificate is not expired
    5. Verify certificate is not revoked

    Attributes:
        infrastructure_factory: Factory for accessing certificate repository
        exempt_paths: URL paths exempt from mTLS validation
    """

    def __init__(self, app: Any, infrastructure_factory: InfrastructureFactory):
        """
        Initialize mTLS validation middleware.

        Args:
            app: FastAPI application
            infrastructure_factory: Factory for infrastructure repositories
        """
        super().__init__(app)
        self.infrastructure_factory = infrastructure_factory
        self.cert_repo = infrastructure_factory.get_certificate_repository()

        # Paths exempt from mTLS validation
        self.exempt_paths = {
            "/",
            "/health",
            "/health/public",  # Public health check (no mTLS)
            "/docs",
            "/redoc",
            "/openapi.json",
        }

        # Exempt prefixes (will match paths starting with these)
        self.exempt_prefixes = [
            "/oauth/",  # All OAuth endpoints (browser-based, no mTLS)
            "/config/",  # Configuration endpoints (used by web clients)
        ]

        # Exempt exact paths (won't match prefixes)
        self.exempt_exact = {
            "/device/enroll",  # Initial enrollment (no cert yet)
            "/device/ca-certificate",  # Public CA cert download
        }

        logger.info("Initialized MTLSValidationMiddleware")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and validate mTLS certificate.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response from next handler or 401/403 error
        """
        # Check if path is exempt from mTLS validation
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # Extract client certificate from headers
        cert_pem = self._extract_certificate(request)

        if not cert_pem:
            # No certificate provided - reject request
            logger.warning(
                f"mTLS validation failed: No client certificate provided "
                f"for {request.method} {request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "unauthorized",
                    "message": "Client certificate required for this endpoint",
                },
            )

        # Validate certificate
        validation_result = await self._validate_certificate(cert_pem)

        if not validation_result["valid"]:
            # Certificate validation failed
            logger.warning(
                f"mTLS validation failed: {validation_result['reason']} "
                f"for {request.method} {request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "forbidden", "message": validation_result["reason"]},
            )

        # Certificate is valid - attach metadata to request state
        request.state.mtls_validated = True
        request.state.device_id = validation_result.get("device_id")
        request.state.certificate_serial = validation_result.get("serial")

        logger.info(
            f"mTLS validation successful: device={validation_result.get('device_id')}, "
            f"serial={validation_result.get('serial')}"
        )

        # Continue to next handler
        return await call_next(request)

    def _is_exempt_path(self, path: str) -> bool:
        """
        Check if path is exempt from mTLS validation.

        Args:
            path: Request URL path

        Returns:
            True if path is exempt, False otherwise
        """
        # Check exact matches
        if path in self.exempt_paths or path in self.exempt_exact:
            return True

        # Check prefix matches (e.g., /oauth/*)
        for prefix in self.exempt_prefixes:
            if path.startswith(prefix):
                return True

        return False

    def _extract_certificate(self, request: Request) -> str | None:
        """
        Extract client certificate from request headers.

        Supports multiple header formats:
        - X-Client-Cert (AWS API Gateway, Cloudflare)
        - X-SSL-Client-Cert (Nginx)
        - X-Forwarded-Client-Cert (Envoy, Istio)

        Args:
            request: HTTP request

        Returns:
            PEM-encoded certificate or None
        """
        # Try X-Client-Cert and X-SSL-Client-Cert (direct PEM)
        for header in ["x-client-cert", "x-ssl-client-cert"]:
            cert_header = request.headers.get(header)
            if cert_header:
                # Decode URL-encoded certificate (AWS encodes newlines)
                cert_pem = cert_header.replace("%0A", "\n").replace("%20", " ")

                # Ensure proper PEM format (only add headers if missing)
                if not cert_pem.startswith("-----BEGIN CERTIFICATE-----"):
                    cert_pem = (
                        f"-----BEGIN CERTIFICATE-----\n{cert_pem}\n"
                        "-----END CERTIFICATE-----"
                    )

                logger.debug(
                    f"Extracted certificate from {header}: {cert_pem[:100]}..."
                )

                return cert_pem

        # Try X-Forwarded-Client-Cert (Envoy format: Cert="base64")
        xfcc_header = request.headers.get("x-forwarded-client-cert")
        if xfcc_header:
            # Envoy format: Cert="<base64-DER-cert>"
            import base64
            import re

            match = re.search(r'Cert="([^"]+)"', xfcc_header)
            if match:
                b64_cert = match.group(1)
                try:
                    # Decode base64 DER to PEM
                    der_cert = base64.b64decode(b64_cert)
                    cert = x509.load_der_x509_certificate(der_cert, default_backend())
                    pem_cert = cert.public_bytes(serialization.Encoding.PEM).decode(
                        "utf-8"
                    )
                    return pem_cert
                except Exception as e:
                    logger.error(f"Failed to decode Envoy certificate: {e}")
                    return None

        return None

    async def _validate_certificate(self, cert_pem: str) -> dict[str, Any]:
        """
        Validate client certificate.

        Validation checks:
        1. Parse certificate
        2. Check serial number is whitelisted
        3. Verify not expired
        4. Verify not revoked

        Args:
            cert_pem: PEM-encoded certificate

        Returns:
            Dict with validation result:
            - valid: bool
            - reason: str (if invalid)
            - device_id: str (if valid)
            - serial: str (if valid)
        """
        try:
            # Parse certificate
            cert = x509.load_pem_x509_certificate(
                cert_pem.encode("utf-8"), default_backend()
            )

            # Extract serial number (pad to 32 hex chars for 128-bit serials)
            serial = format(cert.serial_number, "032X")

            logger.debug(f"Certificate parsed successfully, serial={serial}")

            # Check if serial is whitelisted
            is_whitelisted = await self.cert_repo.is_serial_whitelisted(serial)

            logger.debug(f"Whitelist check for serial {serial}: {is_whitelisted}")

            if not is_whitelisted:
                return {
                    "valid": False,
                    "reason": f"Certificate serial {serial} not whitelisted",
                }

            # Get certificate details from repository
            # We need to find the certificate by serial to get device_id
            stored_cert = None
            for cert_data in await self.cert_repo.list_all_certificates():
                # Compare case-insensitive (serial can be upper or lower)
                if cert_data.serial.upper() == serial.upper():
                    stored_cert = cert_data
                    break

            if not stored_cert:
                return {
                    "valid": False,
                    "reason": f"Certificate serial {serial} not found in repository",
                }

            # Check if certificate is expired
            now = datetime.now(UTC).replace(tzinfo=None)
            # Use new cryptography API (not_valid_before_utc/not_valid_after_utc)
            # These return timezone-aware datetimes, so we convert to naive UTC
            not_before = cert.not_valid_before_utc.replace(tzinfo=None)
            not_after = cert.not_valid_after_utc.replace(tzinfo=None)

            if now < not_before:
                return {"valid": False, "reason": "Certificate not yet valid"}

            if now > not_after:
                return {"valid": False, "reason": "Certificate has expired"}

            # Check if certificate is revoked
            if stored_cert.revoked:
                return {"valid": False, "reason": "Certificate has been revoked"}

            # Certificate is valid
            return {
                "valid": True,
                "device_id": stored_cert.device_id,
                "serial": serial,
                "platform": stored_cert.platform,
            }

        except Exception as e:
            logger.error(f"Certificate validation error: {e}")
            return {
                "valid": False,
                "reason": f"Certificate validation failed: {str(e)}",
            }
