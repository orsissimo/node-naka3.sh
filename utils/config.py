from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List, Any

@dataclass
class Account:
    """A dataclass to hold all information for a single miner account."""
    name: str
    address: str
    private_key: str
    api_port: int

    @property
    def api_url(self) -> str:
        return f"http://localhost:{self.api_port}"

ACCOUNTS = {
    1: Account(
        name="miner1",
        address="STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6", 
        private_key="cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01",
        api_port=20443
    ),
    2: Account(
        name="miner2",
        address="ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y", 
        private_key="21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601",
        api_port=30443
    ),
    3: Account(
        name="miner3",
        address="ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0", 
        private_key="7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01",
        api_port=40443
    )
}

class Miner(Enum):
    """Enum for type-safe miner access."""
    MINER1 = 1
    MINER2 = 2
    MINER3 = 3


class MiningMode(Enum):
    """Enum for mining mode selection."""
    AUTO = "auto"
    MANUAL = "manual"

class TransactionStatus(Enum):
    """Enum for transaction status with IDE autocompletion."""
    SUBMITTED = "submitted"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

class TestResult(Enum):
    """Enum for test results with IDE autocompletion."""
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"

class TxStatus(Enum):
    """Enum for transaction status values from Stacks API."""
    SUCCESS = "success"
    PENDING = "pending"
    ABORT_BY_RESPONSE = "abort_by_response"
    ABORT_BY_POST_CONDITION = "abort_by_post_condition"
    UNKNOWN = "unknown"

class ApiError(Enum):
    """Enum for standardized API error types."""
    NOT_FOUND = "Not found (404)"
    TIMEOUT = "Timeout"
    CONNECTION_ERROR = "Connection error"
    UNKNOWN_ERROR = "Unknown error"

class AccountManager:
    """Type-safe account access."""
    
    @staticmethod
    def get(miner: Miner) -> Account:
        """Get account by enum with full IDE autocompletion support."""
        return ACCOUNTS[miner.value]
    
    @staticmethod
    def all_miners() -> List[Miner]:
        """Get all available miner enums."""
        return list(Miner)
    
    @staticmethod
    def all() -> Dict[str, Account]:
        """Get all accounts."""
        return ACCOUNTS.copy()

@dataclass 
class TransferParams:
    """Parameters for generating transfers."""
    to: str
    amount: int
    memo: str

@dataclass
class TransferInfo:
    """Type-safe transfer information."""
    miner: Miner
    to_address: str
    amount: int
    memo: str
    nonce: int
    status: TransactionStatus = TransactionStatus.PENDING
    txid: Optional[str] = None
    error: Optional[str] = None

@dataclass
class DeploymentInfo:
    """Type-safe deployment information."""
    miner: Miner
    contract_file: str
    contract_name: str
    nonce: int
    status: TransactionStatus = TransactionStatus.PENDING
    txid: Optional[str] = None
    error: Optional[str] = None
    size_kb: float = 0.0

@dataclass
class AccountInfo:
    """Type-safe account information from API."""
    address: str
    balance: int
    nonce: int

@dataclass
class ApiResult:
    """Type-safe API call result."""
    success: bool
    data: Optional[Any] = None
    error: Optional[ApiError] = None
    error_message: Optional[str] = None

@dataclass 
class VerificationSummary:
    """Type-safe verification summary with full IDE support."""
    total: int
    confirmed: int
    pending: int
    failed: int
    success_rate: float
    
@dataclass
class VerificationResults:
    """Type-safe verification results with full IDE support."""
    confirmed: List['TransferInfo'] = None
    failed: List['TransferInfo'] = None
    pending: List['TransferInfo'] = None
    confirmed_deployments: List['DeploymentInfo'] = None
    failed_deployments: List['DeploymentInfo'] = None
    pending_deployments: List['DeploymentInfo'] = None
    
    def __post_init__(self):
        if self.confirmed is None:
            self.confirmed = []
        if self.failed is None:
            self.failed = []
        if self.pending is None:
            self.pending = []
        if self.confirmed_deployments is None:
            self.confirmed_deployments = []
        if self.failed_deployments is None:
            self.failed_deployments = []
        if self.pending_deployments is None:
            self.pending_deployments = []

