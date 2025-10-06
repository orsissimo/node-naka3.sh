#!/usr/bin/env python3
"""
JSON response formatter for Hiro API calls.

This module provides a single source of truth for formatting API responses
into a consistent JSON structure.
"""

import json
from typing import Any, Dict, Optional


def format_endpoint_response(
    endpoint: str,
    response: Any,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format an API endpoint response into a standardized structure.

    Args:
        endpoint: The API endpoint path (e.g., "/extended/v1/tx/{tx_id}")
        response: The raw API response (Pydantic model or dict)
        error: Optional error message if the call failed

    Returns:
        Dict with 'endpoint' and either 'response' or 'error'
    """
    result = {"endpoint": endpoint}

    if error:
        result["error"] = error
    else:
        # Convert Pydantic models to dict
        if hasattr(response, 'model_dump'):
            result["response"] = response.model_dump()
        elif hasattr(response, '__dict__'):
            result["response"] = response.__dict__
        else:
            result["response"] = response

    return result


class ResponseCollection:
    """Manages a collection of API endpoint responses."""

    def __init__(self, target_identifier: str):
        """
        Initialize response collection.

        Args:
            target_identifier: The target being queried (tx_id, contract_id, address, etc.)
        """
        self.data = {
            "target_tx_id": target_identifier,
            "endpoints": {}
        }

    def add_endpoint(
        self,
        method_name: str,
        endpoint: str,
        response: Any = None,
        error: Optional[str] = None
    ) -> None:
        """
        Add an endpoint response to the collection.

        Args:
            method_name: The API method name (e.g., "get_transaction_by_id")
            endpoint: The API endpoint path
            response: The raw API response
            error: Optional error message
        """
        self.data["endpoints"][method_name] = format_endpoint_response(
            endpoint=endpoint,
            response=response,
            error=error
        )

    def save(self, file_path: str) -> None:
        """
        Save the collection to a JSON file.

        Args:
            file_path: Path to save the JSON file
        """
        with open(file_path, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)

    def get_data(self) -> Dict[str, Any]:
        """
        Get the raw collection data.

        Returns:
            The collection data dict
        """
        return self.data

    def __len__(self) -> int:
        """Return the number of endpoints in the collection."""
        return len(self.data["endpoints"])
