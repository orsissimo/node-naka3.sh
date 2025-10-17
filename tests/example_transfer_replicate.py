#!/usr/bin/env python3
"""
Token Transfer Replication Example

This script demonstrates:
1. Fetching a token transfer transaction from mainnet
2. Extracting transfer parameters
3. Replicating the transfer on local Stacks node
4. Verifying balances
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.logger import logger
from utils.base import account_manager, PROJECT_ROOT
from utils.types.stacks.infrastructure import Miner
from utils.stacks.stacks_chain import StacksChain
from utils.types.tokens import StacksToken
from utils.hiro.json_handler import TransactionHandler
from utils.templates.recipe import RecipeTemplate


class ReplicateTransferRecipe(RecipeTemplate):
    """Recipe for replicating a token transfer from mainnet."""

    def _run_recipe(self) -> bool:
        # Start miners
        if not self.miners.snapshot_restore_auto():
            logger.error("Failed to start miners")
            return False

        logger.header("REPLICATING TOKEN TRANSFER FROM MAINNET")

        # Step 1: Fetch and extract transaction data
        logger.header("Step 1: Fetch mainnet data")
        TARGET_TX_ID = "0x65e35f27826de006f73f9813b821a1f27a2b93d8d68e13726e69323dfa2b4330"

        handler = TransactionHandler(TARGET_TX_ID)
        tmp_dir = os.path.join(PROJECT_ROOT, "tmp")
        metadata, data_file = handler.fetch_extract_and_save(tmp_dir)

        if metadata is None:
            logger.error("Failed to fetch transaction metadata")
            return False

        # Ensure this is a token transfer
        from utils.types.hiro.infrastructure import TransferMetadata
        if not isinstance(metadata, TransferMetadata):
            logger.error(f"Expected token transfer, got {type(metadata).__name__}")
            return False

        transfer_metadata = metadata

        logger.info(f"Sender: {transfer_metadata.sender_address}")
        logger.info(f"Recipient: {transfer_metadata.recipient_address}")
        logger.info(f"Amount: {transfer_metadata.amount} µSTX")
        logger.info(f"Memo: {transfer_metadata.memo}")
        logger.info(f"Fee: {transfer_metadata.fee} µSTX")
        logger.success(f"Data loaded and saved to: {data_file}")

        # Setup local environment
        logger.header("Step 2: Setup local environment")
        sender_account = account_manager.get(Miner.MINER1)
        recipient_account = account_manager.get(Miner.MINER2)
        chain = StacksChain(sender_account.api_url)

        logger.info(f"Mainnet sender: {transfer_metadata.sender_address}")
        logger.info(f"Mainnet recipient: {transfer_metadata.recipient_address}")
        logger.warning(
            "Note: Mainnet addresses (SP) have different checksums than testnet (ST)"
        )
        logger.info(f"Local sender: {sender_account.address}")
        logger.info(f"Local recipient: {recipient_account.address}")

        # Step 3: Check initial balances
        logger.header("Step 3: Check initial balances")
        sender_initial = chain.get_stx_balance(sender_account.address)
        recipient_initial = chain.get_stx_balance(recipient_account.address)

        logger.info(f"Sender balance: {sender_initial.format_stx()}")
        logger.info(f"Recipient balance: {recipient_initial.format_stx()}")

        # Step 4: Execute the replicated transfer
        logger.header("Step 4: Execute replicated transfer")
        transfer_amount = StacksToken.from_microstx(int(transfer_metadata.amount))
        transaction_fee = StacksToken.from_microstx(int(transfer_metadata.fee))

        logger.info(f"Replicating transfer with exact mainnet parameters:")
        logger.info(f"Amount: {transfer_amount.format_stx()}")
        logger.info(f"Fee: {transaction_fee.format_stx()}")
        logger.info(f"Memo: {transfer_metadata.memo}")

        result = chain.transfer_and_confirm(
            sender_account=sender_account,
            recipient=recipient_account.address,
            amount=transfer_amount,
            memo=transfer_metadata.memo if transfer_metadata.memo else "",
            fee=transaction_fee,
            timeout=120,
        )

        if not result.confirmed:
            logger.error(f"Transfer failed: {result.txid}")
            return False

        logger.success(f"Transfer confirmed: {result.txid}")

        # Step 5: Verify final balances
        logger.header("Step 5: Verify final balances")
        sender_final = chain.get_stx_balance(sender_account.address)
        recipient_final = chain.get_stx_balance(recipient_account.address)

        sender_change = sender_final - sender_initial
        recipient_change = recipient_final - recipient_initial

        logger.info(f"Sender balance: {sender_final.format_stx()}")
        logger.info(f"Sender change: {sender_change.format_stx()}")
        logger.info(f"Recipient balance: {recipient_final.format_stx()}")
        logger.info(f"Recipient change: {recipient_change.format_stx()}")

        # Verify amounts match
        expected_sender_change = -(transfer_amount + transaction_fee)
        balances_verified = (
            sender_change == expected_sender_change
            and recipient_change == transfer_amount
        )

        if balances_verified:
            logger.success("Balances verified correctly!")
        else:
            logger.warning("Balance changes don't match expected values")

        logger.header("REPLICATION COMPLETE")
        logger.success(f"Replicated mainnet transaction {TARGET_TX_ID}")
        logger.success(f"New local transaction: {result.txid}")

        return balances_verified


if __name__ == "__main__":
    recipe = ReplicateTransferRecipe()
    success = recipe.execute()
    sys.exit(0 if success else 1)
