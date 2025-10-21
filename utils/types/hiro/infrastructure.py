#!/usr/bin/env python3
"""
Hiro infrastructure data structures.

This module contains dataclasses for Hiro API data structures,
contract metadata, and operation results.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ContractMetadata:
    """Contract metadata with optional events."""

    contract_id: str
    contract_name: str
    contract_address: str
    source_code: str
    abi: dict
    abi_functions: "AbiFunctions"
    tx_id: str
    contract_events: Optional[List["ContractCallEvent"]] = None


@dataclass
class ParsedContractId:
    """Parsed contract ID components."""

    address: str
    contract_name: str


@dataclass
class AbiFunctions:
    """Parsed ABI functions grouped by access type."""

    public: List[dict]
    read_only: List[dict]
    public_names: List[str]
    read_only_names: List[str]


@dataclass
class ContractCallEvent:
    """Extracted contract call event information."""

    event_repr: str
    event_name: Optional[str]
    tx_id: str
    event_index: int


@dataclass
class EventCallResult:
    """Result of calling a contract function based on an event."""

    event_name: str
    function_name: str | None
    confirmed: bool
    txid: str | None
    error: str | None = None


@dataclass
class ReadOnlyResult:
    """Result of calling a read-only function."""

    function_name: str
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class TransferMetadata:
    """Token transfer metadata extracted from API response."""

    tx_id: str
    sender_address: str
    recipient_address: str
    amount: str
    memo: Optional[str]
    fee: str


@dataclass
class ContractCallMetadata:
    """Contract call metadata extracted from API response."""

    tx_id: str
    contract_metadata: ContractMetadata
    function_name: str
    function_args: List[dict]
    sender_address: str
    fee: str
