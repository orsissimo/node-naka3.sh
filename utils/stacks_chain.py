#!/usr/bin/env python3

import time
from typing import Optional
from .types.exceptions import *
from .stacks_core_api import StacksCoreAPI
from .blockstack_cli import BlockstackCLI
from .types.tokens import StacksToken
from .logger import logger
from .types.infrastructure import Account, TransactionResult
from .types.api import ReadOnlyFunctionResult


class StacksChain:
    """Façade combining API, CLI for high-level blockchain operations."""

    # TODO: (LATER) La gestione attuale la faccio attraverso un adapter, così se devo ricreare un "sender" e "recipient" li faccio con l'adapter che "autofilla" i parametri
    # TODO: (LATER) Potremmo poi fare l'oggetto chain come oggetto composto da più "chains" così che poi le interrogo in parallelo e do per vera la risposta che ottengo piu volte

    def __init__(self, base_url: str):
        self._api = StacksCoreAPI(base_url=base_url)
        self._cli = BlockstackCLI()

    def get_current_nonce(self, address: str) -> int:
        account_info = self._api.get_account_info(address)
        return account_info.nonce

    def get_current_height(self) -> int:
        node_info = self._api.get_info()
        return node_info.stacks_tip_height

    def get_stx_balance(self, address: str) -> StacksToken:
        account_info = self._api.get_account_info(address)
        return account_info.balance_amount

    def transfer_tokens(
        self,
        sender_account: Account,
        recipient: str,
        amount: StacksToken,
        memo: str = "",
        fee: Optional[StacksToken] = None,
        nonce: Optional[int] = None,
    ) -> str:
        """Transfer tokens with automatic nonce and fee handling."""
        if nonce is None:
            nonce = self.get_current_nonce(sender_account.address)

        if fee is None:
            fee = StacksToken.from_microstx(1_000)

        amount_microstx = amount.to_base_units()
        fee_microstx = fee.to_base_units()

        try:
            tx_hex = self._cli.generate_token_transfer_tx_hex(
                origin_sk=sender_account.private_key,
                fee_rate=fee_microstx,
                nonce=nonce,
                recipient_address=recipient,
                amount=amount_microstx,
                memo=memo if memo else None,
                testnet=True,
            )
        except Exception as e:
            raise StacksException(f"CLI token transfer failed: {str(e)}")

        txid = self._api.post_raw_transaction(bytes.fromhex(tx_hex))

        logger.success(f"Transfer submitted: {txid}")
        return txid

    def wait_for_confirmation(
        self,
        txid: str,
        timeout: int = 120,
        initial_nonce: Optional[int] = None,
        initial_height: Optional[int] = None,
    ) -> bool:
        """Wait for transaction confirmation with smart polling."""

        if initial_nonce is None:
            raise ValueError("initial_nonce must be provided")
        if initial_height is None:
            initial_height = self.get_current_height()

        start_time = time.time()
        last_checked_height = initial_height
        consecutive_failures = 0
        max_consecutive_failures = 5

        while time.time() - start_time < timeout:
            try:
                node_info = self._api.get_info()
                current_height = node_info.stacks_tip_height

                if current_height > last_checked_height:
                    try:
                        logger.debug(
                            f"Checking transaction {txid} at block height {current_height}"
                        )
                        tx_details = self._api.get_transaction_by_id(
                            txid, is_retry_context=True
                        )

                        if tx_details.result and tx_details.result.startswith("(ok "):
                            logger.debug(
                                f"Transaction {txid} successful with result: {tx_details.result}"
                            )
                            logger.success("Transaction confirmed!")
                            return True
                        else:
                            logger.warning(
                                f"Transaction {txid} completed but failed with result: {tx_details.result}"
                            )
                            return False  # Transaction completed but not successful

                    except StacksAPIException as e:
                        if e.is_not_found():
                            logger.debug(
                                f"Transaction {txid} not found yet in block {current_height}"
                            )
                        else:
                            raise

                    last_checked_height = current_height
                    time.sleep(1)
                else:
                    time.sleep(3)

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

        logger.error(f"Transaction confirmation timeout after {timeout}s")
        raise StacksTimeoutException(
            f"Transaction confirmation timeout after {timeout}s"
        )

    def transfer_and_confirm(
        self,
        sender_account: Account,
        recipient: str,
        amount: StacksToken,
        memo: str = "",
        fee: Optional[StacksToken] = None,
        timeout: int = 120,
    ) -> TransactionResult:
        """Transfer tokens and wait for confirmation."""
        initial_nonce = self.get_current_nonce(sender_account.address)
        initial_height = self.get_current_height()

        txid = self.transfer_tokens(
            sender_account=sender_account,
            recipient=recipient,
            amount=amount,
            memo=memo,
            fee=fee,
            nonce=initial_nonce,
        )

        confirmed = self.wait_for_confirmation(
            txid=txid,
            timeout=timeout,
            initial_nonce=initial_nonce,
            initial_height=initial_height,
        )

        return TransactionResult(txid=txid, confirmed=confirmed)

    def deploy_contract(
        self,
        deployer_account: Account,
        contract_name: str,
        contract_file: str,
        fee: Optional[StacksToken] = None,
        nonce: Optional[int] = None,
    ) -> str:
        """Deploy contract with automatic nonce and fee handling."""
        if nonce is None:
            nonce = self.get_current_nonce(deployer_account.address)

        if fee is None:
            fee = StacksToken.from_microstx(50_000)  # Higher default fee for contracts

        fee_microstx = fee.to_base_units()

        try:
            tx_hex = self._cli.generate_contract_deploy_tx_hex(
                publisher_sk=deployer_account.private_key,
                fee_rate=fee_microstx,
                nonce=nonce,
                contract_name=contract_name,
                file_name=contract_file,
                testnet=True,
            )
        except Exception as e:
            raise StacksException(f"CLI contract deployment failed: {str(e)}")

        txid = self._api.post_raw_transaction(bytes.fromhex(tx_hex))

        logger.success(f"Contract deployment submitted: {txid}")
        return txid

    def deploy_and_confirm(
        self,
        deployer_account: Account,
        contract_name: str,
        contract_file: str,
        fee: Optional[StacksToken] = None,
        timeout: int = 120,
    ) -> TransactionResult:
        """Deploy contract and wait for confirmation."""
        initial_nonce = self.get_current_nonce(deployer_account.address)
        initial_height = self.get_current_height()

        txid = self.deploy_contract(
            deployer_account=deployer_account,
            contract_name=contract_name,
            contract_file=contract_file,
            fee=fee,
            nonce=initial_nonce,
        )

        confirmed = self.wait_for_confirmation(
            txid=txid,
            timeout=timeout,
            initial_nonce=initial_nonce,
            initial_height=initial_height,
        )

        return TransactionResult(txid=txid, confirmed=confirmed)

    def call_contract_read_function(
        self,
        contract_address: str,
        contract_name: str,
        function_name: str,
        sender: str,
        function_args: Optional[list] = None,
    ) -> ReadOnlyFunctionResult:
        """Call read-only contract function."""
        return self._api.call_read_only_function(
            contract_address, contract_name, function_name, sender, function_args or []
        )

    def call_contract_write_function(
        self,
        caller_account: Account,
        contract_address: str,
        contract_name: str,
        function_name: str,
        function_args: Optional[list] = None,
        fee: Optional[StacksToken] = None,
        nonce: Optional[int] = None,
    ) -> str:
        """Call contract function (write operation)."""
        if nonce is None:
            nonce = self.get_current_nonce(caller_account.address)

        if fee is None:
            fee = StacksToken.from_microstx(50_000)

        fee_microstx = fee.to_base_units()

        try:
            tx_hex = self._cli.generate_contract_call_tx_hex(
                origin_sk=caller_account.private_key,
                fee_rate=fee_microstx,
                nonce=nonce,
                contract_address=contract_address,
                contract_name=contract_name,
                function_name=function_name,
                args=function_args,
                testnet=True,
            )
        except Exception as e:
            raise StacksException(f"CLI contract call failed: {str(e)}")

        txid = self._api.post_raw_transaction(bytes.fromhex(tx_hex))

        logger.success(f"Contract call submitted: {txid}")
        return txid

    def call_contract_write_function_and_confirm(
        self,
        caller_account: Account,
        contract_address: str,
        contract_name: str,
        function_name: str,
        function_args: Optional[list] = None,
        fee: Optional[StacksToken] = None,
        timeout: int = 120,
    ) -> TransactionResult:
        """Call contract function and wait for confirmation."""
        initial_nonce = self.get_current_nonce(caller_account.address)
        initial_height = self.get_current_height()

        txid = self.call_contract_write_function(
            caller_account=caller_account,
            contract_address=contract_address,
            contract_name=contract_name,
            function_name=function_name,
            function_args=function_args,
            fee=fee,
            nonce=initial_nonce,
        )

        confirmed = self.wait_for_confirmation(
            txid=txid,
            timeout=timeout,
            initial_nonce=initial_nonce,
            initial_height=initial_height,
        )

        return TransactionResult(txid=txid, confirmed=confirmed)
