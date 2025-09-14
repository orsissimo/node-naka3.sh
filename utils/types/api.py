#!/usr/bin/env python3
"""
API type definitions for external service responses.
Includes types from Stacks Core API and blockstack-cli responses.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .tokens import StacksToken


class AccountInfo(BaseModel):
    """Type-safe account information from API."""

    address: str
    balance: int
    nonce: int

    class Config:
        populate_by_name = True

    @property
    def balance_amount(self) -> "StacksToken":
        from .tokens import StacksToken

        return StacksToken.from_microstx(self.balance)


class AddressInfo(BaseModel):
    """Typed response from addresses command."""

    stx_address: str = Field(alias="STX")
    btc_address: str = Field(alias="BTC")

    class Config:
        populate_by_name = True


class ContractInterface(BaseModel):
    """Contract interface response from /v2/contracts/interface endpoint."""

    functions: List[Dict]
    variables: List[Dict]
    maps: List[Dict]
    fungible_tokens: List[Dict] = Field(default_factory=list)
    non_fungible_tokens: List[Dict] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class ContractSource(BaseModel):
    """Contract source response from /v2/contracts/source endpoint."""

    source: str
    publish_height: int
    proof: Optional[str] = None

    class Config:
        populate_by_name = True


class NodeInfo(BaseModel):
    """Typed node information from /v2/info endpoint."""

    peer_version: int
    pox_consensus: str
    burn_block_height: int
    stable_pox_consensus: str
    stable_burn_block_height: int
    server_version: str
    network_id: int
    parent_network_id: int
    stacks_tip_height: int
    stacks_tip: str
    stacks_tip_consensus_hash: str
    genesis_chainstate_hash: str
    unanchored_tip: Optional[str] = None
    unanchored_seq: Optional[int] = None
    tenure_height: int
    exit_at_block_height: Optional[int] = None
    is_fully_synced: bool
    node_public_key: Optional[str] = None
    node_public_key_hash: Optional[str] = None
    affirmations: Optional[Dict] = None
    last_pox_anchor: Optional[Dict] = None
    stackerdbs: Optional[List] = None

    class Config:
        populate_by_name = True


class PoxCycle(BaseModel):
    """PoX cycle information for current cycle."""

    id: int
    min_threshold_ustx: int
    stacked_ustx: int
    is_pox_active: bool

    class Config:
        populate_by_name = True


class PoxNextCycle(BaseModel):
    """PoX next cycle information."""

    id: int
    min_threshold_ustx: int
    min_increment_ustx: int
    stacked_ustx: int
    prepare_phase_start_block_height: int
    blocks_until_prepare_phase: int
    reward_phase_start_block_height: int
    blocks_until_reward_phase: int
    ustx_until_pox_rejection: Optional[int] = None

    class Config:
        populate_by_name = True


class PoxEpoch(BaseModel):
    """PoX epoch information."""

    epoch_id: str
    start_height: int
    end_height: int
    block_limit: "PoxBlockLimit"
    network_epoch: int

    class Config:
        populate_by_name = True


class PoxBlockLimit(BaseModel):
    """Block limit information."""

    write_length: int
    write_count: int
    read_length: int
    read_count: int
    runtime: int

    class Config:
        populate_by_name = True


class PoxContractVersion(BaseModel):
    """PoX contract version information."""

    contract_id: str
    activation_burnchain_block_height: int
    first_reward_cycle_id: int

    class Config:
        populate_by_name = True


class PoxInfo(BaseModel):
    """Typed PoX information from /v2/pox endpoint."""

    contract_id: str
    pox_activation_threshold_ustx: int
    first_burnchain_block_height: int
    current_burnchain_block_height: int
    prepare_phase_block_length: int
    reward_phase_block_length: int
    reward_slots: int
    rejection_fraction: Optional[int] = None
    total_liquid_supply_ustx: int
    current_cycle: PoxCycle
    next_cycle: PoxNextCycle
    epochs: List[PoxEpoch]
    min_amount_ustx: int
    prepare_cycle_length: int
    reward_cycle_id: int
    reward_cycle_length: int
    rejection_votes_left_required: Optional[int] = None
    next_reward_cycle_in: int
    contract_versions: List[PoxContractVersion]

    class Config:
        populate_by_name = True


class ReadOnlyFunctionResult(BaseModel):
    """Read-only function call result from /v2/contracts/call-read endpoint."""

    okay: bool
    result: str
    cause: Optional[str] = None

    class Config:
        populate_by_name = True


class SecretKeyInfo(BaseModel):
    """Typed response from generate-sk command."""

    secret_key: str = Field(alias="secretKey")
    public_key: str = Field(alias="publicKey")
    stacks_address: str = Field(alias="stacksAddress")

    class Config:
        populate_by_name = True


class SortitionInfo(BaseModel):
    """Sortition information from /v3/sortitions endpoint."""

    # Based on the actual API response structure
    burn_block_hash: str
    burn_block_height: int
    burn_header_timestamp: int
    sortition_id: str
    parent_sortition_id: str
    consensus_hash: str
    ops: Optional[List[Dict]] = None  # Could be further typed if needed
    burn_amount: Optional[int] = None
    sunset_burn: Optional[int] = None

    class Config:
        populate_by_name = True


class TraitImplementationResponse(BaseModel):
    """Response for trait implementation check."""

    is_implemented: bool

    class Config:
        populate_by_name = True


class TenureInfo(BaseModel):
    """Tenure information from /v3/tenures/info endpoint."""

    consensus_hash: str
    tenure_start_block_id: str

    class Config:
        populate_by_name = True


class TransactionDetails(BaseModel):
    """Transaction details from /v3/transaction endpoint."""

    index_block_hash: Optional[str] = None
    tx: Optional[str] = None  # Raw transaction hex
    result: Optional[str] = None  # Contract call result like '(ok true)'
    txid: Optional[str] = None  # Added manually by our code
    tx_status: Optional[str] = None  # Added manually by our code
    tx_type: Optional[str] = None  # Added manually by our code
    receipt_time: Optional[int] = None
    receipt_time_iso: Optional[str] = None

    class Config:
        populate_by_name = True

    @property
    def status(self):
        """Get transaction status as typed enum with IDE autocompletion."""
        from .infrastructure import TxStatus

        if self.tx_status == "success":
            return TxStatus.SUCCESS
        elif self.tx_status == "abort_by_response":
            return TxStatus.ABORT_BY_RESPONSE
        elif self.tx_status == "abort_by_post_condition":
            return TxStatus.ABORT_BY_POST_CONDITION
        elif self.tx_status == "pending":
            return TxStatus.PENDING
        else:
            return TxStatus.UNKNOWN


class MapEntry(BaseModel):
    """Data-map entry response from /v2/map_entry endpoint."""

    data: str  # hex-encoded Clarity value (varies by map definition)
    proof: str  # hex-encoded merkle proof for verification

    class Config:
        populate_by_name = True
