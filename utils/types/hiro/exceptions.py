#!/usr/bin/env python3
"""
Exception types for Stacks Mainnet API wrapper.
"""

from typing import Dict, Any, Optional


class MainnetAPIException(Exception):
    """Base exception for all mainnet API related errors."""
    pass


class MainnetHTTPException(MainnetAPIException):
    """HTTP-related exceptions from API calls."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None, 
        error_details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_details = error_details or {}


class MainnetNetworkException(MainnetAPIException):
    """Network-related exceptions (connection errors, timeouts)."""
    pass


class MainnetTimeoutException(MainnetNetworkException):
    """Request timeout exceptions."""
    pass


class MainnetValidationException(MainnetAPIException):
    """Data validation exceptions."""
    pass