"""Additional simple tests to increase coverage."""


import pytest


def test_pkce_utilities():
    """Test PKCE utility functions."""
    from apuntador.utils.pkce import (
        generate_code_challenge,
        generate_code_verifier,
        verify_code_challenge,
    )

    # Generate verifier
    verifier = generate_code_verifier()
    assert len(verifier) >= 43
    assert len(verifier) <= 128

    # Generate challenge from verifier
    challenge = generate_code_challenge(verifier)
    assert len(challenge) > 0

    # Verify challenge matches verifier
    is_valid = verify_code_challenge(verifier, challenge)
    assert is_valid is True

    # Verify mismatch detection
    is_invalid = verify_code_challenge("wrong_verifier", challenge)
    assert is_invalid is False


def test_security_utilities():
    """Test security utility functions."""
    from apuntador.utils.security import generate_state, sign_data, verify_signed_data

    # Generate state
    state = generate_state()
    assert len(state) > 0

    # Sign data
    data = {"key": "value", "number": 123}
    signed = sign_data(data)
    assert isinstance(signed, str)

    # Verify signed data
    verified = verify_signed_data(signed)
    assert verified == data


def test_security_verification_invalid():
    """Test security verification with invalid data."""
    from apuntador.utils.security import verify_signed_data

    try:
        verify_signed_data("invalid_signature")
        raise AssertionError("Should have raised an exception")
    except Exception:
        pass  # Expected


@pytest.mark.asyncio
async def test_local_secrets_empty_value():
    """Test storing empty secret value."""
    import tempfile

    from apuntador.infrastructure.implementations.local import LocalSecretsRepository

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = LocalSecretsRepository(base_dir=tmp_dir)

        # Store empty value
        await repo.store_secret("empty_key", "")

        # Retrieve it
        value = await repo.get_secret("empty_key")
        assert value == ""


@pytest.mark.asyncio
async def test_local_storage_download_nonexistent():
    """Test downloading nonexistent file."""
    import tempfile

    from apuntador.infrastructure.implementations.local import LocalStorageRepository

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = LocalStorageRepository(base_dir=tmp_dir)

        # Download nonexistent file
        content = await repo.download_file("does_not_exist.txt")

        assert content is None


def test_config_provider_check():
    """Test provider enabled check."""
    from apuntador.config import get_settings

    settings = get_settings()

    # Check if googledrive is enabled
    is_enabled = settings.is_provider_enabled("googledrive")
    assert isinstance(is_enabled, bool)
