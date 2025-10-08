#!/usr/bin/env python3
"""
Exception types for Hiro API wrapper.
"""

from typing import Dict, Any, Optional


class HiroAPIException(Exception):
    """Base exception for all Hiro API related errors."""

    pass


class HiroHTTPException(HiroAPIException):
    """HTTP-related exceptions from API calls."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_details = error_details or {}


class HiroNetworkException(HiroAPIException):
    """Network-related exceptions (connection errors, timeouts)."""

    pass


class HiroTimeoutException(HiroNetworkException):
    """Request timeout exceptions."""

    pass


class HiroValidationException(HiroAPIException):
    """Data validation exceptions."""

    pass
