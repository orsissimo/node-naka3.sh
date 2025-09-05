#!/usr/bin/env python3

import os
import sys
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.config import (
    account_manager,
    Miner,
    StacksException,
    StacksAPIException,
    StacksCLIException,
    StacksValidationException,
    StacksNetworkException,
    StacksTimeoutException,
    RecipeFailedException,
)
from utils.miners import MinerManager
from utils.logger import logger, Colors
from utils.stacks_chain import StacksChain
from utils.tokens import TokenAmount, standard_fee, stx, microstx


def main():
    """Execute STX token transfer test"""
    logger.header("STX TOKEN TRANSFER TEST")

    miners = MinerManager()
    sender_account = account_manager.get(Miner.MINER1)
    recipient_account = account_manager.get(Miner.MINER2)
    sender = StacksChain(sender_account)
    recipient = StacksChain(recipient_account)

    try:
        # Start the node
        logger.info("Starting miners...")
        if not miners.snapshot_restore_auto():
            raise StacksException("Failed to start miners")

        # Step 1: Check initial balances
        logger.header("Step 1: Check initial balances")
        sender_initial_balance = sender.get_balance()
        recipient_initial_balance = recipient.get_balance()

        logger.info(f"Sender address: {sender_account.address}")
        logger.info(f"Sender initial balance: {sender_initial_balance}")
        logger.info(f"Recipient address: {recipient_account.address}")
        logger.info(f"Recipient initial balance: {recipient_initial_balance}")

        # Step 2: Prepare transfer
        logger.header("Step 2: Prepare transfer")
        transfer_amount = microstx(50000)  # 50,000 µSTX
        transfer_memo = "Test transfer from example"
        transaction_fee = standard_fee()  # 1000 µSTX

        initial_nonce = sender.get_current_nonce()
        initial_height = sender.get_current_height()

        logger.info(f"Transfer amount: {transfer_amount}")
        logger.info(f"Transfer memo: {transfer_memo}")
        logger.info(f"Transaction fee: {transaction_fee}")
        logger.info(f"Sender nonce: {initial_nonce}")

        # Step 3: Execute transfer
        logger.header("Step 3: Execute transfer")
        try:
            transfer_txid = sender.transfer_tokens(
                recipient=recipient_account.address,
                amount=transfer_amount,
                memo=transfer_memo,
                fee=transaction_fee,
                nonce=initial_nonce,  # Explicit for this demo
            )
        except StacksException as e:
            raise RecipeFailedException(
                "Main token transfer failed",
                step="Step 3: Execute transfer",
                details=str(e),
            )

        # Step 4: Wait for confirmation
        logger.header("Step 4: Wait for confirmation")
        sender.wait_for_confirmation(
            txid=transfer_txid,
            timeout=120,
            initial_nonce=initial_nonce,
            initial_height=initial_height,
        )

        # Step 5: Verify final balances
        logger.header("Step 5: Verify final balances")
        sender_final_balance = sender.get_balance()
        recipient_final_balance = recipient.get_balance()

        sender_change = sender_final_balance - sender_initial_balance
        recipient_change = recipient_final_balance - recipient_initial_balance
        expected_sender_change = -(transfer_amount + transaction_fee)

        logger.info(f"Sender final balance: {sender_final_balance}")
        logger.info(f"Sender balance change: {sender_change}")
        logger.info(f"Recipient final balance: {recipient_final_balance}")
        logger.info(f"Recipient balance change: {recipient_change}")

        # Step 6: Validate transfer amounts
        logger.header("Step 6: Validate transfer amounts")

        # Sender should have lost: transfer_amount + transaction_fee
        if sender_change == expected_sender_change:
            logger.success(f"Sender balance change correct: {expected_sender_change}")
        else:
            logger.error("Sender balance change incorrect")
            logger.info(f"  Expected: {expected_sender_change}")
            logger.info(f"  Actual: {sender_change}")

        # Recipient should have gained: transfer_amount
        if recipient_change == transfer_amount:
            logger.success(f"Recipient balance change correct: +{transfer_amount}")
        else:
            logger.error("Recipient balance change incorrect")
            logger.info(f"  Expected: +{transfer_amount}")
            logger.info(f"  Actual: +{recipient_change}")

        # Step 7: Test multiple small transfers
        logger.header("Step 7: Test multiple small transfers")

        for i in range(3):
            small_amount = microstx(1000 * (i + 1))  # 1000, 2000, 3000 µSTX
            small_memo = f"Small transfer #{i+1}"

            current_nonce = sender.get_current_nonce()
            current_height = sender.get_current_height()

            try:
                small_txid = sender.transfer_and_confirm(
                    recipient=recipient_account.address,
                    amount=small_amount,
                    memo=small_memo,
                    fee=transaction_fee,
                    timeout=120,
                )
                logger.success(f"Transfer #{i+1} completed: {small_txid}")
            except StacksTimeoutException:
                logger.error(f"Transfer #{i+1} confirmation timeout")
            except StacksException as e:
                logger.error(f"Transfer #{i+1} failed: {str(e)}")
                continue

        # Final summary
        logger.header("FINAL RESULT")

        final_sender_balance = sender.get_balance()
        final_recipient_balance = recipient.get_balance()
        total_sender_change = final_sender_balance - sender_initial_balance
        total_recipient_change = final_recipient_balance - recipient_initial_balance

        total_transferred = transfer_amount + microstx(6000)  # Main + 3 small transfers

        logger.info(f"Main transfer TXID: {transfer_txid}")
        logger.info(f"Total amount transferred: {total_transferred}")
        logger.info(f"Total sender change: {total_sender_change}")
        logger.info(f"Total recipient gain: {total_recipient_change}")

        return True

    except Exception as e:
        logger.error(f"TEST FAILED - Unexpected Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

    finally:
        # Cleanup
        logger.header("Cleaning up...")
        miners.stop()
        miners.cleanup()


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)

# TODO: (LATER): Potrei partire da alcuni test base (che estendono da alcuni file) - Che fanno da "template"
