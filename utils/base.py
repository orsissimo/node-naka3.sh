#!/usr/bin/env python3
"""
Central configuration for the project.

This module contains:
- Project paths (PROJECT_ROOT, PLAYBOOK_DIR)
- Constants (token conversions, timeouts, API settings)
- Account configuration and management
"""

import os
from typing import Dict, List
from .types.stacks.infrastructure import Account, Miner


# Project paths
def _find_project_root():
    """Find project root by looking for the naka3 directory."""
    current = os.path.dirname(os.path.abspath(__file__))
    while current != os.path.dirname(current):  # Stop at filesystem root
        if os.path.exists(os.path.join(current, "naka3")):
            return current
        current = os.path.dirname(current)
    raise RuntimeError("Could not find project root (naka3 directory not found)")


PROJECT_ROOT = _find_project_root()
PLAYBOOK_DIR = os.path.join(PROJECT_ROOT, "naka3", "playbooks", "three-miners")


# Constants
MICROSTX_PER_STX = 1_000_000  # 1 STX = 1,000,000 µSTX
SATOSHI_PER_BTC = 100_000_000  # 1 BTC = 100,000,000 satoshi
DEFAULT_HTTP_TIMEOUT = 20
DEFAULT_API_PORT = 20443
DEFAULT_POLL_INTERVAL = 2
DEFAULT_WAIT_TIMEOUT = 60


# Account configuration
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


class AccountManager:
    """Type-safe account access with encapsulation."""

    def __init__(self):
        self._accounts = _ACCOUNTS.copy()
        self._validate_accounts()

    def _validate_accounts(self):
        if not self._accounts:
            raise ValueError("No accounts configured")
        for key, account in self._accounts.items():
            if not isinstance(key, int) or key <= 0:
                raise ValueError(f"Invalid account key: {key}")
            if not isinstance(account, Account):
                raise TypeError(f"Account {key} is not an Account instance")

    def get(self, miner: Miner) -> Account:
        if not isinstance(miner, Miner):
            raise TypeError("Parameter must be a Miner enum")
        if miner.value not in self._accounts:
            raise ValueError(f"No account found for miner: {miner}")
        return self._accounts[miner.value]

    def all_miners(self) -> List[Miner]:
        return list(Miner)

    def all(self) -> Dict[str, Account]:
        return {account.name: account for account in self._accounts.values()}

    @property
    def account_count(self) -> int:
        return len(self._accounts)


# Global account manager instance
account_manager = AccountManager()
