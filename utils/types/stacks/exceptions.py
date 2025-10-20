#!/usr/bin/env python3
"""Exceptions specific to Stacks operations and error handling."""

from typing import Optional, Dict, Any


class StacksException(Exception):
    """Base exception for Stacks-related errors."""

    pass


class StacksAPIException(StacksException):
    """API-related exceptions."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.error_details = error_details or {}
        super().__init__(message)

    def is_not_found(self) -> bool:
        return self.status_code == 404

    def is_client_error(self) -> bool:
        return self.status_code is not None and 400 <= self.status_code < 500

    def is_server_error(self) -> bool:
        return self.status_code is not None and 500 <= self.status_code < 600


class StacksHTTPException(StacksAPIException):
    """HTTP-specific exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, error_details)

    @classmethod
    def from_response(
        cls, response, error_details: Optional[Dict[str, Any]] = None
    ) -> "StacksHTTPException":
        return cls(
            message=f"HTTP {response.status_code}: {response.reason}",
            status_code=response.status_code,
            error_details=error_details or {},
        )


class StacksCLIException(StacksException):
    """CLI-related exceptions."""

    def __init__(
        self,
        message: str,
        return_code: Optional[int] = None,
        stderr: Optional[str] = None,
    ):
        self.return_code = return_code
        self.stderr = stderr
        super().__init__(message)


class StacksValidationException(StacksException):
    """Data validation exceptions."""

    pass


class StacksNetworkException(StacksException):
    """Network/connection related exceptions."""

    pass


class StacksTimeoutException(StacksNetworkException):
    """Timeout-specific exceptions."""

    pass


class RecipeFailedException(StacksException):
    """Exception for test/recipe failures requiring cleanup."""

    def __init__(
        self, message: str, step: Optional[str] = None, details: Optional[str] = None
    ):
        self.step = step
        self.details = details
        super().__init__(message)
