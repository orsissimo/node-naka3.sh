#!/usr/bin/env python3

from pydantic import BaseModel
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens import StacksToken


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


class ApiError(Enum):
    """Standardized API error types."""

    NOT_FOUND = "Not found (404)"
    TIMEOUT = "Timeout"
    CONNECTION_ERROR = "Connection error"
    UNKNOWN_ERROR = "Unknown error"


class TransferResult(BaseModel):
    """Result of a transfer and confirmation operation."""

    txid: str
    confirmed: bool

    class Config:
        populate_by_name = True


class TransferInfo(BaseModel):
    """Type-safe transfer information."""

    miner: Miner
    to_address: str
    amount: int
    memo: str
    nonce: int
    status: TransactionStatus = TransactionStatus.PENDING
    txid: Optional[str] = None
    error: Optional[str] = None

    class Config:
        populate_by_name = True


class DeploymentInfo(BaseModel):
    """Type-safe deployment information."""

    miner: Miner
    contract_file: str
    contract_name: str
    nonce: int
    status: TransactionStatus = TransactionStatus.PENDING
    txid: Optional[str] = None
    error: Optional[str] = None
    size_kb: float = 0.0

    class Config:
        populate_by_name = True


class AccountInfo(BaseModel):
    """Type-safe account information from API."""

    address: str
    balance: int
    nonce: int

    class Config:
        populate_by_name = True

    @property
    def balance_amount(self) -> "StacksToken":
        from ..tokens import StacksToken

        return StacksToken.from_microstx(self.balance)