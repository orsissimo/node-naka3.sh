#!/usr/bin/env python3
"""
API type definitions for Hiro API responses.
Based on the OpenAPI schema definitions.
"""

from pydantic import BaseModel, Field, RootModel
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class TransactionType(str, Enum):
    """Transaction types from the API."""

    COINBASE = "coinbase"
    TOKEN_TRANSFER = "token_transfer"
    SMART_CONTRACT = "smart_contract"
    CONTRACT_CALL = "contract_call"
    POISON_MICROBLOCK = "poison_microblock"
    TENURE_CHANGE = "tenure_change"


class TransactionStatus(str, Enum):
    """Transaction status types."""

    PENDING = "pending"
    SUCCESS = "success"
    ABORT_BY_RESPONSE = "abort_by_response"
    ABORT_BY_POST_CONDITION = "abort_by_post_condition"


class FeeType(str, Enum):
    """Fee types."""

    STX = "stx"


class PostConditionPrincipalType(str, Enum):
    """Post condition principal types."""

    ORIGIN = "principal-origin"
    STANDARD = "principal-standard"
    CONTRACT_NAME = "principal-contract-name"


class PostConditionFungibleConditionCode(str, Enum):
    """Fungible post condition codes."""

    SENT_EQUAL_TO = "sent_equal_to"
    SENT_GREATER_THAN = "sent_greater_than"
    SENT_GREATER_THAN_OR_EQUAL_TO = "sent_greater_than_or_equal_to"
    SENT_LESS_THAN = "sent_less_than"
    SENT_LESS_THAN_OR_EQUAL_TO = "sent_less_than_or_equal_to"


class ApiStatus(BaseModel):
    """API status response from /extended endpoint."""

    server_version: str
    status: str
    pox_v1_unlock_height: Optional[int] = None
    pox_v2_unlock_height: Optional[int] = None
    pox_v3_unlock_height: Optional[int] = None
    chain_tip: Optional["ChainTip"] = None

    class Config:
        populate_by_name = True


class ChainTip(BaseModel):
    """Chain tip information."""

    block_height: int
    block_hash: str
    index_block_hash: str
    microblock_hash: Optional[str] = None
    microblock_sequence: Optional[int] = None
    burn_block_height: int

    class Config:
        populate_by_name = True


class TransactionFee(BaseModel):
    """Transaction fee information."""

    type: FeeType
    amount: str

    class Config:
        populate_by_name = True


class PostCondition(BaseModel):
    """Transaction post condition."""

    type: str
    condition_code: Optional[str] = None
    amount: Optional[str] = None
    principal: Optional[Dict[str, Any]] = None
    asset: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class SmartContractData(BaseModel):
    """Smart contract deployment data."""

    contract_id: str
    source_code: Optional[str] = None

    class Config:
        populate_by_name = True


class ContractCallData(BaseModel):
    """Contract call data."""

    contract_id: str
    function_name: str
    function_signature: Optional[str] = None
    function_args: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class TokenTransferData(BaseModel):
    """Token transfer data."""

    recipient_address: str
    amount: str
    memo: Optional[str] = None

    class Config:
        populate_by_name = True


class Transaction(BaseModel):
    """Transaction response from the API."""

    tx_id: str
    nonce: int
    fee_rate: str
    sender_address: str
    sponsored: bool = False
    sponsor_address: Optional[str] = None
    post_condition_mode: str
    post_conditions: List[PostCondition] = Field(default_factory=list)
    anchor_mode: str
    is_unanchored: bool = False
    block_hash: str
    parent_block_hash: str
    block_height: int
    block_time: int
    block_time_iso: str
    burn_block_height: int
    burn_block_time: int
    burn_block_time_iso: str
    parent_burn_block_time: int
    canonical: bool
    tx_index: int
    tx_status: TransactionStatus
    tx_result: Dict[str, Any] = Field(default_factory=dict)
    microblock_hash: str
    microblock_sequence: int
    microblock_canonical: bool
    event_count: int
    events: List[Dict[str, Any]] = Field(default_factory=list)
    execution_cost_read_count: int
    execution_cost_read_length: int
    execution_cost_runtime: int
    execution_cost_write_count: int
    execution_cost_write_length: int
    tx_type: TransactionType

    # Transaction type-specific fields
    smart_contract: Optional[SmartContractData] = None
    contract_call: Optional[ContractCallData] = None
    token_transfer: Optional[TokenTransferData] = None

    class Config:
        populate_by_name = True


class TransactionList(BaseModel):
    """Response for transaction list endpoints."""

    limit: int
    offset: int
    total: int
    results: List[Transaction]

    class Config:
        populate_by_name = True


