#!/usr/bin/env python3

import time
from typing import Optional
from .types.exceptions import *
from .stacks_core_api import StacksCoreAPI
from .blockstack_cli import BlockstackCLI
from .types.tokens import StacksToken
from .logger import logger
from .types.infrastructure import Account, TransactionResult
from .types.api import ReadOnlyFunctionResult, AccountInfo


class StacksChain:
    """Façade combining API, CLI for high-level blockchain operations."""

    def __init__(self, base_url: str):
        self._api = StacksCoreAPI(base_url=base_url)
        self._cli = BlockstackCLI()

    def get_account_info(self, address: str) -> AccountInfo:
        return self._api.get_account_info(address)

    def get_stx_balance(self, address: str) -> StacksToken:
        account_info = self._api.get_account_info(address)
        return account_info.balance_amount

    def get_current_nonce(self, address: str) -> int:
        account_info = self._api.get_account_info(address)
        return account_info.nonce

    def get_current_height(self) -> int:
        node_info = self._api.get_info()
        return node_info.stacks_tip_height

    def wait_for_confirmation(
        self,
        txid: str,
        timeout: int = 120,
    ) -> bool:
        initial_height = self.get_current_height()

        start_time = time.time()
        poll_interval = 2

        while time.time() - start_time < timeout:
            try:
                current_height = self.get_current_height()

                if current_height > initial_height:
                    logger.debug(
                        f"Checking transaction {txid} at block height {current_height}"
                    )

                    try:
                        tx_details = self._api.get_transaction_by_id(
                            txid, is_retry_context=True
                        )

                        # Transaction found - check result
                        if tx_details.result and tx_details.result.startswith("(ok "):
                            logger.success(
                                f"Transaction {txid} confirmed successfully!"
                            )
                            return True
                        else:
                            logger.warning(
                                f"Transaction {txid} failed with result: {tx_details.result}"
                            )
                            return False

                    except StacksAPIException as e:
                        if not e.is_not_found():
                            raise  # Re-raise if it's not a "not found" error
                        # Transaction not found yet - continue waiting

                    initial_height = current_height

            except (
                StacksNetworkException,
                StacksTimeoutException,
                StacksAPIException,
            ) as e:
                # Log error but continue trying - network issues are expected
                logger.debug(
                    f"Network error during confirmation wait: {type(e).__name__}"
                )

            time.sleep(poll_interval)

        # Timeout reached
        logger.error(f"Transaction confirmation timeout after {timeout}s")
        raise StacksTimeoutException(
            f"Transaction confirmation timeout after {timeout}s"
        )

    def transfer_tokens(
        self,
        sender_account: Account,
        recipient: str,
        amount: StacksToken,
        memo: str = "",
        fee: Optional[StacksToken] = None,
        nonce: Optional[int] = None,
    ) -> str:
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

    def transfer_and_confirm(
        self,
        sender_account: Account,
        recipient: str,
        amount: StacksToken,
        memo: str = "",
        fee: Optional[StacksToken] = None,
        nonce: Optional[int] = None,
        timeout: int = 120,
    ) -> TransactionResult:
        txid = self.transfer_tokens(
            sender_account=sender_account,
            recipient=recipient,
            amount=amount,
            memo=memo,
            fee=fee,
            nonce=nonce,
        )

        confirmed = self.wait_for_confirmation(
            txid=txid,
            timeout=timeout,
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
        nonce: Optional[int] = None,
        timeout: int = 120,
    ) -> TransactionResult:
        txid = self.deploy_contract(
            deployer_account=deployer_account,
            contract_name=contract_name,
            contract_file=contract_file,
            fee=fee,
            nonce=nonce,
        )

        confirmed = self.wait_for_confirmation(
            txid=txid,
            timeout=timeout,
        )

        return TransactionResult(txid=txid, confirmed=confirmed)

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
        nonce: Optional[int] = None,
        timeout: int = 120,
    ) -> TransactionResult:
        txid = self.call_contract_write_function(
            caller_account=caller_account,
            contract_address=contract_address,
            contract_name=contract_name,
            function_name=function_name,
            function_args=function_args,
            fee=fee,
            nonce=nonce,
        )

        confirmed = self.wait_for_confirmation(
            txid=txid,
            timeout=timeout,
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
        return self._api.call_read_only_function(
            contract_address, contract_name, function_name, sender, function_args or []
        )
