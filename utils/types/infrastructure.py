#!/usr/bin/env python3
"""
Infrastructure type definitions for internal business logic and operations.
Includes business entities, status enums, and operational types.
"""

from enum import Enum
from pydantic import BaseModel
from typing import Optional


class Miner(Enum):
    """Type-safe miner access enum."""

    MINER1 = 1
    MINER2 = 2
    MINER3 = 3


class MiningMode(Enum):
    """Mining mode selection enum."""

    AUTO = "auto"
    MANUAL = "manual"


class TransactionStatus(Enum):
    """Transaction status enum."""

    SUBMITTED = "submitted"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class TxStatus(Enum):
    """Transaction status values from Stacks API."""

    SUCCESS = "success"
    PENDING = "pending"
    ABORT_BY_RESPONSE = "abort_by_response"
    ABORT_BY_POST_CONDITION = "abort_by_post_condition"
    UNKNOWN = "unknown"


class Account(BaseModel):
    """Pydantic model for miner account information."""

    name: str
    address: str
    private_key: str
    api_port: int

    class Config:
        populate_by_name = True

    @property
    def api_url(self) -> str:
        return f"http://localhost:{self.api_port}"


class TransferResult(BaseModel):
    """Result of a transfer and confirmation operation."""

    txid: str
    confirmed: bool

    class Config:
        populate_by_name = True