class TransactionEvent(BaseModel):
    """Transaction event information."""

    event_index: int
    event_type: str
    tx_id: str
    contract_log: Optional[Dict[str, Any]] = None
    stx_lock_event: Optional[Dict[str, Any]] = None
    asset: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class EventsList(BaseModel):
    """Response for events endpoints."""

    limit: int
    offset: int
    total: Optional[int] = None  # Some endpoints don't return total
    results: List[TransactionEvent]

    class Config:
        populate_by_name = True


class ContractInfo(BaseModel):
    """Smart contract information."""

    tx_id: str
    canonical: bool
    contract_id: str
    block_height: int
    source_code: str
    abi: str

    class Config:
        populate_by_name = True


class AddressStxBalance(BaseModel):
    """STX balance for an address."""

    balance: str
    total_sent: str
    total_received: str
    total_fees_sent: str
    total_miner_rewards_received: str
    lock_tx_id: str
    locked: str
    lock_height: int
    burnchain_lock_height: int
    burnchain_unlock_height: int

    class Config:
        populate_by_name = True


class FungibleTokenBalance(BaseModel):
    """Fungible token balance."""

    balance: str
    total_sent: str
    total_received: str

    class Config:
        populate_by_name = True


class NonFungibleTokenBalance(BaseModel):
    """Non-fungible token balance."""

    count: str
    total_sent: str
    total_received: str

    class Config:
        populate_by_name = True


class AddressBalance(BaseModel):
    """Complete address balance information."""

    stx: AddressStxBalance
    fungible_tokens: Dict[str, FungibleTokenBalance] = Field(default_factory=dict)
    non_fungible_tokens: Dict[str, NonFungibleTokenBalance] = Field(
        default_factory=dict
    )

    class Config:
        populate_by_name = True


class AddressTransactionWithTransfers(BaseModel):
    """Transaction with transfer information for an address."""

    tx: Transaction
    stx_sent: str
    stx_received: str
    stx_transfers: List[Dict[str, Any]] = Field(default_factory=list)
    ft_transfers: List[Dict[str, Any]] = Field(default_factory=list)
    nft_transfers: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class AddressTransactionsWithTransfers(BaseModel):
    """Response for address transactions with transfers."""

    limit: int
    offset: int
    total: int
    results: List[AddressTransactionWithTransfers]

    class Config:
        populate_by_name = True


class AddressAsset(BaseModel):
    """Asset information for an address."""

    event_index: int
    event_type: str
    tx_id: str
    asset: Dict[str, Any]

    class Config:
        populate_by_name = True


class AddressAssets(BaseModel):
    """Assets response for an address."""

    limit: int
    offset: int
    total: int
    results: List[AddressAsset]

    class Config:
        populate_by_name = True


class StxTransfer(BaseModel):
    """STX transfer information."""

    amount: str
    sender: str
    recipient: str
    memo: Optional[str] = None

    class Config:
        populate_by_name = True


class InboundStxTransfer(BaseModel):
    """Inbound STX transfer."""

    sender: str
    amount: str
    memo: str
    block_height: int
    tx_id: str
    transfer_type: str
    tx_index: int

    class Config:
        populate_by_name = True


class AddressStxInboundList(BaseModel):
    """Response for inbound STX transfers."""

    limit: int
    offset: int
    total: int
    results: List[InboundStxTransfer]

    class Config:
        populate_by_name = True


class AddressNonces(BaseModel):
    """Address nonce information."""

    last_mempool_tx_nonce: Optional[int] = None
    last_executed_tx_nonce: Optional[int] = None
    possible_next_nonce: int
    detected_missing_nonces: List[int] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class SearchResult(BaseModel):
    """Search result response."""

    found: bool
    result: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class TransactionSearchResult(BaseModel):
    """Result for a single transaction in batch lookup."""

    found: bool
    result: Optional[Transaction] = None

    class Config:
        populate_by_name = True


class TransactionMultipleResponse(RootModel[Dict[str, TransactionSearchResult]]):
    """Response for /extended/v1/tx/multiple - batch transaction lookup.

    Note: This uses a Dict because the API returns transaction IDs as dynamic keys.
    The keys are transaction IDs (strings) and values are TransactionSearchResult objects.
    """

    root: Dict[str, TransactionSearchResult]

    def __getitem__(self, key: str) -> TransactionSearchResult:
        return self.root[key]

    def __iter__(self):  # type: ignore
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def items(self):
        return self.root.items()

    def keys(self):
        return self.root.keys()

    def values(self):
        return self.root.values()
