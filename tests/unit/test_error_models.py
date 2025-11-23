"""Tests for error models."""

import pytest

from apuntador.models.errors import ProblemDetail, get_rfc_section_url


def test_get_rfc_section_url_with_unknown_status():
    """Test RFC URL generation for unknown status code."""
    url = get_rfc_section_url(999)

    assert url == "https://datatracker.ietf.org/doc/html/rfc7231#section-6.6.1"


def test_get_rfc_section_url_with_https_url():
    """Test RFC URL generation when status maps to full HTTPS URL."""
    # Add a custom mapping that returns an https URL
    from apuntador.models.errors import status_to_section

    # This should return the section, but if it's a custom URL it returns as-is
    # Status 422 maps to a custom RFC URL
    url = get_rfc_section_url(422)

    # Should return the mapped value
    assert "datatracker.ietf.org" in url or url.startswith("https://")
