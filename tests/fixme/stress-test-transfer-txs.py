#!/usr/bin/env python3

import os
import sys
import time

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_account_info_typed, get_block_height, wait_for_confirmation, get_tx_status_typed
from utils.config import AccountManager, Miner, TransferParams, TransferInfo, VerificationResults, TransactionStatus, TxStatus, VerificationSummary
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.stacks_core_api import StacksCoreAPIWrapper
from typing import List
from utils.miners import MinerManager
from utils.logger import Colors, logger

def generate_transfers(count: int, base_amount: int = 100) -> List[TransferParams]:
    """Generate list of transfer parameters"""
    # Use a fixed recipient address for simplicity
    recipient_address = "ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM"
    
    transfers = []
    for i in range(count):
        transfers.append(TransferParams(
            to=recipient_address,
            amount=base_amount + i,  # Unique amounts
            memo=f"StressTx{i+1:04d}"  # Zero-padded memo
        ))
    
    return transfers

def submit_transfer_batch(miner: Miner, transfers: list) -> list:
    """Submit batch of transfers using raw APIs + helpers"""
    account = AccountManager.get(miner)
    api = StacksCoreAPIWrapper(base_url=account.api_url)
    cli = BlockstackCLIWrapper()
    submitted_transfers = []
    
    # Get initial nonce and manage it manually for batch submission
    account_info = get_account_info_typed(api, account.address)
    current_nonce = account_info.nonce
    
    print(f"\n{Colors.format_info('Submitting batch of transfers...')}")
    print(f"{Colors.format_info('Starting nonce')}: {Colors.format_dim(str(current_nonce))}")
    
    for i, transfer in enumerate(transfers):
        try:
            # Use managed nonce for batch submission
            nonce = current_nonce + i
            
            transfer_info = TransferInfo(
                miner=miner,
                to_address=transfer.to,
                amount=transfer.amount,
                memo=transfer.memo,
                nonce=nonce
            )
            
            # Use raw CLI + API
            tx_hex = cli.token_transfer(account.private_key, 180, nonce, transfer.to, transfer.amount, transfer.memo)
            txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
            
            transfer_info.txid = txid
            transfer_info.status = TransactionStatus.SUBMITTED
            submitted_transfers.append(transfer_info)
            
            print(f"  {i+1:3d}/{len(transfers)} - TX: {txid[:8]}... - Amount: {transfer.amount} - Nonce: {nonce} - Memo: {transfer.memo}")
            
            # Small delay to avoid overwhelming the network
            time.sleep(0.1)
            
        except Exception as e:
            transfer_info.status = TransactionStatus.FAILED
            transfer_info.error = str(e)
            submitted_transfers.append(transfer_info)
            print(f"  {i+1:3d}/{len(transfers)} - FAILED: {str(e)}")
    
    return submitted_transfers

def wait_and_verify_transfers(submitted_transfers: list, timeout: int = 300) -> dict:
    """Wait for block confirmations and verify transfers as blocks are mined"""
    if not submitted_transfers:
        return {"total": 0, "confirmed": 0, "pending": 0, "failed": 0}
    
    # Get initial block height
    account = AccountManager.get(Miner.MINER1)
    api = StacksCoreAPIWrapper(base_url=account.api_url)
    initial_height = get_block_height(api)
    start_time = time.time()
    
    print(f"Initial block height: {initial_height}")
    print(f"Waiting for new blocks (timeout: {timeout}s)...")
    
    verified_count = 0
    last_verified_height = initial_height
    
    while time.time() - start_time < timeout:
        current_height = get_block_height(api)
        
        if current_height > last_verified_height:
            print(f"New block mined! Height: {current_height} (+{current_height - initial_height})")
            
            # Verify transactions in this new block
            verification_results = verify_transfers(submitted_transfers)
            new_verified = verification_results["confirmed"]
            
            if new_verified > verified_count:
                print(f"  Confirmed: {new_verified} (+{new_verified - verified_count})")
                verified_count = new_verified
            
            last_verified_height = current_height
            
            # If all transactions are confirmed or failed, stop waiting
            if verification_results["pending"] == 0:
                print("All transactions processed!")
                break
        
        time.sleep(2)  # Check every 2 seconds
    
    # Final verification
    final_results = verify_transfers(submitted_transfers)
    elapsed = time.time() - start_time
    print(f"Verification completed after {elapsed:.1f}s")
    return final_results

