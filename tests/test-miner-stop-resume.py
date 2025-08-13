#!/usr/bin/env python3

import os
import sys
import time
import subprocess
from typing import Dict, Any, Optional, List

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config import ACCOUNTS, Account, MinerName, AccountManager
from utils.stacks_core_api import StacksCoreAPIWrapper
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.node_manager import NodeManager
from utils.colors import Colors, logger

class MinerStopResumeTester:
    """Direct miner stop/resume testing without recipes framework"""
    
    def __init__(self):
        self.node_manager = NodeManager()
        self.cli = BlockstackCLIWrapper()
        self.submitted_transactions = []  # Store submitted transaction IDs for later verification
        
    def get_account_info(self, miner: str) -> Optional[Dict[str, Any]]:
        """Get account info (balance, nonce) with connection error handling"""
        try:
            account = AccountManager.get_by_name(miner)
            api = StacksCoreAPIWrapper(base_url=account.api_url)
            return api.get_account_info(account.address)
        except Exception as e:
            logger.error(f"Failed to get account info for {miner}: {e}")
            return None
    
    def get_nonce(self, miner: str) -> Optional[int]:
        """Get current nonce for account"""
        account_info = self.get_account_info(miner)
        return account_info["nonce"] if account_info else None
    
    def get_balance(self, miner: str) -> Optional[int]:
        """Get STX balance for account"""
        account_info = self.get_account_info(miner)
        if not account_info:
            return None
        balance_hex = account_info.get('balance', '0x0')
        return int(balance_hex, 16) if balance_hex.startswith('0x') else int(balance_hex)
    
    def get_block_height(self, miner: str) -> Optional[int]:
        """Get current block height with connection error handling"""
        try:
            account = AccountManager.get_by_name(miner)
            api = StacksCoreAPIWrapper(base_url=account.api_url)
            info_data = api.get_info()
            return info_data["stacks_tip_height"]
        except Exception as e:
            logger.error(f"Failed to get block height for {miner}: {e}")
            return None
    
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
    
    def submit_no_wait(self, api_miner: str, from_miner: str, to_address: str, 
                          amount: int, memo: Optional[str] = None, nonce: Optional[int] = None) -> str:
        """Submit transaction via specific miner's API endpoint without waiting for confirmation"""
        from_account = AccountManager.get_by_name(from_miner)
        api_account = AccountManager.get_by_name(api_miner)
        api_wrapper = StacksCoreAPIWrapper(base_url=api_account.api_url)
        
        # Use provided nonce or get current nonce
        if nonce is not None:
            use_nonce = nonce
        else:
            use_nonce = self.get_nonce(from_miner)
            
        print(f"\n{Colors.format_header('=== SUBMITTING UNPROCESSED TX ===')}")
        print(f"{Colors.format_info('API Miner')}: {Colors.format_dim(api_miner)} (endpoint: {api_account.api_url})")
        print(f"{Colors.format_info('From Account')}: {Colors.format_dim(from_account.address)}")
        print(f"{Colors.format_info('To Address')}: {Colors.format_dim(to_address)}")
        print(f"{Colors.format_info('Amount')}: {Colors.format_dim(f'{amount} µSTX')}")
        print(f"{Colors.format_info('Using nonce')}: {Colors.format_dim(str(use_nonce))}")
        
        # Capture initial state before submitting transaction
        initial_nonce = self.get_nonce(from_miner)
        initial_balance = self.get_balance(from_miner)
        initial_height = self.get_block_height(api_miner)
        
        print(f"{Colors.format_info('Current Block Height')}: {Colors.format_dim(str(initial_height))}")
        
        # Create transaction
        cmd = self.cli.token_transfer(from_account.private_key, 180, use_nonce, to_address, amount, memo)
        
        print(f"{Colors.format_info('Creating transaction binary...')}")
        tx_binary = self.run_cli_command(cmd, binary_output=True)
        
        # Submit via specific miner's API endpoint
        print(f"{Colors.format_info(f'Submitting via {api_miner} API...')}")
        txid = api_wrapper.post_raw_transaction(tx_binary)
        
        print(f"{Colors.format_success(f'Transaction submitted via {api_miner} API')}: {Colors.format_info(txid)}")
        print(f"{Colors.format_warn('NOT waiting for confirmation - keeping in mempool')}")
        
        # Store transaction info for later verification
        self.submitted_transactions.append({
            'txid': txid,
            'from_miner': from_miner,
            'api_miner': api_miner,
            'to_address': to_address,
            'amount': amount,
            'nonce': use_nonce,
            'memo': memo,
            'initial_nonce': initial_nonce,
            'initial_balance': initial_balance,
            'initial_height': initial_height
        })
        
        return txid

    def is_miner_available(self, miner: str) -> bool:
        """Check if miner is available for API calls"""
        try:
            account = AccountManager.get_by_name(miner)
            api = StacksCoreAPIWrapper(base_url=account.api_url)
            api.get_info()
            return True
        except Exception:
            return False
    
    def verify_transaction(self, miner: str, txid: str) -> bool:
        """Simple transaction verification - returns True if transaction is found"""
        if not self.is_miner_available(miner):
            print(f"{Colors.format_warn('Miner unavailable, skipping verification')}: {Colors.format_dim(miner)}")
            return False
            
        try:
            account = AccountManager.get_by_name(miner)
            api = StacksCoreAPIWrapper(base_url=account.api_url)
            tx_data = api.get_transaction_by_id(txid)
            print(f"{Colors.format_success('Transaction found')}: {Colors.format_dim(txid)}")
            return True
        except Exception as e:
            print(f"{Colors.format_error('Transaction not found')}: {Colors.format_dim(txid)} - {Colors.format_dim(str(e))}")
            return False

