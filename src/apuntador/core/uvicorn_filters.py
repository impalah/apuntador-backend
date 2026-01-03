"""
Custom logging filters for Uvicorn to reduce noise in logs.

This module provides filters to exclude health check and monitoring
endpoints from Uvicorn access logs.
"""

import logging


class HealthCheckFilter(logging.Filter):
    """
    Filter to exclude health check and monitoring endpoints from logs.
    
    This prevents Uvicorn from logging requests to /health, /healthz, /metrics,
    and /favicon.ico, significantly reducing log volume in production.
    """

    # Paths to exclude from logging
    EXCLUDED_PATHS = {"/health", "/healthz", "/metrics", "/favicon.ico"}

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if a log record should be logged.

        Args:
            record: Log record from Uvicorn

        Returns:
            False if the request path should be excluded, True otherwise
        """
        # Get the log message
        message = record.getMessage()

        # Check if any excluded path is in the message
        # Uvicorn logs format: "IP:PORT - "METHOD PATH PROTOCOL" STATUS"
        # Example: "10.0.12.168:43306 - "GET /health HTTP/1.1" 200"
        for path in self.EXCLUDED_PATHS:
            if f'"{path} ' in message or f'"{path}"' in message:
                return False

        return True