def verify_transfers(submitted_transfers: list) -> dict:
    """Verify all submitted transfers using raw APIs"""
    verification_results = VerificationResults()
    
    print(f"\n{Colors.format_info('Verifying transfers...')}")
    
    for transfer_info in submitted_transfers:
        if transfer_info.status != TransactionStatus.SUBMITTED:
            verification_results.failed.append(transfer_info)
            continue
        
        account = AccountManager.get(transfer_info.miner)
        api = StacksCoreAPIWrapper(base_url=account.api_url)
        
        try:
            # If we can get transaction details, it passed
            tx_details = api.get_transaction_by_id(transfer_info.txid)
            transfer_info.status = TransactionStatus.CONFIRMED
            verification_results.confirmed.append(transfer_info)
            
            print(f"  {Colors.format_success('✓')} Transfer {transfer_info.amount} µSTX - TXID: {transfer_info.txid}")
            print(f"    {Colors.format_dim('Transaction details (omitted for brevity)')}")
            
        except Exception as e:
            # If we can't get transaction details, it failed
            transfer_info.status = TransactionStatus.FAILED
            transfer_info.error = str(e)
            verification_results.failed.append(transfer_info)
            
            print(f"  {Colors.format_error('✗')} Transfer {transfer_info.amount} µSTX - TXID: {transfer_info.txid}")
            print(f"    {Colors.format_dim(f'Error: {str(e)}')}")
    
    return {
        'confirmed': len(verification_results.confirmed),
        'pending': len(verification_results.pending),
        'failed': len(verification_results.failed),
        'total': len(submitted_transfers),
        'details': verification_results
    }

def print_balance_summary(miners: list):
    """Print balance summary for all miners"""
    print(f"\n{Colors.format_header('Balance Summary')}")
    for miner in miners:
        try:
            account = AccountManager.get(miner)
            api = StacksCoreAPIWrapper(base_url=account.api_url)
            account_info = get_account_info_typed(api, account.address)
            balance = account_info.balance
            print(f"  {miner.value}: {balance:,} µSTX ({account.address})")
        except Exception as e:
            print(f"  {miner.value}: Error getting balance - {e}")

def main():
    """Execute the transfer stress test"""
    print(f"{Colors.format_dim('=' * 80)}")
    print(f"{Colors.format_header('STACKS TRANSFER STRESS TEST')}")
    print(f"{Colors.format_dim('=' * 80)}")
    
    # Configuration
    NUM_TRANSFERS = 30  # Test up to 30 transfers to properly stress test
    BASE_AMOUNT = 1000  # µSTX
    
    # Raw minimal setup
    miner_manager = MinerManager()
    miners = [Miner.MINER1, Miner.MINER2, Miner.MINER3]
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not miner_manager.snapshot_restore_auto():
            raise RuntimeError("Failed to start miners")
        
        # Show initial balances
        print_balance_summary(miners)
        
        # Generate transfers
        print(f"\n{Colors.format_header('Generating Transfer Transactions')}")
        print(f"{Colors.format_info('Number of transfers')}: {Colors.format_dim(str(NUM_TRANSFERS))}")
        print(f"{Colors.format_info('Base amount')}: {Colors.format_dim(f'{BASE_AMOUNT} µSTX')}")
        
        transfers = generate_transfers(NUM_TRANSFERS, BASE_AMOUNT)
        
        # Submit transfers from MINER1
        print(f"\n{Colors.format_header('Submitting Transfers')}")
        test_miner = Miner.MINER1
        submitted_transfers = submit_transfer_batch(test_miner, transfers)
        
        successful_submissions = [t for t in submitted_transfers if t.status == TransactionStatus.SUBMITTED]
        failed_submissions = [t for t in submitted_transfers if t.status == TransactionStatus.FAILED]
        
        print(f"\n{Colors.format_info('Submission Results')}:")
        print(f"  Successful: {Colors.format_success(str(len(successful_submissions)))}")
        print(f"  Failed: {Colors.format_error(str(len(failed_submissions)))}")
        
        if failed_submissions:
            print(f"\n{Colors.format_header('Failed Submissions')}:")
            for transfer in failed_submissions[:5]:  # Show first 5 failures
                print(f"  Amount: {transfer.amount}, Error: {transfer.error}")
        
        # Wait for some confirmations
        print(f"\n{Colors.format_header('Waiting for confirmations...')}")
        verification_results = wait_and_verify_transfers(submitted_transfers)
        
        # Show final balances
        print_balance_summary(miners)
        
        # Show some transaction details
        if verification_results['confirmed'] > 0:
            print(f"\n{Colors.format_header('Sample Confirmed Transactions')}")
            confirmed_transfers = verification_results['details'].confirmed[:3]  # Show first 3
            for transfer in confirmed_transfers:
                print(f"  TXID: {transfer.txid}")
                print(f"    Amount: {transfer.amount} µSTX, Memo: {transfer.memo}")
                print(f"    To: {transfer.to_address}")
        
        return verification_results['confirmed'] > 0
        
    except Exception as e:
        print(f"\n{Colors.format_error('TEST FAILED')}: {Colors.format_error(str(e))}")
        return False
        
    finally:
        # Cleanup
        print(f"\n{Colors.format_header('Cleaning up...')}")
        miner_manager.stop()
        miner_manager.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)