"""
Local file-based certificate repository implementation.

Stores certificates as JSON files in a local directory structure:
    {base_dir}/
        certificates/
            {device_id}.json
        serials/
            {serial}.json (symlink to device_id)
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from apuntador.infrastructure.repositories.certificate_repository import (
    Certificate,
    CertificateRepository,
)


class LocalCertificateRepository(CertificateRepository):
    """
    File-based certificate storage for local development.

    Thread-safe via file system atomic writes.
    """

    def __init__(self, base_dir: str = "./.local_infrastructure/certificates"):
        """
        Initialize local certificate repository.

        Args:
            base_dir: Base directory for certificate storage
        """
        self.base_dir = Path(base_dir)
        self.certs_dir = self.base_dir / "certificates"
        self.serials_dir = self.base_dir / "serials"

        # Create directories if they don't exist
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        self.serials_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized LocalCertificateRepository at {self.base_dir}")

    def _cert_path(self, device_id: str) -> Path:
        """Get path to certificate file."""
        return self.certs_dir / f"{device_id}.json"

    def _serial_path(self, serial: str) -> Path:
        """Get path to serial index file."""
        return self.serials_dir / f"{serial}.json"

    def _cert_to_dict(self, cert: Certificate) -> dict[str, Any]:
        """Convert Certificate to JSON-serializable dict."""
        return {
            "device_id": cert.device_id,
            "serial": cert.serial,
            "platform": cert.platform,
            "issued_at": cert.issued_at.isoformat(),
            "expires_at": cert.expires_at.isoformat(),
            "certificate_pem": cert.certificate_pem,
            "revoked": cert.revoked,
        }

    def _dict_to_cert(self, data: dict[str, Any]) -> Certificate:
        """Convert dict to Certificate."""
        return Certificate(
            device_id=data["device_id"],
            serial=data["serial"],
            platform=data["platform"],
            issued_at=datetime.fromisoformat(data["issued_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            certificate_pem=data["certificate_pem"],
            revoked=data.get("revoked", False),
        )

    async def save_certificate(self, certificate: Certificate) -> None:
        """Store certificate to file."""
        cert_path = self._cert_path(certificate.device_id)
        serial_path = self._serial_path(certificate.serial)

        # Write certificate file
        cert_path.write_text(json.dumps(self._cert_to_dict(certificate), indent=2))

        # Write serial index (contains device_id for lookup)
        serial_path.write_text(
            json.dumps({"device_id": certificate.device_id}, indent=2)
        )

        logger.info(
            f"Saved certificate for device {certificate.device_id}, "
            f"serial {certificate.serial}"
        )

    async def get_certificate(self, device_id: str) -> Certificate | None:
        """Retrieve certificate by device ID."""
        cert_path = self._cert_path(device_id)

        if not cert_path.exists():
            return None

        data = json.loads(cert_path.read_text())
        return self._dict_to_cert(data)

    async def is_serial_whitelisted(self, serial: str) -> bool:
        """Check if serial is whitelisted and not revoked."""
        serial_path = self._serial_path(serial)

        if not serial_path.exists():
            return False

        # Get device_id from serial index
        serial_data = json.loads(serial_path.read_text())
        device_id = serial_data["device_id"]

        # Check if certificate is revoked
        cert = await self.get_certificate(device_id)
        if cert is None or cert.revoked:
            return False

        # Check if certificate is expired
        if cert.expires_at < datetime.now(UTC).replace(tzinfo=None):
            logger.warning(f"Certificate {serial} is expired")
            return False

        return True

    async def revoke_certificate(self, device_id: str) -> bool:
        """Revoke a device certificate."""
        cert = await self.get_certificate(device_id)

        if cert is None:
            return False

        cert.revoked = True
        await self.save_certificate(cert)

        logger.info(f"Revoked certificate for device {device_id}")
        return True

    async def list_expiring_certificates(self, days: int) -> list[Certificate]:
        """List certificates expiring within specified days."""
        expiring = []
        threshold = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=days)

        for cert_file in self.certs_dir.glob("*.json"):
            data = json.loads(cert_file.read_text())
            cert = self._dict_to_cert(data)

            if not cert.revoked and cert.expires_at <= threshold:
                expiring.append(cert)

        return expiring

    async def list_all_certificates(self) -> list[Certificate]:
        """List all stored certificates."""
        certificates = []

        for cert_file in self.certs_dir.glob("*.json"):
            data = json.loads(cert_file.read_text())
            cert = self._dict_to_cert(data)
            certificates.append(cert)

        return certificates
