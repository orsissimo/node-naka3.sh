#!/usr/bin/env python3

import os
import sys
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.config import account_manager, Miner
from utils.exceptions import *
from utils.miners import MinerManager
from utils.logger import logger, Colors
from utils.stacks_chain import StacksChain
from utils.tokens import TokenAmount, StacksToken
from utils.asserts import check_eq


def main():
    logger.header("STX TOKEN TRANSFER TEST")

    miners = MinerManager()
    sender_account = account_manager.get(Miner.MINER1)
    recipient_account = account_manager.get(Miner.MINER2)
    chain = StacksChain(sender_account.api_url)

    try:
        logger.info("Starting miners...")
        if not miners.snapshot_restore_auto():
            raise StacksException("Failed to start miners")

        logger.header("Step 1: Check initial balances")
        sender_initial_balance = chain.get_balance(sender_account.address)
        recipient_initial_balance = chain.get_balance(recipient_account.address)

        logger.info(f"Sender address: {sender_account.address}")
        logger.info(f"Sender initial balance: {sender_initial_balance}")
        logger.info(f"Recipient address: {recipient_account.address}")
        logger.info(f"Recipient initial balance: {recipient_initial_balance}")

        logger.header("Step 2: Prepare transfer")
        transfer_amount = StacksToken.from_microstx(50_000)
        transfer_memo = "Test transfer from example"
        transaction_fee = StacksToken.from_microstx(1_000)

        initial_nonce = chain.get_current_nonce(sender_account.address)
        initial_height = chain.get_current_height()

        logger.info(f"Transfer amount: {transfer_amount}")
        logger.info(f"Transfer memo: {transfer_memo}")
        logger.info(f"Transaction fee: {transaction_fee}")
        logger.info(f"Sender nonce: {initial_nonce}")

        logger.header("Step 3: Execute transfer")
        transfer_txid = chain.transfer_tokens(
            sender_account=sender_account,
            recipient=recipient_account.address,
            amount=transfer_amount,
            memo=transfer_memo,
            fee=transaction_fee,
            nonce=initial_nonce,
        )

        logger.header("Step 4: Wait for confirmation")
        chain.wait_for_confirmation(
            txid=transfer_txid,
            timeout=120,
            initial_nonce=initial_nonce,
            initial_height=initial_height,
        )

        logger.header("Step 5: Verify final balances")
        sender_final_balance = chain.get_balance(sender_account.address)
        recipient_final_balance = chain.get_balance(recipient_account.address)

        sender_change = sender_final_balance - sender_initial_balance
        recipient_change = recipient_final_balance - recipient_initial_balance
        expected_sender_change = -(transfer_amount + transaction_fee)

        logger.info(f"Sender final balance: {sender_final_balance}")
        logger.info(f"Sender balance change: {sender_change}")
        logger.info(f"Recipient final balance: {recipient_final_balance}")
        logger.info(f"Recipient balance change: {recipient_change}")

        logger.header("Step 6: Validate transfer amounts")

        check_eq(expected_sender_change, sender_change, "Sender balance change")

        check_eq(transfer_amount, recipient_change, "Recipient balance change")

        logger.header("Step 7: Test multiple small transfers")

        for i in range(3):
            small_amount = StacksToken.from_microstx(
                1_000 * (i + 1)
            )  # 1000, 2000, 3000 µSTX
            small_memo = f"Small transfer #{i+1}"

            try:
                small_txid = chain.transfer_and_confirm(
                    sender_account=sender_account,
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

        logger.header("FINAL RESULT")

        final_sender_balance = chain.get_balance(sender_account.address)
        final_recipient_balance = chain.get_balance(recipient_account.address)
        total_sender_change = final_sender_balance - sender_initial_balance
        total_recipient_change = final_recipient_balance - recipient_initial_balance

        total_transferred = transfer_amount + StacksToken.from_microstx(6_000)

        logger.info(f"Main transfer TXID: {transfer_txid}")
        logger.info(f"Total amount transferred: {total_transferred}")
        logger.info(f"Total sender change: {total_sender_change}")
        logger.info(f"Total recipient gain: {total_recipient_change}")

        check_eq(
            total_transferred,
            total_recipient_change,
            "Total recipient gain matches total transferred",
        )

        return True

    except Exception as e:
        logger.error(f"TEST FAILED - Unexpected Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

    finally:
        logger.header("Cleaning up...")
        miners.stop()
        miners.cleanup()


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)

# TODO: (LATER): Potrei partire da alcuni test base (che estendono da alcuni file) - Che fanno da "template"
