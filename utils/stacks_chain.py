#!/usr/bin/env python3

from typing import Optional, Union
from .config import Account, StacksException, StacksTimeoutException
from .stacks_core_api import StacksCoreAPI
from .blockstack_cli import BlockstackCLI
from .tokens import TokenAmount, standard_fee
from .logger import logger


class StacksChain:
    """
    Façade that combines API, CLI and Wrapper for high-level blockchain operations.
    Provides convenient methods that coordinate multiple components automatically.
    
    Philosophy: Keep underlying components simple and focused, put the "fancy" 
    convenience operations here.
    """

    def __init__(self, account: Account):
        """Initialize façade with all necessary components."""
        self._account = self._validate_account(account)
        self._api = StacksCoreAPI(base_url=account.api_url)
        self._cli = BlockstackCLI()

    def _validate_account(self, account: Account) -> Account:
        """Validate account parameter."""
        if not account:
            raise ValueError("Account cannot be None")
        if not isinstance(account, Account):
            raise TypeError("Account must be an Account instance")
        return account

    @property
    def account(self) -> Account:
        """Get the associated account (read-only)."""
        return self._account

    @property 
    def api(self) -> StacksCoreAPI:
        """Get the raw API instance for direct access when needed."""
        return self._api

    @property
    def cli(self) -> BlockstackCLI:
        """Get the raw CLI for direct access when needed."""
        return self._cli


    def get_current_nonce(self) -> int:
        """Get current nonce for the account - convenience method."""
        account_info = self._api.get_account_info(self._account.address)
        return account_info.nonce

    def get_current_height(self) -> int:
        """Get current block height - convenience method."""
        node_info = self._api.get_info()
        return node_info.stacks_tip_height

    def get_balance(self) -> TokenAmount:
        """Get current balance as StacksAmount - convenience method."""
        account_info = self._api.get_account_info(self._account.address)
        return account_info.balance_amount

    def transfer_tokens(
        self,
        recipient: str,
        amount: TokenAmount,
        memo: str = "",
        fee: Optional[TokenAmount] = None,
        nonce: Optional[int] = None,
    ) -> str:
        """
        Transfer tokens with automatic nonce and fee handling.
        
        Args:
            recipient: Recipient address
            amount: Transfer amount as TokenAmount
            memo: Optional memo
            fee: Transaction fee (defaults to standard fee)
            nonce: Transaction nonce (auto-fetched if not provided)
            
        Returns:
            Transaction ID (txid)
            
        Raises:
            StacksException: If transfer fails
        """
        # Auto-fetch nonce if not provided
        if nonce is None:
            nonce = self.get_current_nonce()
            
        # Use standard fee if not provided
        if fee is None:
            fee = standard_fee()

        # Convert TokenAmount to base units for CLI
        amount_microstx = amount.to_base_units()
        fee_microstx = fee.to_base_units()

        # Execute transfer using raw CLI
        try:
            tx_hex = self._cli.token_transfer(
                origin_sk=self._account.private_key,
                fee_rate=fee_microstx,
                nonce=nonce,
                recipient_address=recipient,
                amount=amount_microstx,
                memo=memo if memo else None,
                testnet=True,
            )
        except Exception as e:
            raise StacksException(f"CLI token transfer failed: {str(e)}")

        # Submit transaction to blockchain
        txid = self._api.post_raw_transaction(bytes.fromhex(tx_hex))
        
        logger.success(f"Transfer submitted: {txid}")
        return txid

    def wait_for_confirmation(
        self, 
        txid: str, 
        timeout: int = 120,
        initial_nonce: Optional[int] = None,
        initial_height: Optional[int] = None
    ) -> bool:
        """
        Wait for transaction confirmation with automatic parameter handling.
        This is a compound operation that coordinates API calls with smart polling.
        
        Args:
            txid: Transaction ID to wait for
            timeout: Timeout in seconds
            initial_nonce: Initial nonce (auto-fetched if not provided)
            initial_height: Initial height (auto-fetched if not provided)
            
        Returns:
            True if confirmed
            
        Raises:
            StacksTimeoutException: If confirmation times out
        """
        import time
        from .config import StacksNetworkException, StacksAPIException, StacksTimeoutException
        
        # Auto-fetch parameters if not provided
        if initial_nonce is None:
            initial_nonce = self.get_current_nonce()
        if initial_height is None:
            initial_height = self.get_current_height()

        start_time = time.time()
        last_checked_height = initial_height
        consecutive_failures = 0
        max_consecutive_failures = 5

        while time.time() - start_time < timeout:
            try:
                # Get current node info using raw API
                node_info = self._api.get_info()
                current_height = node_info.stacks_tip_height

                # Only check transaction when block height increases (more efficient)
                if current_height > last_checked_height:
                    try:
                        # Check transaction result using raw API
                        logger.debug(
                            f"Checking transaction {txid} at block height {current_height}"
                        )
                        tx_details = self._api.get_transaction_by_id(txid, is_retry_context=True)

                        # Check if transaction has result field with '(ok true)'
                        if tx_details.result == "(ok true)":
                            logger.debug(
                                f"Transaction {txid} successful with result: '(ok true)'"
                            )
                            logger.success("Transfer confirmed!")
                            return True
                        else:
                            logger.debug(
                                f"Transaction {txid} completed with result: {tx_details.result}"
                            )
                            return False  # Transaction completed but not successful

                    except StacksAPIException as e:
                        # Transaction not found yet
                        if "404" in str(e):
                            logger.debug(
                                f"Transaction {txid} not found yet in block {current_height}"
                            )
                        else:
                            raise  # Re-raise non-404 errors

                    last_checked_height = current_height
                    # Short sleep after block change
                    time.sleep(1)
                else:
                    # Longer sleep when no new blocks (more efficient)
                    time.sleep(3)

                # Reset failure counter on success
                consecutive_failures = 0

            except (StacksNetworkException, StacksTimeoutException) as e:
                consecutive_failures += 1
                if consecutive_failures < max_consecutive_failures:
                    logger.warning(
                        f"Network error during confirmation wait (retrying {consecutive_failures}/{max_consecutive_failures}): {type(e).__name__}"
                    )
                else:
                    logger.error(
                        f"Network error during confirmation wait (final failure {consecutive_failures}/{max_consecutive_failures}): {e}"
                    )
                    raise StacksNetworkException(
                        f"Too many consecutive network failures during confirmation wait: {e}"
                    ) from e

                time.sleep(2)
            except StacksAPIException as e:
                consecutive_failures += 1
                if consecutive_failures < max_consecutive_failures:
                    logger.warning(
                        f"API error during confirmation wait (retrying {consecutive_failures}/{max_consecutive_failures}): {type(e).__name__}"
                    )
                else:
                    logger.error(
                        f"API error during confirmation wait (final failure {consecutive_failures}/{max_consecutive_failures}): {e}"
                    )
                    raise StacksAPIException(
                        f"Too many consecutive API failures during confirmation wait: {e}"
                    ) from e

                time.sleep(2)

        logger.error(
            f"Transaction confirmation timeout after {timeout}s for account {self._account.address}"
        )
        raise StacksTimeoutException(
            f"Transaction confirmation timeout after {timeout}s for account {self._account.address}"
        )

    def transfer_and_confirm(
        self,
        recipient: str,
        amount: TokenAmount,
        memo: str = "",
        fee: Optional[TokenAmount] = None,
        timeout: int = 120,
    ) -> str:
        """
        Transfer tokens and wait for confirmation - atomic operation.
        
        Args:
            recipient: Recipient address
            amount: Transfer amount
            memo: Optional memo
            fee: Transaction fee (defaults to standard)
            timeout: Confirmation timeout in seconds
            
        Returns:
            Transaction ID (txid)
            
        Raises:
            StacksException: If transfer fails
            StacksTimeoutException: If confirmation times out
        """
        # Capture initial state
        initial_nonce = self.get_current_nonce()
        initial_height = self.get_current_height()
        
        # Execute transfer
        txid = self.transfer_tokens(
            recipient=recipient,
            amount=amount,
            memo=memo,
            fee=fee,
            nonce=initial_nonce
        )
        
        # Wait for confirmation
        self.wait_for_confirmation(
            txid=txid,
            timeout=timeout,
            initial_nonce=initial_nonce,
            initial_height=initial_height
        )
        
        return txid