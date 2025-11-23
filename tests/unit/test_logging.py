"""Tests for logging configuration."""

import io
import json
from unittest.mock import patch

import pytest
from loguru import logger

from apuntador.core.logging import JsonSink, add_trace_id, get_log_format
from apuntador.core.trace_context import trace_id_context


def test_json_sink_basic_message():
    """Test JsonSink formats basic messages correctly."""
    stream = io.StringIO()
    sink = JsonSink(stream=stream)

    # Create a mock message with record attribute
    class MockMessage:
        class MockRecord:
            def __init__(self):
                from datetime import datetime

                self.record = {
                    "time": datetime(2025, 11, 23, 10, 30, 45, 123000),
                    "level": type("Level", (), {"name": "INFO"}),
                    "name": "test_module",
                    "function": "test_function",
                    "line": 42,
                    "message": "Test message",
                    "exception": None,
                    "extra": {"trace_id": "test-trace-123"},
                }

        @property
        def record(self):
            return self.MockRecord().record

    sink.write(MockMessage())

    output = stream.getvalue()
    assert output  # Not empty

    log_data = json.loads(output.strip())
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Test message"
    assert log_data["trace_id"] == "test-trace-123"
    assert log_data["function"] == "test_function"
    assert log_data["line"] == 42


def test_json_sink_with_exception():
    """Test JsonSink formats exceptions correctly."""
    stream = io.StringIO()
    sink = JsonSink(stream=stream)

    # Create a mock message with exception
    class MockMessage:
        class MockRecord:
            def __init__(self):
                from datetime import datetime

                self.record = {
                    "time": datetime(2025, 11, 23, 10, 30, 45, 123000),
                    "level": type("Level", (), {"name": "ERROR"}),
                    "name": "test_module",
                    "function": "test_function",
                    "line": 42,
                    "message": "Error occurred",
                    "exception": (ValueError, ValueError("test error"), None),
                    "extra": {"trace_id": "error-trace-456"},
                }

        @property
        def record(self):
            return self.MockRecord().record

    sink.write(MockMessage())

    output = stream.getvalue()
    log_data = json.loads(output.strip())

    assert "exception" in log_data
    assert log_data["exception"]["type"] == "ValueError"
    assert log_data["exception"]["value"] == "test error"


def test_add_trace_id_filter():
    """Test add_trace_id adds trace_id to log record."""
    record = {"extra": {}}

    # Set a trace ID in context
    trace_id_context.set("test-trace-789")

    result = add_trace_id(record)

    assert result is True
    assert record["extra"]["trace_id"] == "test-trace-789"

    # Clean up
    trace_id_context.set(None)


def test_add_trace_id_no_context():
    """Test add_trace_id uses N/A when no trace_id in context."""
    record = {"extra": {}}

    # Ensure no trace ID in context
    trace_id_context.set(None)

    result = add_trace_id(record)

    assert result is True
    assert record["extra"]["trace_id"] == "N/A"


def test_get_log_format_human():
    """Test get_log_format returns human-readable format."""
    with patch("apuntador.core.logging.settings") as mock_settings:
        mock_settings.log_format = "human"

        fmt = get_log_format()

        assert isinstance(fmt, str)
        assert "{time}" in fmt or "time" in fmt.lower()


def test_get_log_format_json():
    """Test get_log_format with JSON format setting."""
    with patch("apuntador.core.logging.settings") as mock_settings:
        mock_settings.log_format = "json"

        # JSON format still returns a format string
        fmt = get_log_format()

        assert isinstance(fmt, str)
