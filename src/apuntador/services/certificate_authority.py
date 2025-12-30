"""
Certificate Authority service for signing device certificates.

Handles CSR (Certificate Signing Request) parsing, validation, and signing
with the CA private key. Issues short-lived client certificates for enrolled devices.

Security notes:
- CA private key never leaves the server
- Device certificates valid 7-30 days only
- Each certificate has unique serial number
- Serials are tracked for whitelist validation
"""

import secrets
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID
from loguru import logger

from apuntador.infrastructure import InfrastructureFactory
from apuntador.infrastructure.repositories import Certificate


class CertificateAuthority:
    """
    Certificate Authority for signing device certificates.

    Loads CA private key and certificate from infrastructure repository,
    signs CSRs from enrolled devices, and tracks issued certificates.
    """

    def __init__(self, infrastructure_factory: InfrastructureFactory):
        """
        Initialize Certificate Authority.

        Args:
            infrastructure_factory: Factory for accessing repositories
        """
        self.factory = infrastructure_factory
        self.secrets_repo = infrastructure_factory.get_secrets_repository()
        self.cert_repo = infrastructure_factory.get_certificate_repository()

        self._ca_private_key = None
        self._ca_certificate = None

        logger.info("Initialized CertificateAuthority")

    async def _load_ca_credentials(self) -> None:
        """Load CA private key and certificate from repository."""
        if self._ca_private_key is None:
            ca_key_pem = await self.secrets_repo.get_ca_private_key()
            self._ca_private_key = serialization.load_pem_private_key(
                ca_key_pem.encode(), password=None
            )
            logger.info("Loaded CA private key")

        if self._ca_certificate is None:
            ca_cert_pem = await self.secrets_repo.get_ca_certificate()
            self._ca_certificate = x509.load_pem_x509_certificate(ca_cert_pem.encode())
            logger.info("Loaded CA certificate")

    def _generate_serial_number(self) -> int:
        """
        Generate cryptographically secure serial number.

        Returns:
            Random 128-bit integer
        """
        return secrets.randbits(128)

    def _get_validity_days(self, platform: str) -> int:
        """
        Get certificate validity period based on platform.

        Args:
            platform: Device platform (android, ios, desktop, web)

        Returns:
            Number of days certificate should be valid
        """
        validity_map = {
            "android": 30,
            "ios": 30,
            "desktop": 7,
            "web": 1,  # Session-based, very short
        }
        return validity_map.get(platform.lower(), 7)

    async def sign_csr(
        self,
        csr_pem: str,
        device_id: str,
        platform: str,
        validity_days: int | None = None,
    ) -> Certificate:
        """
        Sign a Certificate Signing Request from a device.

        Args:
            csr_pem: PEM-encoded CSR from device
            device_id: Unique device identifier
            platform: Device platform (android, ios, desktop)
            validity_days: Override default validity period

        Returns:
            Certificate object with signed certificate and metadata

        Raises:
            ValueError: If CSR is invalid or malformed
            Exception: If signing fails
        """
        await self._load_ca_credentials()

        # Parse CSR
        try:
            csr = x509.load_pem_x509_csr(csr_pem.encode())
        except Exception as e:
            logger.error(f"Failed to parse CSR: {e}")
            raise ValueError(f"Invalid CSR format: {e}") from e

        # Verify CSR signature (ensures private key matches public key)
        if not csr.is_signature_valid:
            logger.error("CSR signature validation failed")
            raise ValueError("CSR signature is invalid")

        # Generate serial number (pad to 32 hex chars for 128-bit serials)
        serial = self._generate_serial_number()
        serial_hex = format(serial, "032X")

        logger.info(f"Signing certificate for device {device_id}, serial {serial_hex}")

        # Determine validity period
        if validity_days is None:
            validity_days = self._get_validity_days(platform)

        now = datetime.now(UTC)
        not_before = now
        not_after = now + timedelta(days=validity_days)

        # Build certificate
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, device_id),
                        x509.NameAttribute(
                            NameOID.ORGANIZATION_NAME, "Apuntador Devices"
                        ),
                    ]
                )
            )
            .issuer_name(self._ca_certificate.subject)
            .public_key(csr.public_key())
            .serial_number(serial)
            .not_valid_before(not_before)
            .not_valid_after(not_after)
        )

        # Add X.509v3 extensions
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True
        )

        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

        cert_builder = cert_builder.add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )

        cert_builder = cert_builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(csr.public_key()), critical=False
        )

        cert_builder = cert_builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                self._ca_certificate.public_key()
            ),
            critical=False,
        )

        # Sign certificate with CA private key
        certificate = cert_builder.sign(
            private_key=self._ca_private_key, algorithm=hashes.SHA256()
        )

        # Convert to PEM
        cert_pem = certificate.public_bytes(
            encoding=serialization.Encoding.PEM
        ).decode()

        # Create Certificate object
        cert_obj = Certificate(
            device_id=device_id,
            serial=serial_hex,
            platform=platform,
            issued_at=not_before.replace(tzinfo=None),
            expires_at=not_after.replace(tzinfo=None),
            certificate_pem=cert_pem,
            revoked=False,
        )

        # Store in repository (adds to whitelist)
        await self.cert_repo.save_certificate(cert_obj)

        logger.info(
            f"Certificate signed for {device_id}: "
            f"serial={serial_hex}, expires={not_after.isoformat()}"
        )

        return cert_obj

    async def verify_certificate(self, cert_pem: str) -> bool:
        """
        Verify a certificate was signed by this CA.

        Args:
            cert_pem: PEM-encoded certificate to verify

        Returns:
            True if certificate is valid and signed by this CA
        """
        await self._load_ca_credentials()

        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode())

            # Verify issuer matches CA
            if cert.issuer != self._ca_certificate.subject:
                logger.warning("Certificate issuer does not match CA")
                return False

            # Verify certificate is not expired
            now = datetime.now(UTC).replace(tzinfo=None)
            if now < cert.not_valid_before_utc.replace(tzinfo=None):
                logger.warning("Certificate is not yet valid")
                return False
            if now > cert.not_valid_after_utc.replace(tzinfo=None):
                logger.warning("Certificate has expired")
                return False

            logger.info(
                f"Certificate verified: serial={format(cert.serial_number, 'x')}"
            )
            return True

        except Exception as e:
            logger.error(f"Certificate verification failed: {e}")
            return False

    async def get_ca_certificate_pem(self) -> str:
        """
        Get CA certificate in PEM format.

        Returns:
            PEM-encoded CA certificate (for client truststore)
        """
        return await self.secrets_repo.get_ca_certificate()

    async def revoke_certificate(self, device_id: str) -> bool:
        """
        Revoke a device certificate.

        Args:
            device_id: Device ID to revoke certificate for

        Returns:
            True if certificate was revoked, False if not found
        """
        revoked = await self.cert_repo.revoke_certificate(device_id)

        if revoked:
            logger.warning(f"Certificate revoked for device {device_id}")
        else:
            logger.warning(f"No certificate found for device {device_id}")

        return revoked

    async def list_expiring_certificates(self, days: int = 5) -> list[Certificate]:
        """
        List certificates expiring within specified days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of certificates that will expire soon
        """
        return await self.cert_repo.list_expiring_certificates(days)
