#!/usr/bin/env python3
"""
STX Transfer Example

This script demonstrates:
1. Checking account balances
2. Executing STX transfers
3. Verifying transaction confirmation
"""

import os
import sys

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.base import account_manager
from utils.types.stacks.infrastructure import Miner
from utils.types.stacks.exceptions import *
from utils.logger import logger
from utils.stacks.stacks_chain import StacksChain
from utils.types.tokens import StacksToken
from utils.asserts import check_eq
from utils.templates.recipe import RecipeTemplate


class TransferRecipe(RecipeTemplate):
    def _run_recipe(self) -> bool:
        logger.header("STX TOKEN TRANSFER TEST")

        sender_account = account_manager.get(Miner.MINER1)
        recipient_account = account_manager.get(Miner.MINER2)
        chain = StacksChain(sender_account.api_url)

        if not self.miners.snapshot_restore_auto():
            raise StacksException("Failed to start miners")

        logger.header("Step 1: Check initial balances")
        sender_initial_balance = chain.get_stx_balance(sender_account.address)
        recipient_initial_balance = chain.get_stx_balance(recipient_account.address)

        logger.info(f"Sender address: {sender_account.address}")
        logger.info(f"Sender initial balance: {sender_initial_balance.format_stx()}")
        logger.info(f"Recipient address: {recipient_account.address}")
        logger.info(
            f"Recipient initial balance: {recipient_initial_balance.format_stx()}"
        )

        logger.header("Step 2: Prepare transfer")
        transfer_amount = StacksToken.from_microstx(50_000)
        transfer_memo = "Test transfer from example"
        transaction_fee = StacksToken.from_microstx(1_000)

        initial_nonce = chain.get_current_nonce(sender_account.address)

        logger.info(f"Transfer amount: {transfer_amount.format_stx()}")
        logger.info(f"Transfer memo: {transfer_memo}")
        logger.info(f"Transaction fee: {transaction_fee.format_stx()}")
        logger.info(f"Sender nonce: {initial_nonce}")

        logger.header("Step 3: Execute transfer and wait for confirmation")
        result = chain.transfer_and_confirm(
            sender_account=sender_account,
            recipient=recipient_account.address,
            amount=transfer_amount,
            memo=transfer_memo,
            fee=transaction_fee,
            timeout=120,
        )

        if result.confirmed:
            logger.success(f"Main transfer confirmed: {result.txid}")
        else:
            logger.error(
                f"Main transfer submitted but confirmation failed: {result.txid}"
            )
            raise RecipeFailedException(
                "Main transfer confirmation failed",
                step="transfer_confirmation",
                details=f"Transaction {result.txid} was submitted but not confirmed within timeout",
            )

        logger.header("Step 4: Verify final balances")
        sender_final_balance = chain.get_stx_balance(sender_account.address)
        recipient_final_balance = chain.get_stx_balance(recipient_account.address)

        sender_change = sender_final_balance - sender_initial_balance
        recipient_change = recipient_final_balance - recipient_initial_balance
        expected_sender_change = -(transfer_amount + transaction_fee)

        logger.info(f"Sender final balance: {sender_final_balance.format_stx()}")
        logger.info(f"Sender balance change: {sender_change.format_stx()}")
        logger.info(f"Recipient final balance: {recipient_final_balance.format_stx()}")
        logger.info(f"Recipient balance change: {recipient_change.format_stx()}")

        logger.header("Step 5: Validate transfer amounts")
        check_eq(expected_sender_change, sender_change, "Sender balance change")
        check_eq(transfer_amount, recipient_change, "Recipient balance change")

        logger.header("Step 6: Test multiple small transfers")
        for i in range(3):
            small_amount = StacksToken.from_microstx(
                1_000 * (i + 1)
            )  # 1000, 2000, 3000 µSTX
            small_memo = f"Small transfer #{i+1}"

            try:
                result = chain.transfer_and_confirm(
                    sender_account=sender_account,
                    recipient=recipient_account.address,
                    amount=small_amount,
                    memo=small_memo,
                    fee=transaction_fee,
                    timeout=120,
                )
                if result.confirmed:
                    logger.success(f"Transfer #{i+1} completed: {result.txid}")
                else:
                    logger.error(
                        f"Transfer #{i+1} submitted but confirmation failed: {result.txid}"
                    )
                    raise RecipeFailedException(
                        f"Small transfer #{i+1} confirmation failed",
                        step=f"small_transfer_{i+1}_confirmation",
                        details=f"Transaction {result.txid} was submitted but not confirmed within timeout",
                    )
            except StacksTimeoutException:
                logger.error(f"Transfer #{i+1} confirmation timeout")
            except StacksException as e:
                logger.error(f"Transfer #{i+1} failed: {str(e)}")
                continue

        logger.header("SUMMARY")
        final_sender_balance = chain.get_stx_balance(sender_account.address)
        final_recipient_balance = chain.get_stx_balance(recipient_account.address)
        total_sender_change = final_sender_balance - sender_initial_balance
        total_recipient_change = final_recipient_balance - recipient_initial_balance

        total_transferred = transfer_amount + StacksToken.from_microstx(6_000)

        logger.info(f"Total amount transferred: {total_transferred.format_stx()}")
        logger.info(f"Total sender change: {total_sender_change.format_stx()}")
        logger.info(f"Total recipient gain: {total_recipient_change.format_stx()}")

        check_eq(
            total_transferred,
            total_recipient_change,
            "Total recipient gain matches total transferred",
        )

        return True


if __name__ == "__main__":
    recipe = TransferRecipe()
    success = recipe.execute()
    sys.exit(0 if success else 1)
