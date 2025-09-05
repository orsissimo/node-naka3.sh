from pydantic import BaseModel, Field
from enum import Enum
from typing import Dict, Optional, List, Any
import os

# Constants
MICROSTX_PER_STX = 1_000_000
SATOSHI_PER_BTC = 100_000_000  # 1 BTC = 100,000,000 satoshi
DEFAULT_HTTP_TIMEOUT = 20
DEFAULT_API_PORT = 20443
DEFAULT_POLL_INTERVAL = 2
DEFAULT_WAIT_TIMEOUT = 60


class Account(BaseModel):
    """A Pydantic model to hold all information for a single miner account."""

    name: str
    address: str
    private_key: str
    api_port: int

    class Config:
        populate_by_name = True

    @property
    def api_url(self) -> str:
        return f"http://localhost:{self.api_port}"


_ACCOUNTS = {
    1: Account(
        name="miner1",
        address="STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
        private_key="cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01",
        api_port=20443,
    ),
    2: Account(
        name="miner2",
        address="ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y",
        private_key="21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601",
        api_port=30443,
    ),
    3: Account(
        name="miner3",
        address="ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0",
        private_key="7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01",
        api_port=40443,
    ),
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


# Custom Exception Classes for better error handling
class StacksException(Exception):
    """Base exception for all Stacks-related errors."""

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
    """Exception for explicit test/recipe failures that require cleanup."""

    def __init__(
        self, message: str, step: Optional[str] = None, details: Optional[str] = None
    ):
        self.step = step
        self.details = details
        super().__init__(message)


class AccountManager:
    """Type-safe account access with perfect encapsulation."""

    def __init__(self):
        self._accounts = _ACCOUNTS.copy()
        self._validate_accounts()

    def _validate_accounts(self):
        """Validate account configuration."""
        if not self._accounts:
            raise ValueError("No accounts configured")
        for key, account in self._accounts.items():
            if not isinstance(key, int) or key <= 0:
                raise ValueError(f"Invalid account key: {key}")
            if not isinstance(account, Account):
                raise TypeError(f"Account {key} is not an Account instance")

    def get(self, miner: Miner) -> Account:
        """Get account by enum with validation."""
        if not isinstance(miner, Miner):
            raise TypeError("Parameter must be a Miner enum")
        if miner.value not in self._accounts:
            raise ValueError(f"No account found for miner: {miner}")
        return self._accounts[miner.value]

    def all_miners(self) -> List[Miner]:
        """Get all available miner enums."""
        return list(Miner)

    def all(self) -> Dict[str, Account]:
        """Get copy of all accounts (read-only)."""
        return {account.name: account for account in self._accounts.values()}

    @property
    def account_count(self) -> int:
        """Get number of managed accounts (read-only)."""
        return len(self._accounts)


# Global account manager instance
account_manager = AccountManager()


class TransferParams(BaseModel):
    """Parameters for generating transfers."""

    to: str
    amount: int
    memo: str

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
    def balance_amount(self) -> "TokenAmount":
        """Get balance as TokenAmount for easy conversions."""
        from .tokens import microstx

        return microstx(self.balance)


class ApiResult(BaseModel):
    """Type-safe API call result."""

    success: bool
    data: Optional[Any] = None
    error: Optional[ApiError] = None
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True


class VerificationSummary(BaseModel):
    """Type-safe verification summary with full IDE support."""

    total: int
    confirmed: int
    pending: int
    failed: int
    success_rate: float

    class Config:
        populate_by_name = True


class VerificationResults(BaseModel):
    """Type-safe verification results with full IDE support."""

    confirmed: List["TransferInfo"] = Field(default_factory=list)
    failed: List["TransferInfo"] = Field(default_factory=list)
    pending: List["TransferInfo"] = Field(default_factory=list)
    confirmed_deployments: List["DeploymentInfo"] = Field(default_factory=list)
    failed_deployments: List["DeploymentInfo"] = Field(default_factory=list)
    pending_deployments: List["DeploymentInfo"] = Field(default_factory=list)

    class Config:
        populate_by_name = True
