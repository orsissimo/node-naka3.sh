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


class TransactionResult(BaseModel):
    """Result of a transaction and confirmation operation."""

    txid: str
    confirmed: bool

    class Config:
        populate_by_name = True
