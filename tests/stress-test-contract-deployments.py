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

class ContractDeploymentStressTester:
    """Direct contract deployment stress testing without recipes framework"""
    
    def __init__(self):
        self.node_manager = NodeManager()
        self.cli = BlockstackCLIWrapper()
        self.submitted_deployments = []
        
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
    
    def generate_contract_files(self, count: int) -> List[str]:
        """Generate list of contract files cycling through available sizes"""
        base_contracts = [
            "contracts/contract-8kb.clar",
            "contracts/contract-16kb.clar",
            "contracts/contract-24kb.clar",
            "contracts/contract-40kb.clar",
            "contracts/contract-60kb.clar",
            "contracts/contract-80kb.clar",
            "contracts/contract-100kb.clar",
            "contracts/contract-120kb.clar",
            "contracts/contract-160kb.clar",
            "contracts/contract-200kb.clar",
            "contracts/contract-240kb.clar",
            "contracts/contract-300kb.clar",
            "contracts/contract-400kb.clar",
            "contracts/contract-500kb.clar",
            "contracts/contract-600kb.clar",
            "contracts/contract-700kb.clar",
            "contracts/contract-800kb.clar",
            "contracts/contract-900kb.clar",
            "contracts/contract-1000kb.clar"
        ]
        
        # Cycle through contracts if count > available files
        contract_files = []
        for i in range(count):
            contract_files.append(base_contracts[i % len(base_contracts)])
        
        return contract_files
    
    def extract_size_from_filename(self, filename: str) -> Optional[int]:
        """Extract size in KB from filename like 'contract-120kb.clar'"""
        try:
            if 'contract-' in filename and 'kb.clar' in filename:
                start = filename.find('contract-') + 9
                end = filename.find('kb.clar')
                size_str = filename[start:end]
                return int(size_str)
        except:
            pass
        return None
    
    def submit_contract_deployment(self, miner: str, contract_file: str, contract_name: str, nonce: int) -> Dict[str, Any]:
        """Submit contract deployment without waiting for confirmation"""
        account = ACCOUNTS[miner]
        api = StacksCoreAPIWrapper(base_url=account.api_url)
        
        # Get contract file path
        if not os.path.isabs(contract_file):
            contract_path = os.path.join(os.path.dirname(__file__), '..', contract_file)
        else:
            contract_path = contract_file
        
        deployment_info = {
            'miner': miner,
            'contract_file': contract_file,
            'contract_name': contract_name,
            'nonce': nonce,
            'submitted': False,
            'txid': None,
            'error': None,
            'size_kb': 0
        }
        
        if not os.path.exists(contract_path):
            deployment_info['error'] = f"Contract file not found: {contract_path}"
            return deployment_info
        
        try:
            # Get contract size and content
            with open(contract_path, 'r') as f:
                contract_code = f.read().strip()
            
            deployment_info['size_kb'] = len(contract_code) / 1024
            
            print(f"{Colors.format_info('Submitting')}: {contract_name} ({deployment_info['size_kb']:.1f}KB) with nonce {nonce}")
            
            # Calculate fee
            contract_size = len(contract_code)
            base_fee = max(contract_size, 10000)
            fee = int(base_fee * 1.1)
            
            # Build CLI command
            cmd = self.cli.publish_contract(account.private_key, fee, nonce, contract_name, contract_path)
            
            # Create transaction binary
            tx_binary = self.run_cli_command(cmd, binary_output=True)
            
            # Submit transaction
            txid = api.post_raw_transaction(tx_binary)
            deployment_info['txid'] = txid
            deployment_info['submitted'] = True
            
            print(f"{Colors.format_success('Submitted')}: {contract_name} -> {txid}")
            
        except Exception as e:
            deployment_info['error'] = str(e)
            print(f"{Colors.format_error('Failed')}: {contract_name} -> {str(e)}")
        
        return deployment_info
    
    def batch_submit_contracts(self, miner: str, contract_count: int) -> List[Dict[str, Any]]:
        """Submit multiple contracts rapidly to test mempool limits"""
        print(f"\n{Colors.format_header('=== BATCH CONTRACT DEPLOYMENT ===')}")
        print(f"{Colors.format_info('Miner')}: {Colors.format_dim(miner)}")
        print(f"{Colors.format_info('Contract count')}: {Colors.format_dim(str(contract_count))}")
        
        # Get initial state
        initial_nonce = self.get_nonce(miner)
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        print(f"{Colors.format_info('Initial nonce')}: {Colors.format_dim(str(initial_nonce))}")
        print(f"{Colors.format_info('Initial balance')}: {Colors.format_dim(str(initial_balance))}")
        print(f"{Colors.format_info('Initial height')}: {Colors.format_dim(str(initial_height))}")
        
        # Generate contract files
        contract_files = self.generate_contract_files(contract_count)
        
        # Submit all contracts rapidly
        deployments = []
        current_nonce = initial_nonce
        
        print(f"\n{Colors.format_subheader('Submitting contracts rapidly...')}")
        start_time = time.time()
        
        for i, contract_file in enumerate(contract_files, 1):
            size_kb = self.extract_size_from_filename(contract_file)
            contract_name = f"stress-{size_kb}kb-{i}" if size_kb else f"stress-contract-{i}"
            
            deployment = self.submit_contract_deployment(miner, contract_file, contract_name, current_nonce)
            deployments.append(deployment)
            
            if deployment['submitted']:
                current_nonce += 1
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.1)
        
        end_time = time.time()
        submission_duration = end_time - start_time
        
        print(f"\n{Colors.format_info('Submission completed in')}: {Colors.format_dim(f'{submission_duration:.2f} seconds')}")
        
        successful_submissions = [d for d in deployments if d['submitted']]
        failed_submissions = [d for d in deployments if not d['submitted']]
        
        print(f"{Colors.format_success('Successful submissions')}: {Colors.format_dim(str(len(successful_submissions)))}")
        print(f"{Colors.format_error('Failed submissions')}: {Colors.format_dim(str(len(failed_submissions)))}")
        
        if failed_submissions:
            print(f"\n{Colors.format_subheader('Failed submission details')}:")
            for i, failed in enumerate(failed_submissions, 1):
                print(f"  {i}. {failed['contract_name']}: {Colors.format_error(failed['error'])}")
        
        return deployments
    
    def wait_and_verify_deployments(self, deployments: List[Dict[str, Any]], timeout: int = 120) -> Dict[str, Any]:
        """Wait for deployments to be confirmed and verify results"""
        print(f"\n{Colors.format_header('=== VERIFICATION PHASE ===')}")
        
        successful_deployments = [d for d in deployments if d['submitted']]
        if not successful_deployments:
            return {
                'confirmed': 0,
                'failed': 0,
                'pending': 0,
                'success_rate': 0.0,
                'confirmed_deployments': [],
                'failed_deployments': [],
                'pending_deployments': []
            }
        
        miner = successful_deployments[0]['miner']  # Use first deployment's miner
        
        print(f"{Colors.format_info('Waiting for confirmations')}: {Colors.format_dim(f'{timeout}s timeout')}")
        print(f"{Colors.format_info('Tracking')}: {Colors.format_dim(f'{len(successful_deployments)} submitted deployments')}")
        
        start_time = time.time()
        confirmed_deployments = []
        failed_deployments = []
        
        while time.time() - start_time < timeout and len(confirmed_deployments) + len(failed_deployments) < len(successful_deployments):
            # Check each unresolved deployment
            unresolved = [d for d in successful_deployments if d not in confirmed_deployments and d not in failed_deployments]
            
            for deployment in unresolved[:5]:  # Check up to 5 at a time to avoid overwhelming API
                try:
                    account = ACCOUNTS[miner]
                    api = StacksCoreAPIWrapper(base_url=account.api_url)
                    
                    # Try to get transaction info
                    tx_info = api.get_transaction_by_id(deployment['txid'])
                    tx_status = tx_info.get('tx_status', 'unknown')
                    
                    if tx_status == 'success':
                        confirmed_deployments.append(deployment)
                        print(f"{Colors.format_success('✓')} {deployment['contract_name']}: {Colors.format_success('Confirmed')}")
                    elif tx_status in ['abort_by_response', 'abort_by_post_condition']:
                        failed_deployments.append(deployment)
                        print(f"{Colors.format_error('✗')} {deployment['contract_name']}: {Colors.format_error('Failed')} ({tx_status})")
                    
                except Exception as e:
                    # Transaction might not be found yet, continue waiting
                    pass
            
            time.sleep(2)  # Wait before next check
        
        pending_deployments = [d for d in successful_deployments if d not in confirmed_deployments and d not in failed_deployments]
        
        # Final summary
        total_submitted = len(successful_deployments)
        confirmed_count = len(confirmed_deployments)
        failed_count = len(failed_deployments)
        pending_count = len(pending_deployments)
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
            'confirmed_deployments': confirmed_deployments,
            'failed_deployments': failed_deployments,
            'pending_deployments': pending_deployments
        }

