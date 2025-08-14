#!/usr/bin/env python3

import os
import sys
import time
import json
import subprocess
from typing import Dict, Any, Optional, List

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config import ACCOUNTS, Account, MinerName, AccountManager
from utils.stacks_core_api import StacksCoreAPIWrapper
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.node_manager import NodeManager
from utils.logger import Colors, logger

class SizeLimitTester:
    """Direct size limit testing without recipes framework"""
    
    def __init__(self):
        self.node_manager = NodeManager()
        self.cli = BlockstackCLIWrapper()
        self.miner1 = AccountManager.get(MinerName.MINER1)
        self.miner2 = AccountManager.get(MinerName.MINER2)
        self.miner3 = AccountManager.get(MinerName.MINER3)
        
    def get_account_info(self, miner: str) -> Dict[str, Any]:
        """Get account info (balance, nonce)"""
        account = AccountManager.get_by_name(miner)
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
        account = AccountManager.get_by_name(miner)
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
    
    def try_deploy_contract(self, miner: str, contract_file: str, contract_name: str) -> Dict[str, Any]:
        """Try to deploy contract and return detailed result"""
        account = AccountManager.get_by_name(miner)
        api = StacksCoreAPIWrapper(base_url=account.api_url)
        
        # Get contract file path
        if not os.path.isabs(contract_file):
            contract_path = os.path.join(os.path.dirname(__file__), '..', contract_file)
        else:
            contract_path = contract_file
        
        result = {
            'contract_name': contract_name,
            'contract_file': contract_file,
            'contract_path': contract_path,
            'success': False,
            'error': None,
            'txid': None,
            'size_kb': 0
        }
        
        if not os.path.exists(contract_path):
            result['error'] = f"Contract file not found: {contract_path}"
            return result
        
        # Get contract size
        try:
            with open(contract_path, 'r') as f:
                contract_code = f.read().strip()
            result['size_kb'] = len(contract_code) / 1024
        except Exception as e:
            result['error'] = f"Could not read contract file: {e}"
            return result
        
        try:
            # Get initial state
            initial_nonce = self.get_nonce(miner)
            initial_balance = self.get_balance(miner)
            initial_height = self.get_block_height(miner)
            
            size_kb = result['size_kb']
            print(f"\n{Colors.format_subheader(f'--- Deploying {contract_name} ({size_kb:.1f}KB) ---')}")
            print(f"{Colors.format_info('File')}: {Colors.format_dim(contract_path)}")
            print(f"{Colors.format_info('Account')}: {Colors.format_dim(account.address)}")
            print(f"{Colors.format_info('Using nonce')}: {Colors.format_dim(str(initial_nonce))}")
            
            # Calculate fee based on contract size
            contract_size = len(contract_code)
            base_fee = max(contract_size, 10000)
            fee = str(int(base_fee * 1.1))
            print(f"{Colors.format_info('Using fee')}: {Colors.format_dim(f'{fee} µSTX')}")
            
            # Build and run CLI command
            cmd = self.cli.publish_contract(account.private_key, int(fee), initial_nonce, contract_name, contract_path)
            
            print(f"{Colors.format_info('Creating contract deployment transaction...')}")
            tx_binary = self.run_cli_command(cmd, binary_output=True)
            
            print(f"{Colors.format_info('Submitting transaction...')}")
            txid = api.post_raw_transaction(tx_binary)
            result['txid'] = txid
            
            print(f"{Colors.format_success(f'Contract deployment submitted')}: {Colors.format_info(txid)}")
            
            
            # Wait for confirmation
            if self.wait_for_confirmation(miner, initial_nonce, initial_height, timeout=30):
                result['success'] = True
                
                # Get transaction details from v3 API after confirmation
                try:
                    print(f"{Colors.format_info('Fetching confirmed transaction details from v3 API...')}")
                    tx_details = api.get_transaction_by_id(txid)
                    print(f"{Colors.format_info('V3 API Response')}: {Colors.format_dim(json.dumps(tx_details, indent=2))}")
                except Exception as api_error:
                    print(f"{Colors.format_warn('Could not fetch v3 API details')}: {Colors.format_dim(str(api_error))}")
                print(f"{Colors.format_success(f'{contract_name} deployed successfully!')}")
            else:
                result['error'] = "Confirmation timeout"
                print(f"{Colors.format_error(f'✗ {contract_name} confirmation timeout')}")
                
        except Exception as e:
            result['error'] = str(e)
            print(f"{Colors.format_error(f'{contract_name} deployment failed')}: {Colors.format_error(str(e))}")
        
        return result
    
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
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze deployment results to find size limits"""
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        analysis = {
            'total_tested': len(results),
            'successful_count': len(successful),
            'failed_count': len(failed),
            'largest_successful': None,
            'smallest_failed': None,
            'limit_found': False,
            'limit_range': None
        }
        
        if successful:
            analysis['largest_successful'] = max(successful, key=lambda x: x['size_kb'])
        
        if failed:
            analysis['smallest_failed'] = min(failed, key=lambda x: x['size_kb'])
        
        if analysis['largest_successful'] and analysis['smallest_failed']:
            largest_size = analysis['largest_successful']['size_kb']
            smallest_failed_size = analysis['smallest_failed']['size_kb']
            if largest_size < smallest_failed_size:
                analysis['limit_found'] = True
                analysis['limit_range'] = (largest_size, smallest_failed_size)
        
        return analysis

def main():
    """Execute the size limit test"""
    print(f"{Colors.format_dim('=' * 80)}")
    print(f"{Colors.format_header('STACKS CONTRACT DEPLOYMENT SIZE LIMIT TEST')}")
    print(f"{Colors.format_dim('=' * 80)}")
    
    tester = SizeLimitTester()
    
    # Define contract files to test (ordered by size - biggest to smallest)
    contract_files = [
        "contracts/contract-4000kb.clar",
        "contracts/contract-3000kb.clar",
        "contracts/contract-2250kb.clar",
        "contracts/contract-2000kb.clar",
        "contracts/contract-1500kb.clar",
        "contracts/contract-1200kb.clar",
        "contracts/contract-1000kb.clar",
        "contracts/contract-900kb.clar",
        "contracts/contract-800kb.clar",
        "contracts/contract-700kb.clar",
        "contracts/contract-600kb.clar",
        "contracts/contract-500kb.clar",
        "contracts/contract-400kb.clar",
        "contracts/contract-300kb.clar",
        "contracts/contract-240kb.clar",
        "contracts/contract-200kb.clar",
        "contracts/contract-160kb.clar",
        "contracts/contract-120kb.clar",
        "contracts/contract-100kb.clar",
        "contracts/contract-80kb.clar",
        "contracts/contract-60kb.clar",
        "contracts/contract-40kb.clar",
        "contracts/contract-24kb.clar", 
        "contracts/contract-16kb.clar",
        "contracts/contract-8kb.clar"
    ]
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not tester.node_manager.start_node():
            raise RuntimeError("Failed to start miners")
        
        print(f"\n{Colors.format_header('Testing contract deployment size limits')}")
        print(f"{Colors.format_info('Total contracts to test')}: {Colors.format_dim(str(len(contract_files)))}")
        
        # Test each contract
        results = []
        test_miner = "miner1"  # Use only the first miner
        
        for i, contract_file in enumerate(contract_files):
            miner = test_miner  # Always use miner1
            size_kb = tester.extract_size_from_filename(contract_file)
            contract_name = f"contract-{size_kb}kb" if size_kb else f"contract-{i+1}"
            
            result = tester.try_deploy_contract(miner, contract_file, contract_name)
            results.append(result)
            
            # Small delay between deployments
            time.sleep(1)
        
        # Analyze results
        analysis = tester.analyze_results(results)
        
        print(f"\n{Colors.format_dim('=' * 80)}")
        print(f"{Colors.format_header('SIZE LIMIT ANALYSIS')}")
        print(f"{Colors.format_dim('=' * 80)}")
        
        print(f"\n{Colors.format_info('Summary')}:")
        print(f"  Total contracts tested: {Colors.format_dim(str(analysis['total_tested']))}")
        print(f"  Successful deployments: {Colors.format_success(str(analysis['successful_count']))}")
        print(f"  Failed deployments: {Colors.format_error(str(analysis['failed_count']))}")
        
        if analysis['largest_successful']:
            largest = analysis['largest_successful']
            largest_size = largest['size_kb']
            print(f"  Largest successful: {Colors.format_success(f'{largest_size:.1f}KB')} ({largest['contract_name']})")
        
        if analysis['smallest_failed']:
            smallest = analysis['smallest_failed']
            smallest_size = smallest['size_kb']
            print(f"  Smallest failed: {Colors.format_error(f'{smallest_size:.1f}KB')} ({smallest['contract_name']})")
            print(f"  Failure reason: {Colors.format_dim(smallest['error'])}")
        
        if analysis['limit_found']:
            range_start, range_end = analysis['limit_range']
            print(f"\n{Colors.format_success('SIZE LIMIT FOUND!')}")
            print(f"  The deployment size limit is between {Colors.format_info(f'{range_start:.1f}KB')} and {Colors.format_info(f'{range_end:.1f}KB')}")
        else:
            print(f"\n{Colors.format_warn('Size limit boundary not clearly identified')}")
            if analysis['successful_count'] == analysis['total_tested']:
                print(f"  All contracts deployed successfully - need to test larger contracts")
            elif analysis['failed_count'] == analysis['total_tested']:
                print(f"  All contracts failed - need to test smaller contracts")
            else:
                print(f"  Results are mixed - may need more targeted testing")
        
        # Detailed results
        print(f"\n{Colors.format_header('Detailed Results')}:")
        for i, result in enumerate(results, 1):
            status = Colors.format_success('SUCCESS') if result['success'] else Colors.format_error('FAILED')
            size_info = f"{result['size_kb']:.1f}KB"
            print(f"  {i:2d}. {result['contract_name']:20} ({size_info:>8}): {status}")
            if not result['success'] and result['error']:
                error_preview = result['error'][:80] + "..." if len(result['error']) > 80 else result['error']
                print(f"      {Colors.format_dim(error_preview)}")
        
        # Test some working contracts
        working_contracts = [r for r in results if r['success']]
        if len(working_contracts) >= 2:
            print(f"\n{Colors.format_header('Testing deployed contract functionality')}")
            
            # Test smallest successful contract
            smallest_working = min(working_contracts, key=lambda x: x['size_kb'])
            print(f"\n{Colors.format_subheader('Testing smallest working contract')}")
            print(f"Contract: {smallest_working['contract_name']} ({smallest_working['size_kb']:.1f}KB)")
            
            try:
                account = AccountManager.get(MinerName.MINER1)
                api = StacksCoreAPIWrapper(base_url=account.api_url)
                
                # Try to call a function (first try without arguments)
                function_name = "calc-function-0001"
                try:
                    result = api.call_read_only_function(
                        account.address, 
                        smallest_working['contract_name'], 
                        function_name, 
                        account.address, 
                        []  # No arguments first
                    )
                except Exception as no_args_error:
                    # If no-args version fails, try with properly hex-encoded argument
                    print(f"{Colors.format_info('Retrying with hex-encoded argument...')}")
                    # u12345 in hex is 0x0100000000000000000000000000003039 (uint 12345)
                    result = api.call_read_only_function(
                        account.address, 
                        smallest_working['contract_name'], 
                        function_name, 
                        account.address, 
                        ["0x0100000000000000000000000000003039"]
                    )
                print(f"{Colors.format_success('Contract function call successful')}")
                print(f"Function: {function_name}, Result: {Colors.format_dim(json.dumps(result))}")
                
            except Exception as e:
                print(f"{Colors.format_warn('Contract function test failed')}: {Colors.format_dim(str(e))}")
        
        return analysis['limit_found'] or analysis['successful_count'] > 0
        
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