def main():
    """Execute the miner mempool stop/resume test"""
    print(f"{Colors.format_dim('=' * 80)}")
    print(f"{Colors.format_header('MINER MEMPOOL BEHAVIOR ON STOP/RESUME TEST')}")
    print(f"{Colors.format_dim('=' * 80)}")
    
    tester = MinerStopResumeTester()
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not tester.node_manager.start_node():
            raise RuntimeError("Failed to start miners")
        
        # Step 1: Submit ALL valid transaction combinations (sender-receiver-api_host)
        print(f"\n{Colors.format_header('Step 1: Submit ALL valid transaction combinations (excluding self-transactions)')}")
        
        submitted_txs = []
        tx_counter = 1
        
        # Get all available miners dynamically from ACCOUNTS
        all_miners = list(ACCOUNTS.keys())
        print(f"{Colors.format_info('Configured miners')}: {Colors.format_dim(', '.join(all_miners))} ({len(all_miners)} total)")
        
        # Filter to only available miners
        miners = [miner for miner in all_miners if tester.is_miner_available(miner)]
        unavailable = [miner for miner in all_miners if not tester.is_miner_available(miner)]
        
        print(f"{Colors.format_info('Available miners')}: {Colors.format_dim(', '.join(miners))} ({len(miners)} total)")
        if unavailable:
            print(f"{Colors.format_warn('Unavailable miners')}: {Colors.format_dim(', '.join(unavailable))}")
        
        if len(miners) < 2:
            raise RuntimeError(f"Need at least 2 available miners, got {len(miners)}")
        
        # Get initial nonces from API for each available sender
        print(f"\n{Colors.format_info('Getting initial nonces from blockchain...')}")
        nonces = {}
        for miner in miners:
            initial_nonce = tester.get_nonce(miner)
            if initial_nonce is not None:
                nonces[miner] = initial_nonce
                print(f"{Colors.format_dim(f'  {miner}: starting nonce {initial_nonce}')}")
            else:
                print(f"{Colors.format_error(f'  {miner}: failed to get nonce - skipping')}")
        
        # Only use miners that we could get nonces for
        miners = list(nonces.keys())
        
        for sender in miners:
            for receiver in miners:
                for api_host in miners:
                    # Skip self-transactions (Stacks doesn't allow sender = recipient)
                    if sender == receiver:
                        continue
                    
                    # Create readable combo code (sender-receiver-api indices)
                    combo_code = f"{miners.index(sender) + 1}-{miners.index(receiver) + 1}-{miners.index(api_host) + 1}"
                    description = f"{sender}→{receiver} via {api_host} API"
                    
                    print(f"\n{Colors.format_subheader(f'TX{tx_counter} ({combo_code}): {description}')}")
                    
                    txid = tester.submit_no_wait(
                        api_miner=api_host,
                        from_miner=sender,
                        to_address=AccountManager.get_by_name(receiver).address,
                        amount=100000 + (tx_counter * 10000),  # Unique amounts
                        memo=f"{combo_code}: {description}",
                        nonce=nonces[sender]  # Use global nonce for this sender
                    )
                    
                    submitted_txs.append((f"tx{tx_counter}", txid, sender, receiver, api_host, combo_code))
                    nonces[sender] += 1  # Increment global nonce for this sender
                    tx_counter += 1
        
        print(f"\n{Colors.format_success('All valid transaction combinations submitted!')}")
        expected_combinations = len(miners) * (len(miners) - 1) * len(miners)  # N × (N-1) × N
        print(f"{Colors.format_info('Total transactions')}: {Colors.format_dim(str(len(submitted_txs)))} ({expected_combinations} combinations: {len(miners)} senders × {len(miners)-1} valid receivers × {len(miners)} API hosts)")
        
        # Step 3: Stop first miner while transactions are in mempool
        # (This check is redundant since we already verified above)
        
        # Stop first miner (affects transactions submitted via this miner's API)
        target_miner_name = miners[0]
        target_miner_num = miners.index(target_miner_name) + 1
        
        affected_txs = [tx for tx in submitted_txs if tx[4] == target_miner_name]  # tx[4] is api_host
        unaffected_txs = [tx for tx in submitted_txs if tx[4] != target_miner_name]  # Should still work
        
        print(f"\n{Colors.format_header(f'Step 3: Stop {target_miner_name} (affects {len(affected_txs)} transactions, {len(unaffected_txs)} should survive)')}")
        print(f"{Colors.format_info(f'Affected (via {target_miner_name} API)')}: {Colors.format_dim(f'{len(affected_txs)} transactions')}")
        print(f"{Colors.format_info('Unaffected (via other APIs)')}: {Colors.format_dim(f'{len(unaffected_txs)} transactions')}")
        tester.node_manager.stop_miner(target_miner_num)
        
        # Step 4: Try to verify transactions while miner1 is stopped
        # Use an active miner (not miner1) for verification
        active_miners = [m for m in miners if m != target_miner_name]
        active_miner_name = active_miners[0] if active_miners else None
        
        if not active_miner_name:
            raise RuntimeError("No active miners available for verification")
        
        print(f"\n{Colors.format_header(f'Step 4: Verify all {len(submitted_txs)} transactions while {target_miner_name} is stopped')}")
        print(f"{Colors.format_info(f'Checking transaction visibility from {active_miner_name} (active miner)...')}")
        
        found_while_stopped = []
        for tx_name, txid, sender, receiver, api_host, combo_code in submitted_txs:
            print(f"\n{Colors.format_info(f'Checking {tx_name} ({combo_code})')}: {Colors.format_dim(f'{sender} → {receiver} via {api_host}')}")
            found = tester.verify_transaction(active_miner_name, txid)
            if found:
                found_while_stopped.append((tx_name, txid, sender, receiver, api_host, combo_code))
            time.sleep(0.5)  # Small delay between API calls
        
        if not found_while_stopped:
            print(f"\n{Colors.format_success(f'Expected: No transactions found while {target_miner_name} stopped')}")
            print(f"{Colors.format_dim(f'  This means all transactions were lost when {target_miner_name} stopped')}")
        else:
            print(f"\n{Colors.format_warn(f'Unexpected: {len(found_while_stopped)} transactions found from other miners')}")
            print(f"{Colors.format_dim('  This means some transactions propagated to other miners')}")
            for tx_name, txid, sender, receiver, api_host, combo_code in found_while_stopped:
                print(f"{Colors.format_dim(f'  - {tx_name} ({combo_code}): {sender} → {receiver} via {api_host}')}")
        
        # Step 5: Resume target miner (same one we stopped)
        print(f"\n{Colors.format_header(f'Step 5: Resume {target_miner_name}')}")
        tester.node_manager.resume_miner(target_miner_num)
        
        # Step 6: Wait for confirmation after target miner is resumed
        print(f"\n{Colors.format_header(f'Step 6: Wait for confirmation after {target_miner_name} resumed')}")
        print(f"{Colors.format_info('Waiting for transactions to be processed...')}")
        
        # Check available miners for nonce increases
        available_miners_for_check = [m for m in miners if tester.is_miner_available(m)]
        if not available_miners_for_check:
            print(f"{Colors.format_warn('No miners available for confirmation check')}")
            confirmation_result = False
        else:
            initial_nonces = {}
            for miner in available_miners_for_check[:2]:  # Check up to 2 miners
                nonce = tester.get_nonce(miner)
                if nonce is not None:
                    initial_nonces[miner] = nonce
            
            current_height = None
            for miner in available_miners_for_check:
                height = tester.get_block_height(miner)
                if height is not None:
                    current_height = height
                    break
            
            if not initial_nonces or current_height is None:
                print(f"{Colors.format_warn('Could not get initial state for confirmation check')}")
                confirmation_result = False
            else:
                for miner, nonce in initial_nonces.items():
                    print(f"{Colors.format_info(f'{miner.capitalize()} initial nonce')}: {Colors.format_dim(str(nonce))}")
                print(f"{Colors.format_info('Current height')}: {Colors.format_dim(str(current_height))}")
        
                # Wait to see if transactions get confirmed now that target miner is back
                confirmation_results = {}
                for miner, initial_nonce in initial_nonces.items():
                    print(f"{Colors.format_info(f'Checking {miner} for confirmation...')}")
                    confirmation_results[miner] = tester.wait_for_confirmation(miner, initial_nonce, current_height, timeout=15)
                
                confirmation_result = any(confirmation_results.values())
        
        if confirmation_result and 'initial_nonces' in locals() and 'current_height' in locals():
            final_nonces = {}
            for miner in initial_nonces.keys():
                nonce = tester.get_nonce(miner)
                if nonce is not None:
                    final_nonces[miner] = nonce
            
            final_height = None
            for miner in available_miners_for_check:
                height = tester.get_block_height(miner)
                if height is not None:
                    final_height = height
                    break
            
            if final_nonces and final_height is not None:
                print(f"{Colors.format_success(f'Transactions confirmed after {target_miner_name} resumed!')}")
                
                for miner in initial_nonces.keys():
                    if miner in final_nonces:
                        initial_nonce = initial_nonces[miner]
                        final_nonce = final_nonces[miner]
                        print(f"{Colors.format_info(f'{miner.capitalize()} nonce')}: {Colors.format_dim(str(initial_nonce))} → {Colors.format_dim(str(final_nonce))} (+{final_nonce - initial_nonce})")
                
                print(f"{Colors.format_info('Block height')}: {Colors.format_dim(str(current_height))} → {Colors.format_dim(str(final_height))} (+{final_height - current_height})")
            else:
                print(f"{Colors.format_warn('Could not get final state for confirmation summary')}")
        else:
            print(f"{Colors.format_warn('No confirmation detected within timeout period')}")
        
        # Step 7: Try to verify transactions after target miner resumed
        print(f"\n{Colors.format_header(f'Step 7: Verify transactions after {target_miner_name} resumed')}")
        print(f"{Colors.format_info(f'Checking if transactions are now visible from {target_miner_name}...')}")
        
        found_after_resume = []
        for tx_name, txid, sender, receiver, api_host, combo_code in submitted_txs:
            print(f"\n{Colors.format_info(f'Checking {tx_name} ({combo_code})')}: {Colors.format_dim(f'{sender} → {receiver} via {api_host}')}")
            # Check from the original API host that submitted the transaction
            found = tester.verify_transaction(api_host, txid)
            if found:
                found_after_resume.append((tx_name, txid, sender, receiver, api_host, combo_code))
            time.sleep(0.5)  # Small delay between API calls
        
        transactions_found_after_resume = len(found_after_resume) > 0
        
        # Final summary
        print(f"\n{Colors.format_dim('=' * 80)}")
        print(f"{Colors.format_header('FINAL RESULT')}")
        print(f"{Colors.format_dim('=' * 80)}")
        
        print(f"\n{Colors.format_info('Transaction Details')}:")
        for tx_name, txid, sender, receiver, api_host, combo_code in submitted_txs:
            # Check if this transaction was found after resume
            is_verified = any(found_tx[1] == txid for found_tx in found_after_resume)
            status_icon = f"{Colors.GREEN}✓{Colors.RESET}" if is_verified else f"{Colors.RED}✗{Colors.RESET}"
            print(f"{status_icon} {Colors.format_info(f'{tx_name.upper()} ({combo_code})')}: {Colors.format_dim(txid)} - {Colors.format_dim(f'{sender} → {receiver} via {api_host} API')}")
        return True
        
    except Exception as e:
        print(f"\n{Colors.format_error('TEST FAILED')}: {Colors.format_error(str(e))}")
        return False
        
    finally:
        # Cleanup
        print(f"\n{Colors.format_stacks('Cleaning up...')}")
        tester.node_manager.stop_node()
        tester.node_manager.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)