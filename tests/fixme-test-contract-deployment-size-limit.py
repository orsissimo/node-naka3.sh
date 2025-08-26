#!/usr/bin/env python3

import os
import sys
import time
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_api, get_cli, submit_tx_hex, get_nonce, get_block_height, wait_for_confirmation
from utils.config import AccountManager, Miner
from utils.miners import MinerManager
from utils.logger import Colors

def try_deploy_contract(miner: Miner, contract_file: str, contract_name: str) -> dict:
    """Try to deploy contract and return detailed result"""
    api = get_api(miner)
    cli = get_cli()
    account = AccountManager.get(miner)
    
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
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        size_kb = result['size_kb']
        print(f"\n{Colors.format_subheader(f'--- Deploying {contract_name} ({size_kb:.1f}KB) ---')}")
        print(f"{Colors.format_info('File')}: {Colors.format_dim(contract_path)}")
        print(f"{Colors.format_info('Account')}: {Colors.format_dim(account.address)}")
        print(f"{Colors.format_info('Using nonce')}: {Colors.format_dim(str(initial_nonce))}")
        
        # Calculate fee based on contract size
        contract_size = len(contract_code)
        base_fee = max(contract_size, 10000)
        fee = int(base_fee * 1.1)
        print(f"{Colors.format_info('Using fee')}: {Colors.format_dim(f'{fee} µSTX')}")
        
        # Deploy using raw APIs + helpers
        tx_hex = cli.publish_contract(account.private_key, fee, initial_nonce, contract_name, contract_path)
        print(f"{Colors.format_info('Deploying contract using minimal helpers...')}")
        txid = submit_tx_hex(api, tx_hex)
        result['txid'] = txid
        
        print(f"{Colors.format_success(f'Contract deployment submitted')}: {Colors.format_info(txid)}")
        
        # Wait for confirmation
        if wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=30):
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

def extract_size_from_filename(filename: str) -> int:
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

def analyze_results(results: list) -> dict:
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
    
    # Raw minimal setup
    miners = MinerManager()
    
    # Define contract files to test (ordered by size - biggest to smallest)
    contract_files = [
        "contracts/contract-8000kb.clar",
        "contracts/contract-6000kb.clar",
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
        if not miners.snapshot_restore_auto():
            raise RuntimeError("Failed to start miners")
        
        print(f"\n{Colors.format_header('Testing contract deployment size limits')}")
        print(f"{Colors.format_info('Total contracts to test')}: {Colors.format_dim(str(len(contract_files)))}")
        
        # Test each contract
        results = []
        test_miner = Miner.MINER1  # Use only the first miner
        
        for i, contract_file in enumerate(contract_files):
            miner = test_miner  # Always use miner1
            size_kb = extract_size_from_filename(contract_file)
            contract_name = f"contract-{size_kb}kb" if size_kb else f"contract-{i+1}"
            
            result = try_deploy_contract(miner, contract_file, contract_name)
            results.append(result)
            
            # Small delay between deployments
            time.sleep(1)
        
        # Analyze results
        analysis = analyze_results(results)
        
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
                api = get_api(Miner.MINER1)
                account = AccountManager.get(Miner.MINER1)
                
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
        miners.stop()
        miners.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)