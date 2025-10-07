#!/usr/bin/env python3
"""
Replicate a mainnet transaction on local node.

This script:
1. Fetches a transaction from Hiro mainnet API
2. Extracts the transfer parameters
3. Replicates it on your local Stacks node
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.config import account_manager
from utils.types.infrastructure import Miner
from utils.logger import logger
from utils.stacks_chain import StacksChain
from utils.types.tokens import StacksToken
from utils.templates.recipe import RecipeTemplate
from utils.hiro.hiro_api import HiroAPI


class ReplicateTransactionRecipe(RecipeTemplate):
    def _run_recipe(self) -> bool:
        # Configuration
        ORIGINAL_TX_ID = "0x65e35f27826de006f73f9813b821a1f27a2b93d8d68e13726e69323dfa2b4330"

        logger.header("REPLICATE MAINNET TRANSACTION")

        # Step 1: Fetch original transaction from Hiro mainnet
        logger.header("Step 1: Fetch transaction from mainnet")
        hiro_api = HiroAPI()
        tx = hiro_api.get_transaction_by_id(ORIGINAL_TX_ID)

        logger.info(f"Original TX ID: {ORIGINAL_TX_ID}")
        logger.info(f"Transaction type: {tx.tx_type}")
        logger.info(f"Original sender: {tx.sender_address}")
        logger.info(f"Fee: {tx.fee_rate} µSTX")

        # Extract transfer details from events
        recipient = None
        amount_microstx = None
        memo = None

        for event in tx.events:
            if event.get("event_type") == "stx_asset":
                asset = event.get("asset", {})
                recipient = asset.get("recipient")
                amount_microstx = int(asset.get("amount", 0))
                memo = asset.get("memo", "0x00")

        if not recipient or amount_microstx is None:
            logger.error("Could not extract transfer details from transaction")
            return False

        logger.success(f"Extracted recipient: {recipient}")
        logger.success(f"Extracted amount: {amount_microstx} µSTX")
        logger.success(f"Extracted memo: {memo}")

        # Step 2: Setup local environment
        logger.header("Step 2: Setup local node")
        sender_account = account_manager.get(Miner.MINER1)
        recipient_account = account_manager.get(Miner.MINER2)
        chain = StacksChain(sender_account.api_url)

        if not self.miners.snapshot_restore_auto():
            logger.error("Failed to start miners")
            return False

        logger.info(f"Local sender: {sender_account.address}")
        logger.warning("Note: Mainnet addresses (SP) have different checksums than testnet (ST)")
        logger.info(f"Mainnet recipient: {recipient}")
        logger.info(f"Local recipient: {recipient_account.address}")

        # Step 3: Check initial balances
        logger.header("Step 3: Check initial balances")
        sender_initial = chain.get_stx_balance(sender_account.address)
        recipient_initial = chain.get_stx_balance(recipient_account.address)

        logger.info(f"Sender balance: {sender_initial.format_stx()}")
        logger.info(f"Recipient balance: {recipient_initial.format_stx()}")

        # Step 4: Execute the replicated transfer
        logger.header("Step 4: Execute replicated transfer")
        transfer_amount = StacksToken.from_microstx(amount_microstx)
        transaction_fee = StacksToken.from_microstx(int(tx.fee_rate))

        logger.info(f"Replicating transaction with parameters from mainnet:")
        logger.info(f"Amount (exact): {transfer_amount.format_stx()}")
        logger.info(f"Fee (exact): {transaction_fee.format_stx()}")
        logger.info(f"Memo (exact): {memo}")
        logger.info(f"Recipient: {recipient_account.address} (local testnet address)")

        result = chain.transfer_and_confirm(
            sender_account=sender_account,
            recipient=recipient_account.address,  # Local recipient (address checksums differ)
            amount=transfer_amount,  # Exact amount from mainnet
            memo=memo if memo else "",  # Exact memo from mainnet
            fee=transaction_fee,  # Exact fee from mainnet
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
        if sender_change == expected_sender_change and recipient_change == transfer_amount:
            logger.success("Balances verified correctly!")
        else:
            logger.warning("Balance changes don't match expected values")

        logger.header("SUCCESS")
        logger.success(f"Replicated mainnet transaction {ORIGINAL_TX_ID}")
        logger.success(f"New local transaction: {result.txid}")

        return True


if __name__ == "__main__":
    recipe = ReplicateTransactionRecipe()
    success = recipe.execute()
    sys.exit(0 if success else 1)
