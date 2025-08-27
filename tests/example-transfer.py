#!/usr/bin/env python3

import os
import sys
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_block_height, wait_for_confirmation
from utils.config import AccountManager, Miner
from utils.miners import MinerManager
from utils.logger import Colors
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.stacks_core_api import StacksCoreAPI

def main():
    """Execute STX token transfer test"""
    print(f"{Colors.format_dim('=' * 60)}")
    print(f"{Colors.format_header('STX TOKEN TRANSFER TEST')}")
    print(f"{Colors.format_dim('=' * 60)}")
    
    # Raw minimal setup
    # FIXME: (LATER): Potrei creare un type "Setup" che ha cli, api, minermanager, ...
    miners = MinerManager()
    sender_account = AccountManager.get(Miner.MINER1)
    recipient_account = AccountManager.get(Miner.MINER2)
    api = StacksCoreAPI(base_url=sender_account.api_url)
    cli = BlockstackCLIWrapper()
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not miners.snapshot_restore_auto():
            raise RuntimeError("Failed to start miners")
        
        # Step 1: Check initial balances
        print(f"\n{Colors.format_header('Step 1: Check initial balances')}")
        # FIXME: Deve diventare una cosa tipo: logger.header('Step 1: Check initial balances')
        # FIXME: Poi separo logger.info, logger.error, logger.success, logger.warn, logger.dim, logger.subheader, logger.stacks da quello logger.custom (come cose piu "print" style)
        sender_account_info = api.get_account_info(sender_account.address)
        sender_initial_balance = sender_account_info.balance
        recipient_account_info = api.get_account_info(recipient_account.address)
        recipient_initial_balance = recipient_account_info.balance

        # FIXME: In generale il dev non deve occuparsi dei colori, deve essere tipo logger.formar_response ecc ecc ecc...
        print(f"{Colors.format_info('Sender address')}: {Colors.format_dim(sender_account.address)}")
        print(f"{Colors.format_info('Sender initial balance')}: {Colors.format_dim(f'{sender_initial_balance:,} µSTX')}")
        print(f"{Colors.format_info('Recipient address')}: {Colors.format_dim(recipient_account.address)}")
        print(f"{Colors.format_info('Recipient initial balance')}: {Colors.format_dim(f'{recipient_initial_balance:,} µSTX')}")
        
        # Step 2: Prepare transfer
        print(f"\n{Colors.format_header('Step 2: Prepare transfer')}")
        transfer_amount = 50000  # 50,000 µSTX
        transfer_memo = "Test transfer from example"
        fee = 180  # Transaction fee in µSTX
        
        sender_account_info = api.get_account_info(sender_account.address)
        initial_nonce = sender_account_info.nonce
        initial_height = get_block_height(api)
        
        print(f"{Colors.format_info('Transfer amount')}: {Colors.format_dim(f'{transfer_amount:,} µSTX')}")
        print(f"{Colors.format_info('Transfer memo')}: {Colors.format_dim(transfer_memo)}")
        print(f"{Colors.format_info('Transaction fee')}: {Colors.format_dim(f'{fee} µSTX')}")
        print(f"{Colors.format_info('Sender nonce')}: {Colors.format_dim(str(initial_nonce))}")
        
        # Step 3: Execute transfer
        print(f"\n{Colors.format_header('Step 3: Execute transfer')}")
        tx_hex = cli.token_transfer(
            sender_account.private_key,  # Private key for signing
            fee,                        # Transaction fee
            initial_nonce,              # Transaction nonce
            recipient_account.address,  # Recipient address
            transfer_amount,            # Amount to transfer
            transfer_memo               # Transfer memo
        )
        
        transfer_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        print(f"{Colors.format_success('Transfer submitted')}: {Colors.format_info(transfer_txid)}")
        
        # Step 4: Wait for confirmation
        print(f"\n{Colors.format_header('Step 4: Wait for confirmation')}")
        if not wait_for_confirmation(api, sender_account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Transfer confirmation timeout")
        print(f"{Colors.format_success('Transfer confirmed!')}")
        
        # Step 5: Verify final balances
        print(f"\n{Colors.format_header('Step 5: Verify final balances')}")
        sender_account_info = api.get_account_info(sender_account.address)
        sender_final_balance = sender_account_info.balance
        recipient_account_info = api.get_account_info(recipient_account.address)
        recipient_final_balance = recipient_account_info.balance
        
        sender_change = sender_final_balance - sender_initial_balance
        recipient_change = recipient_final_balance - recipient_initial_balance
        expected_sender_change = -(transfer_amount + fee)
        
        print(f"{Colors.format_info('Sender final balance')}: {Colors.format_dim(f'{sender_final_balance:,} µSTX')}")
        print(f"{Colors.format_info('Sender balance change')}: {Colors.format_dim(f'{sender_change:,} µSTX')}")
        print(f"{Colors.format_info('Recipient final balance')}: {Colors.format_dim(f'{recipient_final_balance:,} µSTX')}")
        print(f"{Colors.format_info('Recipient balance change')}: {Colors.format_dim(f'{recipient_change:,} µSTX')}")
        
        # Step 6: Validate transfer amounts
        print(f"\n{Colors.format_header('Step 6: Validate transfer amounts')}")
        
        # Sender should have lost: transfer_amount + fee
        if sender_change == expected_sender_change:
            print(f"{Colors.format_success('Sender balance change correct')}: {Colors.format_dim(f'{expected_sender_change:,} µSTX')}")
        else:
            print(f"{Colors.format_error('Sender balance change incorrect')}")
            print(f"  Expected: {expected_sender_change:,} µSTX")
            print(f"  Actual: {sender_change:,} µSTX")
        
        # Recipient should have gained: transfer_amount
        if recipient_change == transfer_amount:
            print(f"{Colors.format_success('Recipient balance change correct')}: {Colors.format_dim(f'+{transfer_amount:,} µSTX')}")
        else:
            print(f"{Colors.format_error('Recipient balance change incorrect')}")
            print(f"  Expected: +{transfer_amount:,} µSTX")
            print(f"  Actual: +{recipient_change:,} µSTX")
        
        # Step 7: Test multiple small transfers
        print(f"\n{Colors.format_header('Step 7: Test multiple small transfers')}")
        
        for i in range(3):
            small_amount = 1000 * (i + 1)  # 1000, 2000, 3000 µSTX
            small_memo = f"Small transfer #{i+1}"
            
            sender_account_info = api.get_account_info(sender_account.address)
            current_nonce = sender_account_info.nonce
            current_height = get_block_height(api)
            
            tx_hex = cli.token_transfer(
                sender_account.private_key,
                fee,
                current_nonce,
                recipient_account.address,
                small_amount,
                small_memo
            )
            
            small_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
            print(f"{Colors.format_success(f'Transfer #{i+1} submitted')}: {Colors.format_info(small_txid)} - {Colors.format_dim(f'{small_amount:,} µSTX')}")
            
            if not wait_for_confirmation(api, sender_account.address, current_nonce, current_height, timeout=120):
                print(f"{Colors.format_error(f'Transfer #{i+1} confirmation timeout')}")
            else:
                print(f"{Colors.format_success(f'Transfer #{i+1} confirmed')}")
        
        # Final summary
        print(f"\n{Colors.format_dim('=' * 60)}")
        print(f"{Colors.format_header('FINAL RESULT')}")
        print(f"{Colors.format_dim('=' * 60)}")
        
        sender_account_info = api.get_account_info(sender_account.address)
        final_sender_balance = sender_account_info.balance
        recipient_account_info = api.get_account_info(recipient_account.address)
        final_recipient_balance = recipient_account_info.balance
        total_sender_change = final_sender_balance - sender_initial_balance
        total_recipient_change = final_recipient_balance - recipient_initial_balance
        
        print(f"{Colors.format_info('Main transfer TXID')}: {Colors.format_dim(transfer_txid)}")
        print(f"{Colors.format_info('Total amount transferred')}: {Colors.format_dim(f'{transfer_amount + 6000:,} µSTX')}")  # Main + 3 small transfers
        print(f"{Colors.format_info('Total sender change')}: {Colors.format_dim(f'{total_sender_change:,} µSTX')}")
        print(f"{Colors.format_info('Total recipient gain')}: {Colors.format_dim(f'{total_recipient_change:,} µSTX')}")
        
        return True
        
    # FIXME: Tenere try catch finale ma gli faccio risalire le eccezioni dai livelli piu bassi, eccetto eccezioni come socket IO per esempio, che "blocco" in componenti piu bassi (in /utils)
    except Exception as e:
        print(f"\n{Colors.format_error('TEST FAILED')}: {Colors.format_error(str(e))}")
        return False
        
    finally:
        # Cleanup
        print(f"\n{Colors.format_header('Cleaning up...')}")
        miners.stop()
        miners.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)