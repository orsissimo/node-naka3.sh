#!/usr/bin/env python3
"""
JSON response formatter for Hiro API calls.

This module provides a single source of truth for formatting API responses
into a consistent JSON structure, plus utilities for extracting data from
responses.
"""

import json
import re
from typing import Any, Dict, List, Optional

from utils.types.hiro.infrastructure import (
    ContractMetadata,
    ParsedContractId,
    AbiFunctions,
    ContractCallEvent,
)


class ResponseCollection:
    """Manages a collection of API endpoint responses."""

    def __init__(self, target_identifier: str):
        """
        Initialize response collection.

        Args:
            target_identifier: The target being queried (tx_id, contract_id, address, etc.)
        """
        self.data = {"target_tx_id": target_identifier, "endpoints": {}}

    def add(
        self, method_name: str, response: Any = None, error: Optional[str] = None
    ) -> None:
        result = {}

        if error:
            result["error"] = error
        else:
            # Convert Pydantic models to dict
            if hasattr(response, "model_dump"):
                result["response"] = response.model_dump()
            elif hasattr(response, "__dict__"):
                result["response"] = response.__dict__
            else:
                result["response"] = response

        self.data["endpoints"][method_name] = result

    def save(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

    def get_data(self) -> Dict[str, Any]:
        return self.data

    def __len__(self) -> int:
        """Return the number of endpoints in the collection."""
        return len(self.data["endpoints"])


# Data extraction utilities


def extract_contract_metadata(data: dict) -> ContractMetadata:
    """
    Extract contract metadata from response collection data.

    Args:
        data: The response collection data (loaded from JSON)

    Returns:
        ContractMetadata with all contract information including parsed ABI functions and events
    """
    contract_response = data["endpoints"]["get_contract_by_id"]["response"]
    contract_id = contract_response["contract_id"]
    parsed_id = _parse_contract_id(contract_id)

    # Parse ABI string to dict if needed
    abi_data = contract_response["abi"]
    abi_dict = json.loads(abi_data) if isinstance(abi_data, str) else abi_data

    # Parse ABI functions
    abi_functions = _parse_abi_functions(abi_dict)

    # Extract contract events
    contract_events = _extract_contract_call_events(data)

    return ContractMetadata(
        contract_id=contract_id,
        contract_name=parsed_id.contract_name,
        contract_address=parsed_id.address,
        source_code=contract_response["source_code"],
        abi=abi_dict,
        abi_functions=abi_functions,
        tx_id=contract_response["tx_id"],
        contract_events=contract_events,
    )


def _extract_events_chronological(data: dict) -> list:
    """
    Extract contract events in chronological order.

    The API returns newest events first, this function reverses them
    to get chronological order (oldest to newest).

    Args:
        data: The response collection data (loaded from JSON)

    Returns:
        List of events in chronological order
    """
    events_response = data["endpoints"]["get_contract_events_by_id"]["response"]
    events = events_response["results"]

    # Reverse to get chronological order (API returns newest first)
    return list(reversed(events))


def _extract_contract_call_events(data: dict) -> List[ContractCallEvent]:
    """
    Extract and parse contract call events from response collection data.

    This function:
    1. Gets events in chronological order
    2. Filters for smart_contract_log events
    3. Extracts event representation and parses event names
    4. Returns clean ContractCallEvent objects

    Args:
        data: The response collection data (loaded from JSON)

    Returns:
        List of ContractCallEvent objects with parsed event information
    """
    events = _extract_events_chronological(data)

    contract_call_events = []
    for event in events:
        if event.get("event_type") == "smart_contract_log":
            contract_log = event.get("contract_log")
            if contract_log:
                value_repr = contract_log["value"]["repr"]
                event_name = _parse_event_name(value_repr)

                contract_call_events.append(
                    ContractCallEvent(
                        event_repr=value_repr,
                        event_name=event_name,
                        tx_id=event["tx_id"],
                        event_index=event["event_index"],
                    )
                )

    return contract_call_events


def _parse_abi_functions(abi_str_or_dict) -> AbiFunctions:
    """
    Parse ABI and group functions by access type.

    Args:
        abi_str_or_dict: Either an ABI JSON string or already-parsed dict

    Returns:
        AbiFunctions with public and read_only function lists plus name lists
    """
    # Parse if string, otherwise use as-is
    abi_dict = (
        json.loads(abi_str_or_dict)
        if isinstance(abi_str_or_dict, str)
        else abi_str_or_dict
    )

    public_functions = [
        func for func in abi_dict["functions"] if func["access"] == "public"
    ]

    read_only_functions = [
        func for func in abi_dict["functions"] if func["access"] == "read_only"
    ]

    return AbiFunctions(
        public=public_functions,
        read_only=read_only_functions,
        public_names=[func["name"] for func in public_functions],
        read_only_names=[func["name"] for func in read_only_functions],
    )


def find_function_by_event(event_name: str, source_code: str) -> str | None:
    """
    Find which function contains a specific event by searching the source code.

    This searches for print statements containing the event name, then determines
    which public function contains that print statement.

    Args:
        event_name: The event name (e.g., "incremented")
        source_code: The contract source code

    Returns:
        The function name that contains this event, or None if not found
    """
    # Search for the event in print statements
    # Pattern: (print {event: "event_name"
    event_pattern = rf'\(print\s+\{{[^}}]*event:\s*"{re.escape(event_name)}"'
    event_match = re.search(event_pattern, source_code)

    if not event_match:
        return None

    # Find the position of the event
    event_pos = event_match.start()

    # Find all public function definitions
    # Pattern: (define-public (function-name)
    func_pattern = r"\(define-public\s+\(([a-zA-Z0-9\-_]+)"

    # Find all functions and their positions
    functions = []
    for match in re.finditer(func_pattern, source_code):
        func_name = match.group(1)
        func_start = match.start()
        functions.append((func_name, func_start))

    # Find which function contains this event
    # The event belongs to the last function that starts before the event position
    containing_function = None
    for func_name, func_start in sorted(functions, key=lambda x: x[1]):
        if func_start < event_pos:
            containing_function = func_name
        else:
            break

    return containing_function


def _parse_event_name(event_repr: str) -> str | None:
    """
    Extract event name from Clarity event log representation.

    Args:
        event_repr: The event representation string, e.g.,
                   '(tuple (caller '...) (event "incremented") ...)'

    Returns:
        The event name (e.g., "incremented") or None if not found
    """
    # Pattern: (event "event_name")
    event_match = re.search(r'\(event\s+"([^"]+)"\)', event_repr)
    return event_match.group(1) if event_match else None


def _parse_contract_id(contract_id: str) -> ParsedContractId:
    """
    Split contract_id into address and contract name components.

    Args:
        contract_id: Full contract ID in format 'ADDRESS.contract-name'

    Returns:
        ParsedContractId with address and contract_name
    """
    parts = contract_id.split(".")
    return ParsedContractId(
        address=parts[0],
        contract_name=parts[1] if len(parts) > 1 else "",
    )
