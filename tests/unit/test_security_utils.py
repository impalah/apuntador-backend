"""
Unit tests for security utilities.

Tests token signing, state generation, and verification.
"""

from apuntador.utils.security import generate_state, sign_data, verify_signed_data


def test_generate_state():
    """Test state generation produces unique random strings."""
    # Act
    state1 = generate_state()
    state2 = generate_state()
    state3 = generate_state()

    # Assert
    assert isinstance(state1, str)
    assert isinstance(state2, str)
    assert isinstance(state3, str)
    assert state1 != state2
    assert state2 != state3
    assert len(state1) > 0


def test_generate_state_length():
    """Test generated state has reasonable length."""
    # Act
    state = generate_state()

    # Assert
    # Should be at least 20 characters for security
    assert len(state) >= 20
    assert len(state) <= 100  # Reasonable upper bound


def test_sign_data():
    """Test data signing produces a signed token."""
    # Arrange
    data = {
        "key1": "value1",
        "key2": "value2",
        "timestamp": 1234567890,
    }

    # Act
    signed = sign_data(data)

    # Assert
    assert isinstance(signed, str)
    assert len(signed) > 0
    # Signed data should be different from original
    assert signed != str(data)


def test_verify_signed_data_success():
    """Test verification of correctly signed data."""
    # Arrange
    original_data = {
        "user_id": "12345",
        "scope": "read:files",
        "nonce": "random-nonce-abc",
    }

    # Act
    signed = sign_data(original_data)
    verified = verify_signed_data(signed)

    # Assert
    assert verified == original_data
    assert verified["user_id"] == "12345"
    assert verified["scope"] == "read:files"


def test_verify_signed_data_tampered():
    """Test verification fails for tampered data."""
    # Arrange
    original_data = {"sensitive": "data"}
    signed = sign_data(original_data)

    # Tamper with signed data
    tampered = signed[:-5] + "xxxxx"

    # Act
    result = verify_signed_data(tampered)

    # Assert
    assert result is None


def test_verify_signed_data_invalid_format():
    """Test verification fails for invalid format."""
    # Arrange
    invalid_token = (
        "this-is-not-a-valid-signed-token"  # NOSONAR - Test fixture, not a real secret
    )

    # Act
    result = verify_signed_data(invalid_token)

    # Assert
    assert result is None


def test_sign_and_verify_complex_data():
    """Test signing and verification with complex nested data."""
    # Arrange
    complex_data = {
        "user": {
            "id": "user-123",
            "roles": ["admin", "editor"],
        },
        "permissions": {
            "read": True,
            "write": True,
            "delete": False,
        },
        "metadata": {
            "created_at": "2025-01-01T00:00:00Z",
            "expires_at": "2025-12-31T23:59:59Z",
        },
    }

    # Act
    signed = sign_data(complex_data)
    verified = verify_signed_data(signed)

    # Assert
    assert verified == complex_data
    assert verified["user"]["id"] == "user-123"
    assert "admin" in verified["user"]["roles"]
    assert verified["permissions"]["read"] is True


def test_sign_data_empty_dict():
    """Test signing empty dictionary."""
    # Arrange
    empty_data = {}

    # Act
    signed = sign_data(empty_data)
    verified = verify_signed_data(signed)

    # Assert
    assert verified == empty_data


def test_sign_data_with_special_characters():
    """Test signing data with special characters."""
    # Arrange
    data_with_special = {
        "message": "Hello! @#$%^&*() 你好 🎉",
        "url": "https://example.com/path?param=value&other=123",
        "emoji": "😀😃😄",
    }

    # Act
    signed = sign_data(data_with_special)
    verified = verify_signed_data(signed)

    # Assert
    assert verified == data_with_special
    assert verified["message"] == "Hello! @#$%^&*() 你好 🎉"


def test_multiple_sign_verify_cycles():
    """Test multiple sign/verify cycles produce consistent results."""
    # Arrange
    data = {"test": "data", "cycle": 1}

    # Act
    signed1 = sign_data(data)
    verified1 = verify_signed_data(signed1)

    signed2 = sign_data(verified1)
    verified2 = verify_signed_data(signed2)

    # Assert
    assert verified1 == data
    assert verified2 == data
    # Note: signed1 and signed2 may differ due to timestamps in signature


def test_state_uniqueness():
    """Test state generation produces unique values."""
    # Arrange
    num_states = 50

    # Act
    states = {generate_state() for _ in range(num_states)}

    # Assert - All states should be unique
    assert len(states) == num_states
