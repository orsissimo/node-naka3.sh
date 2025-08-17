#!/usr/bin/env python3

import os
import sys
import time
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_api, get_cli, submit_tx, get_nonce, get_balance, submit_transfer, wait_for_confirmation, safe_api_call, get_tx_status_typed
from utils.config import AccountManager, MinerName, TransferParams, TransferInfo, VerificationResults, TransactionStatus, TxStatus, VerificationSummary
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

def submit_transfer_batch(miner: MinerName, transfers: list) -> list:
    """Submit batch of transfers using raw APIs + helpers"""
    api = get_api(miner)
    cli = get_cli()
    account = AccountManager.get(miner)
    submitted_transfers = []
    
    # Get initial nonce and manage it manually for batch submission
    current_nonce = get_nonce(api, account.address)
    
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
            cmd = cli.token_transfer(account.private_key, 180, nonce, transfer.to, transfer.amount, transfer.memo)
            txid = submit_tx(api, cmd)
            
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

def verify_transfers(submitted_transfers: list) -> dict:
    """Verify all submitted transfers using raw APIs"""
    verification_results = VerificationResults()
    
    print(f"\n{Colors.format_info('Verifying transfers...')}")
    
    for transfer_info in submitted_transfers:
        if transfer_info.status != TransactionStatus.SUBMITTED:
            verification_results.failed.append(transfer_info)
            continue
        
        api = get_api(transfer_info.miner)
        
        # Use typed API call with proper error handling
        tx_status = get_tx_status_typed(api, transfer_info.txid)
        
        if tx_status != TxStatus.UNKNOWN:
            if tx_status == TxStatus.SUCCESS:
                transfer_info.status = TransactionStatus.CONFIRMED
                verification_results.confirmed.append(transfer_info)
            elif tx_status in [TxStatus.ABORT_BY_RESPONSE, TxStatus.ABORT_BY_POST_CONDITION]:
                transfer_info.status = TransactionStatus.FAILED
                transfer_info.error = f"Transaction failed with status: {tx_status.value}"
                verification_results.failed.append(transfer_info)
            else:
                transfer_info.status = TransactionStatus.PENDING
                verification_results.pending.append(transfer_info)
        else:
            transfer_info.status = TransactionStatus.PENDING
            verification_results.pending.append(transfer_info)
    
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
            api = get_api(miner)
            account = AccountManager.get(miner)
            balance = get_balance(api, account.address)
            account = AccountManager.get(miner)
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
    miners = [MinerName.MINER1, MinerName.MINER2, MinerName.MINER3]
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not miner_manager.snapshot_restore("auto"):
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
        test_miner = MinerName.MINER1
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
        time.sleep(30)  # Give time for transactions to be processed
        
        # Verify transfers
        verification_results = verify_transfers(submitted_transfers)
        
        print(f"\n{Colors.format_header('Verification Results')}")
        print(f"  Total submitted: {Colors.format_dim(str(verification_results['total']))}")
        print(f"  Confirmed: {Colors.format_success(str(verification_results['confirmed']))}")
        print(f"  Pending: {Colors.format_warn(str(verification_results['pending']))}")
        print(f"  Failed: {Colors.format_error(str(verification_results['failed']))}")
        
        success_rate = (verification_results['confirmed'] / verification_results['total']) * 100 if verification_results['total'] > 0 else 0
        print(f"  Success rate: {Colors.format_info(f'{success_rate:.1f}%')}")
        
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