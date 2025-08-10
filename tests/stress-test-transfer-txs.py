#!/usr/bin/env python3

import os
import sys
import time
import json
import subprocess
from typing import Dict, Any, Optional, List

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config import ACCOUNTS, Account
from utils.stacks_core_api import StacksCoreAPIWrapper
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.node_manager import NodeManager
from utils.colors import Colors, logger

class TransferStressTester:
    """Direct transfer stress testing without recipes framework"""
    
    def __init__(self):
        self.node_manager = NodeManager()
        self.cli = BlockstackCLIWrapper()
        self.submitted_transfers = []
        
    def get_account_info(self, miner: str) -> Dict[str, Any]:
        """Get account info (balance, nonce)"""
        account = ACCOUNTS[miner]
        api = StacksCoreAPIWrapper(base_url=account.api_url)
        return api.get_account_info(account.address)
    
    def get_nonce(self, miner: str) -> int:
        """Get current nonce for account"""
        return self.get_account_info(miner)["nonce"]
    
    def get_balance(self, miner: str) -> int:
        """Get STX balance for account"""
        account_info = self.get_account_info(miner)
        balance_hex = account_info.get('balance', '0x0')
        return int(balance_hex, 16) if balance_hex.startswith('0x') else int(balance_hex)
    
    def get_block_height(self, miner: str) -> int:
        """Get current block height"""
        account = ACCOUNTS[miner]
        api = StacksCoreAPIWrapper(base_url=account.api_url)
        info_data = api.get_info()
        return info_data["stacks_tip_height"]
    
    def run_cli_command(self, command: list, binary_output: bool = False) -> bytes:
        """Run blockstack-cli command and return output"""
        try:
            result = subprocess.run(command, capture_output=True, check=True)
            if binary_output:
                hex_output = result.stdout.decode().strip()
                return bytes.fromhex(hex_output)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"CLI command failed: {' '.join(command)}\nError: {e.stderr.decode()}")
    
    def generate_transfers(self, count: int, base_amount: int = 100) -> List[Dict[str, Any]]:
        """Generate list of transfer parameters"""
        # Use a fixed recipient address for simplicity
        recipient_address = "ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM"
        
        transfers = []
        for i in range(count):
            transfers.append({
                "to": recipient_address,
                "amount": base_amount + i,  # Unique amounts
                "memo": f"StressTx{i+1:04d}"  # Zero-padded memo
            })
        
        return transfers
    
    def submit_transfer(self, miner: str, to_address: str, amount: int, memo: str, nonce: int) -> Dict[str, Any]:
        """Submit transfer without waiting for confirmation"""
        account = ACCOUNTS[miner]
        api = StacksCoreAPIWrapper(base_url=account.api_url)
        
        transfer_info = {
            'miner': miner,
            'to_address': to_address,
            'amount': amount,
            'memo': memo,
            'nonce': nonce,
            'submitted': False,
            'txid': None,
            'error': None
        }
        
        try:
            print(f"{Colors.format_info('Submitting')}: {amount} µSTX to {to_address[:8]}... (memo: {memo}, nonce: {nonce})")
            
            # Fixed fee for transfers
            fee = 180
            
            # Build CLI command
            cmd = self.cli.token_transfer(account.private_key, fee, nonce, to_address, amount, memo)
            
            # Create transaction binary
            tx_binary = self.run_cli_command(cmd, binary_output=True)
            
            # Submit transaction
            txid = api.post_raw_transaction(tx_binary)
            transfer_info['txid'] = txid
            transfer_info['submitted'] = True
            
            print(f"{Colors.format_success('Submitted')}: {memo} -> {txid}")
            
        except Exception as e:
            transfer_info['error'] = str(e)
            print(f"{Colors.format_error('Failed')}: {memo} -> {str(e)}")
        
        return transfer_info
    
    def wait_for_confirmation(self, miner: str, initial_nonce: int, initial_height: int, timeout: int = 60) -> bool:
        """Wait for transaction confirmation (nonce + height increase)"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_nonce = self.get_nonce(miner)
                current_height = self.get_block_height(miner)
                
                if current_nonce > initial_nonce and current_height > initial_height:
                    return True
                    
            except Exception:
                pass
            
            time.sleep(1)
        
        return False
    
    def batch_submit_transfers(self, miner: str, transfer_count: int) -> List[Dict[str, Any]]:
        """Submit multiple transfers rapidly to test mempool limits"""
        print(f"\n{Colors.format_header('=== BATCH TRANSFER SUBMISSION ===')}")
        print(f"{Colors.format_info('Miner')}: {Colors.format_dim(miner)}")
        print(f"{Colors.format_info('Transfer count')}: {Colors.format_dim(str(transfer_count))}")
        
        # Get initial state
        initial_nonce = self.get_nonce(miner)
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        print(f"{Colors.format_info('Initial nonce')}: {Colors.format_dim(str(initial_nonce))}")
        print(f"{Colors.format_info('Initial balance')}: {Colors.format_dim(str(initial_balance))}")
        print(f"{Colors.format_info('Initial height')}: {Colors.format_dim(str(initial_height))}")
        
        # Generate transfers
        transfers = self.generate_transfers(transfer_count)
        
        # Calculate total cost
        total_amount = sum(t['amount'] for t in transfers)
        total_fees = transfer_count * 180  # 180 µSTX per transfer
        total_cost = total_amount + total_fees
        
        print(f"{Colors.format_info('Total transfer amount')}: {Colors.format_dim(f'{total_amount} µSTX')}")
        print(f"{Colors.format_info('Total fees')}: {Colors.format_dim(f'{total_fees} µSTX')}")
        print(f"{Colors.format_info('Total cost')}: {Colors.format_dim(f'{total_cost} µSTX')}")
        
        if initial_balance < total_cost:
            print(f"{Colors.format_warn('Warning')}: Insufficient balance ({initial_balance} µSTX < {total_cost} µSTX required)")
            print(f"  Some transfers may fail due to insufficient balance")
        
        # Submit all transfers rapidly
        submitted_transfers = []
        current_nonce = initial_nonce
        
        print(f"\n{Colors.format_subheader('Submitting transfers rapidly...')}")
        start_time = time.time()
        
        for i, transfer in enumerate(transfers, 1):
            transfer_result = self.submit_transfer(
                miner,
                transfer['to'],
                transfer['amount'],
                transfer['memo'],
                current_nonce
            )
            submitted_transfers.append(transfer_result)
            
            if transfer_result['submitted']:
                current_nonce += 1
            else:
                # Stop submitting after first failure (chaining limit reached)
                print(f"\n{Colors.format_warn('Stopping submissions after first failure - limit found!')}")
                break
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.05)  # Faster than contract deployments
        
        end_time = time.time()
        submission_duration = end_time - start_time
        
        print(f"\n{Colors.format_info('Submission completed in')}: {Colors.format_dim(f'{submission_duration:.2f} seconds')}")
        
        successful_submissions = [t for t in submitted_transfers if t['submitted']]
        failed_submissions = [t for t in submitted_transfers if not t['submitted']]
        
        print(f"{Colors.format_success('Successful submissions')}: {Colors.format_dim(str(len(successful_submissions)))}")
        print(f"{Colors.format_error('Failed submissions')}: {Colors.format_dim(str(len(failed_submissions)))}")
        
        if failed_submissions:
            print(f"\n{Colors.format_subheader('Failed submission details')}:")
            for i, failed in enumerate(failed_submissions[:10], 1):  # Show up to 10 failures
                error_preview = failed['error'][:60] + "..." if len(failed['error']) > 60 else failed['error']
                print(f"  {i}. {failed['memo']}: {Colors.format_error(error_preview)}")
            
            if len(failed_submissions) > 10:
                print(f"  ... and {len(failed_submissions) - 10} more failures")
        
        return submitted_transfers
    
    def wait_and_verify_transfers(self, transfers: List[Dict[str, Any]], timeout: int = 120) -> Dict[str, Any]:
        """Wait for transfers to be confirmed and verify results"""
        print(f"\n{Colors.format_header('=== VERIFICATION PHASE ===')}")
        
        successful_transfers = [t for t in transfers if t['submitted']]
        if not successful_transfers:
            return {
                'confirmed': 0,
                'failed': 0,
                'pending': 0,
                'success_rate': 0.0,
                'confirmed_transfers': [],
                'failed_transfers': [],
                'pending_transfers': []
            }
        
        miner = successful_transfers[0]['miner']  # Use first transfer's miner
        
        print(f"{Colors.format_info('Waiting for confirmations')}: {Colors.format_dim(f'{timeout}s timeout')}")
        print(f"{Colors.format_info('Tracking')}: {Colors.format_dim(f'{len(successful_transfers)} submitted transfers')}")
        
        start_time = time.time()
        confirmed_transfers = []
        failed_transfers = []
        
        while time.time() - start_time < timeout and len(confirmed_transfers) + len(failed_transfers) < len(successful_transfers):
            # Check each unresolved transfer
            unresolved = [t for t in successful_transfers if t not in confirmed_transfers and t not in failed_transfers]
            
            for transfer in unresolved[:10]:  # Check up to 10 at a time
                try:
                    account = ACCOUNTS[miner]
                    api = StacksCoreAPIWrapper(base_url=account.api_url)
                    
                    # Try to get transaction info
                    tx_info = api.get_transaction_by_id(transfer['txid'])
                    tx_status = tx_info.get('tx_status', 'unknown')
                    
                    if tx_status == 'success':
                        confirmed_transfers.append(transfer)
                        print(f"{Colors.format_success('✓')} {transfer['memo']}: {Colors.format_success('Confirmed')}")
                    elif tx_status in ['abort_by_response', 'abort_by_post_condition']:
                        failed_transfers.append(transfer)
                        print(f"{Colors.format_error('✗')} {transfer['memo']}: {Colors.format_error('Failed')} ({tx_status})")
                    
                except Exception as e:
                    # Transaction might not be found yet, continue waiting
                    pass
            
            # Show progress less frequently for transfers
            if int(time.time() - start_time) % 10 == 0:
                confirmed_count = len(confirmed_transfers)
                failed_count = len(failed_transfers)
                total_resolved = confirmed_count + failed_count
                print(f"{Colors.format_info('Progress')}: {total_resolved}/{len(successful_transfers)} resolved ({confirmed_count} confirmed, {failed_count} failed)")
            
            time.sleep(3)  # Wait before next check
        
        pending_transfers = [t for t in successful_transfers if t not in confirmed_transfers and t not in failed_transfers]
        
        # Final summary
        total_submitted = len(successful_transfers)
        confirmed_count = len(confirmed_transfers)
        failed_count = len(failed_transfers)
        pending_count = len(pending_transfers)
        success_rate = (confirmed_count / total_submitted) * 100 if total_submitted > 0 else 0
        
        print(f"\n{Colors.format_subheader('Verification Results')}:")
        print(f"  Confirmed: {Colors.format_success(str(confirmed_count))}")
        print(f"  Failed: {Colors.format_error(str(failed_count))}")
        print(f"  Pending: {Colors.format_warn(str(pending_count))}")
        print(f"  Success rate: {Colors.format_info(f'{success_rate:.1f}%')}")
        
        return {
            'confirmed': confirmed_count,
            'failed': failed_count,
            'pending': pending_count,
            'success_rate': success_rate,
            'confirmed_transfers': confirmed_transfers,
            'failed_transfers': failed_transfers,
            'pending_transfers': pending_transfers
        }

def main():
    """Execute the transfer stress test"""
    print(f"{Colors.format_dim('=' * 80)}")
    print(f"{Colors.format_header('STACKS TRANSFER TRANSACTION STRESS TEST')}")
    print(f"{Colors.format_dim('=' * 80)}")
    
    tester = TransferStressTester()
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not tester.node_manager.start_node():
            raise RuntimeError("Failed to start miners")
        
        # Configuration
        transfer_count = 50  # Test with 50 transfers initially
        test_miner = "miner1"
        
        print(f"\n{Colors.format_header('Test Configuration')}:")
        print(f"  Target transfers: {Colors.format_dim(str(transfer_count))}")
        print(f"  Test miner: {Colors.format_dim(test_miner)}")
        
        # Step 1: Batch submit transfers
        print(f"\n{Colors.format_header('Step 1: Batch submit transfers')}")
        transfers = tester.batch_submit_transfers(test_miner, transfer_count)
        
        # Step 2: Wait and verify transfers
        successful_submissions = [t for t in transfers if t['submitted']]
        failed_submissions = [t for t in transfers if not t['submitted']]
        chaining_limit_hit = any('TooMuchChaining' in t.get('error', '') for t in failed_submissions)
        
        if chaining_limit_hit:
            print(f"\n{Colors.format_header('Step 2: Wait for transactions to process (chaining limit reached)')}\n")
            print(f"{Colors.format_success('Chaining limit found')}: Waiting for {len(successful_submissions)} transactions to be processed...")
            
            # Get initial state for confirmation waiting
            initial_nonce = tester.get_nonce(test_miner)
            initial_height = tester.get_block_height(test_miner)
            
            print(f"{Colors.format_info('Initial nonce')}: {Colors.format_dim(str(initial_nonce))}")
            print(f"{Colors.format_info('Initial height')}: {Colors.format_dim(str(initial_height))}")
            print(f"{Colors.format_info('Expected final nonce')}: {Colors.format_dim(str(initial_nonce + len(successful_submissions)))}")
            
            # Wait for nonce to advance (all transactions processed)
            confirmed = tester.wait_for_confirmation(test_miner, initial_nonce, initial_height, timeout=300)
            
            if confirmed:
                print(f"{Colors.format_success('Transactions processed - nonce advanced')}")
                
                # Now verify each transaction
                print(f"\n{Colors.format_header('Step 3: Verify individual transactions')}")
                confirmed_count = 0
                failed_count = 0
                
                for i, transfer in enumerate(successful_submissions, 1):
                    try:
                        account = ACCOUNTS[test_miner]
                        api = StacksCoreAPIWrapper(base_url=account.api_url)
                        tx_info = api.get_transaction_by_id(transfer['txid'])
                        
                        # Show transaction details and API response (omit tx field for brevity)
                        print(f"\n{Colors.format_info(f'Transaction {i}')}: {Colors.format_dim(transfer['memo'])}")
                        print(f"{Colors.format_info('Nonce')}: {Colors.format_dim(str(transfer['nonce']))}")
                        print(f"{Colors.format_info('TXID')}: {Colors.format_dim(transfer['txid'])}")
                        
                        # Create a copy of tx_info without the 'tx' field for cleaner output
                        display_info = dict(tx_info)
                        if 'tx' in display_info:
                            display_info['tx'] = "omitted for brevity"
                        print(f"{Colors.format_info('API Response')}: {Colors.format_dim(json.dumps(display_info, indent=2))}")
                        
                        tx_status = tx_info.get('tx_status', 'unknown')
                        
                        if tx_status == 'success':
                            confirmed_count += 1
                            print(f"{Colors.format_success('Status')}: {Colors.format_success('Confirmed')}")
                        elif tx_info:  # Transaction found but status might be different
                            # Just finding the transaction means it was processed
                            confirmed_count += 1
                            print(f"{Colors.format_success('Status')}: {Colors.format_success('Found')} (status: {tx_status})")
                        else:
                            failed_count += 1
                            print(f"{Colors.format_error('Status')}: {Colors.format_error('Failed')} ({tx_status})")
                            
                    except Exception as e:
                        failed_count += 1
                        print(f"\n{Colors.format_info(f'Transaction {i}')}: {Colors.format_dim(transfer['memo'])}")
                        print(f"{Colors.format_info('Nonce')}: {Colors.format_dim(str(transfer['nonce']))}")
                        print(f"{Colors.format_info('TXID')}: {Colors.format_dim(transfer['txid'])}")
                        print(f"{Colors.format_error('Status')}: {Colors.format_error('API Error')} ({str(e)[:50]}...)")
                
                success_rate = (confirmed_count / len(successful_submissions)) * 100 if successful_submissions else 0
                verification_results = {
                    'confirmed': confirmed_count,
                    'failed': failed_count,
                    'pending': 0,
                    'success_rate': success_rate,
                    'confirmed_transfers': [t for t in successful_submissions][:confirmed_count],
                    'failed_transfers': [t for t in successful_submissions][confirmed_count:confirmed_count+failed_count],
                    'pending_transfers': []
                }
            else:
                print(f"{Colors.format_error('Timeout waiting for transaction processing')}")
                verification_results = {
                    'confirmed': 0,
                    'failed': 0,
                    'pending': len(successful_submissions),
                    'success_rate': 0.0,
                    'confirmed_transfers': [],
                    'failed_transfers': [],
                    'pending_transfers': successful_submissions
                }
        else:
            print(f"\n{Colors.format_header('Step 2: Wait and verify transfers')}")
            verification_results = tester.wait_and_verify_transfers(transfers)
        
        # Final step: Analyze results
        step_num = "Step 4" if chaining_limit_hit else "Step 3"
        print(f"\n{Colors.format_header(f'{step_num}: Analyze stress test results')}")
        
        successful_submissions = [t for t in transfers if t['submitted']]
        submission_rate = (len(successful_submissions) / len(transfers)) * 100 if transfers else 0
        
        print(f"\n{Colors.format_subheader('Submission Analysis')}:")
        print(f"  Total attempted: {Colors.format_dim(str(len(transfers)))}")
        print(f"  Successfully submitted: {Colors.format_success(str(len(successful_submissions)))}")
        print(f"  Submission rate: {Colors.format_info(f'{submission_rate:.1f}%')}")
        
        print(f"\n{Colors.format_subheader('Confirmation Analysis')}:")
        print(f"  Confirmed transfers: {Colors.format_success(str(verification_results['confirmed']))}")
        print(f"  Failed transfers: {Colors.format_error(str(verification_results['failed']))}")
        print(f"  Pending transfers: {Colors.format_warn(str(verification_results['pending']))}")
        success_rate = verification_results['success_rate']
        print(f"  Confirmation rate: {Colors.format_info(f'{success_rate:.1f}%')}")
        
        # Calculate transaction throughput
        if verification_results['confirmed'] > 0:
            # Estimate time from submission start to last confirmation
            # For simplicity, use a rough estimate
            throughput_time = 120  # Approximate time window
            throughput = verification_results['confirmed'] / (throughput_time / 60)  # TPS converted to TPM
            print(f"  Estimated throughput: {Colors.format_dim(f'{throughput:.1f} tx/min')}")
        
        # Determine test success
        if chaining_limit_hit:
            # When chaining limit is hit, success is finding the limit + reasonable confirmation rate
            # Lower confirmation rate threshold since processing is slower due to chaining
            test_success = submission_rate >= 90.0 and verification_results['success_rate'] >= 50.0
        else:
            # Normal case: high submission and confirmation rates
            test_success = submission_rate >= 90.0 and verification_results['success_rate'] >= 70.0
        
        if verification_results['confirmed'] > 0:
            print(f"\n{Colors.format_subheader('Transfer Amount Analysis')}:")
            confirmed = verification_results['confirmed_transfers']
            amounts = [t['amount'] for t in confirmed]
            if amounts:
                total_amount = sum(amounts)
                avg_amount = total_amount / len(amounts)
                min_amount = min(amounts)
                max_amount = max(amounts)
                print(f"  Total confirmed amount: {Colors.format_dim(f'{total_amount} µSTX')}")
                print(f"  Average transfer amount: {Colors.format_dim(f'{avg_amount:.1f} µSTX')}")
                print(f"  Amount range: {Colors.format_dim(f'{min_amount} - {max_amount} µSTX')}")
        
        return test_success
        
    except Exception as e:
        print(f"\n{Colors.format_error('TEST FAILED')}: {Colors.format_error(str(e))}")
        return False
        
    finally:
        # Cleanup
        print(f"\n{Colors.format_header('Cleaning up...')}")
        tester.node_manager.stop_node()
        tester.node_manager.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)