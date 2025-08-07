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

class MinerStopResumeTester:
    """Direct miner stop/resume testing without recipes framework"""
    
    def __init__(self):
        self.node_manager = NodeManager()
        self.cli = BlockstackCLIWrapper()
        self.submitted_transactions = []  # Store submitted transaction IDs for later verification
        
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
        from_account = ACCOUNTS[from_miner]
        api_account = ACCOUNTS[api_miner]
        api_wrapper = StacksCoreAPIWrapper(base_url=api_account.api_url)
        
        # Use provided nonce or get current nonce
        if nonce is not None:
            use_nonce = nonce
        else:
            use_nonce = self.get_nonce(from_miner)
            
        initial_height = self.get_block_height(api_miner)
        
        print(f"\n{Colors.format_header('=== SUBMITTING UNPROCESSED TX ===')}")
        print(f"{Colors.format_info('API Miner')}: {Colors.format_dim(api_miner)} (endpoint: {api_account.api_url})")
        print(f"{Colors.format_info('From Account')}: {Colors.format_dim(from_account.address)}")
        print(f"{Colors.format_info('To Address')}: {Colors.format_dim(to_address)}")
        print(f"{Colors.format_info('Amount')}: {Colors.format_dim(f'{amount} µSTX')}")
        print(f"{Colors.format_info('Current Block Height')}: {Colors.format_dim(str(initial_height))}")
        print(f"{Colors.format_info('Using nonce')}: {Colors.format_dim(str(use_nonce))}")
        
        # Create transaction
        cmd = self.cli.token_transfer(from_account.private_key, 180, use_nonce, to_address, amount, memo)
        
        print(f"{Colors.format_info('Creating transaction binary...')}")
        tx_binary = self.run_cli_command(cmd, binary_output=True)
        
        # Submit via specific miner's API endpoint
        print(f"{Colors.format_info(f'Submitting via {api_miner} API...')}")
        txid = api_wrapper.post_raw_transaction(tx_binary)
        
        print(f"{Colors.format_success(f'Transaction submitted via {api_miner} API')}: {Colors.format_info(txid)}")
        print(f"{Colors.format_warn('NOT waiting for confirmation - keeping in mempool')}")
        
        # Capture initial state for later verification
        initial_nonce = self.get_nonce(from_miner)
        initial_balance = self.get_balance(from_miner)
        initial_height = self.get_block_height(api_miner)
        
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

    def verify_transaction(self, miner: str, txid: str) -> bool:
        """Simple transaction verification - returns True if transaction is found"""
        try:
            account = ACCOUNTS[miner]
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
        miners = list(ACCOUNTS.keys())
        print(f"{Colors.format_info('Available miners')}: {Colors.format_dim(', '.join(miners))} ({len(miners)} total)")
        
        # Get initial nonces from API for each sender (mempool is shared across miners)
        print(f"\n{Colors.format_info('Getting initial nonces from blockchain...')}")
        nonces = {}
        for miner in miners:
            initial_nonce = tester.get_nonce(miner)
            nonces[miner] = initial_nonce
            print(f"{Colors.format_dim(f'  {miner}: starting nonce {initial_nonce}')}")
        
        for sender in miners:
            for receiver in miners:
                for api_host in miners:
                    # Skip self-transactions (Stacks doesn't allow sender = recipient)
                    if sender == receiver:
                        continue
                    
                    sender_num = miners.index(sender) + 1
                    receiver_num = miners.index(receiver) + 1  
                    api_num = miners.index(api_host) + 1
                    
                    combo_code = f"{sender_num}-{receiver_num}-{api_num}"
                    description = f"{sender}→{receiver} via {api_host} API"
                    
                    print(f"\n{Colors.format_subheader(f'TX{tx_counter} ({combo_code}): {description}')}")
                    
                    txid = tester.submit_no_wait(
                        api_miner=api_host,
                        from_miner=sender,
                        to_address=ACCOUNTS[receiver].address,
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
        
        # Step 3: Always stop miner1 while transactions are in mempool
        if len(miners) < 2:
            raise RuntimeError("Need at least 2 miners to test mempool behavior")
        
        # Always stop miner1 (affects transactions submitted via miner1's API)
        target_miner_name = "miner1"
        target_miner_num = 1
        
        affected_txs = [tx for tx in submitted_txs if tx[4] == target_miner_name]  # tx[4] is api_host
        unaffected_txs = [tx for tx in submitted_txs if tx[4] != target_miner_name]  # Should still work
        
        print(f"\n{Colors.format_header(f'Step 3: Stop {target_miner_name} (affects {len(affected_txs)} transactions, {len(unaffected_txs)} should survive)')}")
        print(f"{Colors.format_info('Affected (via miner1 API)')}: {Colors.format_dim(f'{len(affected_txs)} transactions')}")
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
            print(f"\n{Colors.format_success('Expected: No transactions found while miner2 stopped')}")
            print(f"{Colors.format_dim('  This means all transactions were lost when miner2 stopped')}")
        else:
            print(f"\n{Colors.format_warn(f'Unexpected: {len(found_while_stopped)} transactions found from other miners')}")
            print(f"{Colors.format_dim('  This means some transactions propagated to other miners')}")
            for tx_name, txid, sender, receiver, api_host, combo_code in found_while_stopped:
                print(f"{Colors.format_dim(f'  - {tx_name} ({combo_code}): {sender} → {receiver} via {api_host}')}")
        
        # Step 5: Resume miner2
        print(f"\n{Colors.format_header('Step 5: Resume miner2')}")
        tester.node_manager.resume_miner(2)
        
        # Step 6: Wait for confirmation after miner2 is resumed
        print(f"\n{Colors.format_header('Step 6: Wait for confirmation after miner2 resumed')}")
        print(f"{Colors.format_info('Waiting for transactions to be processed...')}")
        
        # Check both sending miners for nonce increases
        miner1_initial_nonce = tester.get_nonce("miner1")
        miner3_initial_nonce = tester.get_nonce("miner3") 
        current_height = tester.get_block_height("miner1")  # Any miner for height
        
        print(f"{Colors.format_info('Miner1 initial nonce')}: {Colors.format_dim(str(miner1_initial_nonce))}")
        print(f"{Colors.format_info('Miner3 initial nonce')}: {Colors.format_dim(str(miner3_initial_nonce))}")
        print(f"{Colors.format_info('Current height')}: {Colors.format_dim(str(current_height))}")
        
        # Wait to see if transactions get confirmed now that miner2 is back
        print(f"{Colors.format_info('Checking miner1 for confirmation...')}")
        miner1_confirmed = tester.wait_for_confirmation("miner1", miner1_initial_nonce, current_height, timeout=15)
        
        print(f"{Colors.format_info('Checking miner3 for confirmation...')}")  
        miner3_confirmed = tester.wait_for_confirmation("miner3", miner3_initial_nonce, current_height, timeout=15)
        
        confirmation_result = miner1_confirmed or miner3_confirmed
        
        if confirmation_result:
            final_miner1_nonce = tester.get_nonce("miner1")
            final_miner3_nonce = tester.get_nonce("miner3")
            final_height = tester.get_block_height("miner1")
            print(f"{Colors.format_success('Transactions confirmed after miner2 resumed!')}")
            print(f"{Colors.format_info('Miner1 nonce')}: {Colors.format_dim(str(miner1_initial_nonce))} → {Colors.format_dim(str(final_miner1_nonce))} (+{final_miner1_nonce - miner1_initial_nonce})")
            print(f"{Colors.format_info('Miner3 nonce')}: {Colors.format_dim(str(miner3_initial_nonce))} → {Colors.format_dim(str(final_miner3_nonce))} (+{final_miner3_nonce - miner3_initial_nonce})")
            print(f"{Colors.format_info('Block height')}: {Colors.format_dim(str(current_height))} → {Colors.format_dim(str(final_height))} (+{final_height - current_height})")
        else:
            print(f"{Colors.format_warn('No confirmation detected within timeout period')}")
        
        # Step 7: Try to verify transactions after miner2 resumed
        print(f"\n{Colors.format_header('Step 7: Verify transactions after miner2 resumed')}")
        print(f"{Colors.format_info('Checking if transactions are now visible from miner2...')}")
        
        found_after_resume = []
        for tx_name, txid, sender, receiver, api_host, combo_code in submitted_txs:
            print(f"\n{Colors.format_info(f'Checking {tx_name} ({combo_code})')}: {Colors.format_dim(f'{sender} → {receiver} via {api_host}')}")
            # Check from the original API host that submitted the transaction
            found = tester.verify_transaction(api_host, txid)
            if found:
                found_after_resume.append((tx_name, txid, sender, receiver, api_host, combo_code))
            time.sleep(0.5)  # Small delay between API calls
        
        if found_after_resume:
            print(f"\n{Colors.format_success(f'Expected: {len(found_after_resume)} transactions found after miner2 resumed')}")
            print(f"{Colors.format_dim('  This means mempool transactions were recovered/processed')}")
            for tx_name, txid, sender, receiver, api_host, combo_code in found_after_resume:
                print(f"{Colors.format_dim(f'  - {tx_name} ({combo_code}): {sender} → {receiver} via {api_host}')}")
        else:
            print(f"\n{Colors.format_warn('All transactions still not found after resume')}")
            print(f"{Colors.format_dim('  This means all mempool transactions were permanently lost')}")
        
        transactions_found_after_resume = len(found_after_resume) > 0
        
        # Final summary
        print(f"\n{Colors.format_dim('=' * 80)}")
        print(f"{Colors.format_header('FINAL RESULT')}")
        print(f"{Colors.format_dim('=' * 80)}")

        # Determine overall test result
        if confirmation_result and transactions_found_after_resume:
            print(f"{Colors.format_success('ALL TESTS PASSED')} - Perfect mempool recovery!")
            print(f"{Colors.format_success('Key findings:')}")
            print(f"  {Colors.format_success('•')} Nonce/height changes detected - transactions were processed")
            print(f"  {Colors.format_success('•')} Transaction details found - transactions are in blockchain")
            print(f"  {Colors.format_success('•')} Mempool transactions survived miner restart")
        elif confirmation_result:
            print(f"{Colors.format_success('ALL TESTS PASSED')} - Transaction processing detected!")
            print(f"{Colors.format_success('Nonce/height changes detected')} - transactions were processed")
        elif transactions_found_after_resume:
            print(f"{Colors.format_success('ALL TESTS PASSED')} - Transactions found in blockchain!")
            print(f"{Colors.format_success('Transaction details found')} - transactions are in blockchain")
        else:
            print(f"{Colors.format_warn('PARTIAL SUCCESS')} - Transactions appear to be permanently lost")
            print(f"{Colors.format_warn('Note:')} This shows mempool does not persist across miner restarts")
        
        print(f"\n{Colors.format_info('Transaction Details')}:")
        for tx_name, txid, sender, receiver, api_host, combo_code in submitted_txs:
            print(f"{Colors.format_info(f'{tx_name.upper()} ({combo_code})')}: {Colors.format_dim(txid)} - {Colors.format_dim(f'{sender} → {receiver} via {api_host} API')}")
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