def main():
    """Execute the contract deployment stress test"""
    print(f"{Colors.format_dim('=' * 80)}")
    print(f"{Colors.format_header('STACKS CONTRACT DEPLOYMENT STRESS TEST')}")
    print(f"{Colors.format_dim('=' * 80)}")
    
    tester = ContractDeploymentStressTester()
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not tester.node_manager.start_node():
            raise RuntimeError("Failed to start miners")
        
        # Configuration
        contract_count = 50  # Test with 50 contracts initially
        test_miner = "miner1"
        
        print(f"\n{Colors.format_header('Test Configuration')}:")
        print(f"  Target contracts: {Colors.format_dim(str(contract_count))}")
        print(f"  Test miner: {Colors.format_dim(test_miner)}")
        
        # Step 1: Batch submit contracts
        print(f"\n{Colors.format_header('Step 1: Batch submit contracts')}")
        deployments = tester.batch_submit_contracts(test_miner, contract_count)
        
        # Step 2: Wait and verify
        print(f"\n{Colors.format_header('Step 2: Wait and verify deployments')}")
        verification_results = tester.wait_and_verify_deployments(deployments)
        
        # Step 3: Analyze results
        print(f"\n{Colors.format_header('Step 3: Analyze stress test results')}")
        
        successful_submissions = [d for d in deployments if d['submitted']]
        submission_rate = (len(successful_submissions) / len(deployments)) * 100 if deployments else 0
        
        print(f"\n{Colors.format_subheader('Submission Analysis')}:")
        print(f"  Total attempted: {Colors.format_dim(str(len(deployments)))}")
        print(f"  Successfully submitted: {Colors.format_success(str(len(successful_submissions)))}")
        print(f"  Submission rate: {Colors.format_info(f'{submission_rate:.1f}%')}")
        
        print(f"\n{Colors.format_subheader('Confirmation Analysis')}:")
        print(f"  Confirmed deployments: {Colors.format_success(str(verification_results['confirmed']))}")
        print(f"  Failed deployments: {Colors.format_error(str(verification_results['failed']))}")
        print(f"  Pending deployments: {Colors.format_warn(str(verification_results['pending']))}")
        success_rate = verification_results['success_rate']
        print(f"  Confirmation rate: {Colors.format_info(f'{success_rate:.1f}%')}")
        
        # Determine test success
        # Consider test successful if at least 80% submission rate and 50% confirmation rate
        test_success = submission_rate >= 80.0 and verification_results['success_rate'] >= 50.0
        
        if verification_results['confirmed'] > 0:
            print(f"\n{Colors.format_subheader('Contract Size Analysis')}:")
            confirmed = verification_results['confirmed_deployments']
            sizes = [d['size_kb'] for d in confirmed if d['size_kb'] > 0]
            if sizes:
                avg_size = sum(sizes) / len(sizes)
                min_size = min(sizes)
                max_size = max(sizes)
                print(f"  Average deployed size: {Colors.format_dim(f'{avg_size:.1f}KB')}")
                print(f"  Size range: {Colors.format_dim(f'{min_size:.1f}KB - {max_size:.1f}KB')}")
        
        # Final summary
        print(f"\n{Colors.format_dim('=' * 80)}")
        print(f"{Colors.format_header('FINAL RESULT')}")
        print(f"{Colors.format_dim('=' * 80)}")
        
        if test_success:
            print(f"{Colors.format_success('✓ STRESS TEST PASSED')}")
            print(f"  The system handled contract deployment stress appropriately")
            print(f"  Submission rate: {Colors.format_success(f'{submission_rate:.1f}%')}")
            success_rate = verification_results['success_rate']
            print(f"  Confirmation rate: {Colors.format_success(f'{success_rate:.1f}%')}")
        else:
            print(f"{Colors.format_error('✗ STRESS TEST FAILED')}")
            print(f"  The system showed poor performance under contract deployment stress")
            print(f"  Submission rate: {Colors.format_error(f'{submission_rate:.1f}%')} (target: ≥80%)")
            success_rate = verification_results['success_rate']
            print(f"  Confirmation rate: {Colors.format_error(f'{success_rate:.1f}%')} (target: ≥50%)")
        
        return test_success
        
    except Exception as e:
        print(f"\n{Colors.format_error('✗ TEST FAILED')}: {Colors.format_error(str(e))}")
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