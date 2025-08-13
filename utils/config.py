from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

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

class MinerName(Enum):
    """Enum for type-safe miner name access with IDE autocompletion."""
    MINER1 = "miner1"
    MINER2 = "miner2"
    MINER3 = "miner3"

# The Single Source of Truth for all miner account information.
ACCOUNTS = {
    "miner1": Account(
        name="miner1",
        address="STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6", 
        private_key="cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01",
        api_port=20443
    ),
    "miner2": Account(
        name="miner2",
        address="ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y", 
        private_key="21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601",
        api_port=30443
    ),
    "miner3": Account(
        name="miner3",
        address="ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0", 
        private_key="7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01",
        api_port=40443
    )
}

class AccountManager:
    """Type-safe account access with IDE autocompletion."""
    
    @staticmethod
    def get(miner: MinerName) -> Account:
        """Get account by enum with full IDE autocompletion support."""
        return ACCOUNTS[miner.value]
    
    @staticmethod
    def get_by_name(miner_name: str) -> Optional[Account]:
        """Get account by string name (for backward compatibility)."""
        return ACCOUNTS.get(miner_name)
    
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
    """Type-safe transfer information with IDE autocompletion."""
    miner: str
    to_address: str
    amount: int
    memo: str
    nonce: int
    submitted: bool = False
    txid: Optional[str] = None
    error: Optional[str] = None

@dataclass
class DeploymentInfo:
    """Type-safe deployment information with IDE autocompletion."""
    miner: str
    contract_file: str
    contract_name: str
    nonce: int
    submitted: bool = False
    txid: Optional[str] = None
    error: Optional[str] = None
    size_kb: float = 0.0

@dataclass
class VerificationResults:
    """Type-safe verification results with IDE autocompletion."""
    confirmed: int
    failed: int
    pending: int
    success_rate: float
    confirmed_transfers: list = None
    failed_transfers: list = None
    pending_transfers: list = None
    confirmed_deployments: list = None
    failed_deployments: list = None
    pending_deployments: list = None
    
    def __post_init__(self):
        if self.confirmed_transfers is None:
            self.confirmed_transfers = []
        if self.failed_transfers is None:
            self.failed_transfers = []
        if self.pending_transfers is None:
            self.pending_transfers = []
        if self.confirmed_deployments is None:
            self.confirmed_deployments = []
        if self.failed_deployments is None:
            self.failed_deployments = []
        if self.pending_deployments is None:
            self.pending_deployments = []

