#!/usr/bin/env python3

import os
import sys
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import wait_for_confirmation
from utils.config import AccountManager, Miner
from utils.miners import MinerManager
from utils.logger import logger
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.stacks_core_api import StacksCoreAPI, StacksCoreAPIWrapper

def main():
    """Execute STX token transfer test"""
    logger.header('STX TOKEN TRANSFER TEST')
    
    # Raw minimal setup
    # FIXME: (LATER): Potrei creare un type "Setup" che ha cli, api, minermanager, ...
    miners = MinerManager()
    sender_account = AccountManager.get(Miner.MINER1)
    recipient_account = AccountManager.get(Miner.MINER2)
    api = StacksCoreAPI(base_url=sender_account.api_url)
    api_wrapper = StacksCoreAPIWrapper(api)
    cli = BlockstackCLIWrapper()
    
    try:
        # Start the node
        logger.stacks('Starting miners...')
        if not miners.snapshot_restore_auto():
            raise RuntimeError("Failed to start miners")
        
        # Step 1: Check initial balances
        logger.header('Step 1: Check initial balances')
        sender_account_info = api.get_account_info(sender_account.address)
        sender_initial_balance = sender_account_info.balance
        recipient_account_info = api.get_account_info(recipient_account.address)
        recipient_initial_balance = recipient_account_info.balance

        logger.standard('Sender address', sender_account.address)
        logger.standard('Sender initial balance', sender_initial_balance, 'µSTX')
        logger.standard('Recipient address', recipient_account.address)
        logger.standard('Recipient initial balance', recipient_initial_balance, 'µSTX')
        
        # Step 2: Prepare transfer
        logger.header('Step 2: Prepare transfer')
        transfer_amount = 50000  # 50,000 µSTX
        transfer_memo = "Test transfer from example"
        fee = 1000  # Transaction fee in µSTX (CLI default)
        
        sender_account_info = api.get_account_info(sender_account.address)
        initial_nonce = sender_account_info.nonce
        initial_height = api_wrapper.get_block_height()
        
        logger.standard('Transfer amount', transfer_amount, 'µSTX')
        logger.standard('Transfer memo', transfer_memo)
        logger.standard('Transaction fee', fee, 'µSTX')
        logger.standard('Sender nonce', initial_nonce)
        
        # Step 3: Execute transfer
        logger.header('Step 3: Execute transfer')
        cli_result = cli.transfer_tokens(
            sender_account.private_key,  # Private key for signing
            recipient_account.address,   # Recipient address
            transfer_amount / 1_000_000, # Amount in STX (convert from µSTX)
            transfer_memo,              # Transfer memo
            initial_nonce,              # Current nonce
            fee                         # Transaction fee
        )
        
        if not cli_result.success:
            raise RuntimeError(f"Token transfer failed: {cli_result.error}")
        tx_hex = cli_result.data.tx_hex
        
        transfer_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        logger.success(f"Transfer submitted: {transfer_txid}")
        
        # Step 4: Wait for confirmation
        logger.header('Step 4: Wait for confirmation')
        if not wait_for_confirmation(api, sender_account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Transfer confirmation timeout")
        logger.success('Transfer confirmed!')
        
        # Step 5: Verify final balances
        logger.header('Step 5: Verify final balances')
        sender_account_info = api.get_account_info(sender_account.address)
        sender_final_balance = sender_account_info.balance
        recipient_account_info = api.get_account_info(recipient_account.address)
        recipient_final_balance = recipient_account_info.balance
        
        sender_change = sender_final_balance - sender_initial_balance
        recipient_change = recipient_final_balance - recipient_initial_balance
        expected_sender_change = -(transfer_amount + fee)
        
        logger.standard('Sender final balance', sender_final_balance, 'µSTX')
        logger.standard('Sender balance change', sender_change, 'µSTX')
        logger.standard('Recipient final balance', recipient_final_balance, 'µSTX')
        logger.standard('Recipient balance change', recipient_change, 'µSTX')
        
        # Step 6: Validate transfer amounts
        logger.header('Step 6: Validate transfer amounts')
        
        # Sender should have lost: transfer_amount + fee
        if sender_change == expected_sender_change:
            logger.success(f"Sender balance change correct: {expected_sender_change:,} µSTX")
        else:
            logger.error('Sender balance change incorrect')
            logger.info(f"  Expected: {expected_sender_change:,} µSTX")
            logger.info(f"  Actual: {sender_change:,} µSTX")
        
        # Recipient should have gained: transfer_amount
        if recipient_change == transfer_amount:
            logger.success(f"Recipient balance change correct: +{transfer_amount:,} µSTX")
        else:
            logger.error('Recipient balance change incorrect')
            logger.info(f"  Expected: +{transfer_amount:,} µSTX")
            logger.info(f"  Actual: +{recipient_change:,} µSTX")
        
        # Step 7: Test multiple small transfers
        logger.header('Step 7: Test multiple small transfers')
        
        for i in range(3):
            small_amount = 1000 * (i + 1)  # 1000, 2000, 3000 µSTX
            small_memo = f"Small transfer #{i+1}"
            
            sender_account_info = api.get_account_info(sender_account.address)
            current_nonce = sender_account_info.nonce
            current_height = api_wrapper.get_block_height()
            
            cli_result = cli.transfer_tokens(
                sender_account.private_key,
                recipient_account.address,
                small_amount / 1_000_000,  # Convert µSTX to STX
                small_memo,
                current_nonce,  # Use current nonce
                fee            # Use same fee
            )
            
            if not cli_result.success:
                logger.error(f'Transfer #{i+1} failed: {cli_result.error}')
                continue
            tx_hex = cli_result.data.tx_hex
            
            small_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
            logger.success(f"Transfer #{i+1} submitted: {small_txid} - {small_amount:,} µSTX")
            
            if not wait_for_confirmation(api, sender_account.address, current_nonce, current_height, timeout=120):
                logger.error(f'Transfer #{i+1} confirmation timeout')
            else:
                logger.success(f'Transfer #{i+1} confirmed')
        
        # Final summary
        logger.header('FINAL RESULT')
        
        sender_account_info = api.get_account_info(sender_account.address)
        final_sender_balance = sender_account_info.balance
        recipient_account_info = api.get_account_info(recipient_account.address)
        final_recipient_balance = recipient_account_info.balance
        total_sender_change = final_sender_balance - sender_initial_balance
        total_recipient_change = final_recipient_balance - recipient_initial_balance
        
        logger.standard('Main transfer TXID', transfer_txid)
        logger.standard('Total amount transferred', transfer_amount + 6000, 'µSTX')  # Main + 3 small transfers
        logger.standard('Total sender change', total_sender_change, 'µSTX')
        logger.standard('Total recipient gain', total_recipient_change, 'µSTX')
        
        return True
        
    # FIXME: Tenere try catch finale ma gli faccio risalire le eccezioni dai livelli piu bassi, eccetto eccezioni come socket IO per esempio, che "blocco" in componenti piu bassi (in /utils)
    except Exception as e:
        logger.error(f'TEST FAILED: {str(e)}')
        return False
        
    finally:
        # Cleanup
        logger.header('Cleaning up...')
        miners.stop()
        miners.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)