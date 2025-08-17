#!/usr/bin/env python3

import os
import sys
import time

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_api, get_cli, submit_tx, get_nonce, wait_for_confirmation, get_tx_status_typed
from utils.config import AccountManager, MinerName, DeploymentInfo, VerificationResults, TransactionStatus, TxStatus
from utils.miners import MinerManager
from utils.logger import Colors

def generate_contract_files(count: int) -> list:
    """Generate list of contract files cycling through available sizes"""
    base_contracts = [
        "contracts/contract-8kb.clar",
        "contracts/contract-16kb.clar",
        "contracts/contract-24kb.clar"
    ]
    
    contract_files = []
    for i in range(count):
        # Cycle through available contracts
        contract_file = base_contracts[i % len(base_contracts)]
        contract_files.append(contract_file)
    
    return contract_files

def submit_deployment_batch(miner: MinerName, contract_files: list) -> list:
    """Submit batch of contract deployments using raw APIs + helpers"""
    api = get_api(miner)
    cli = get_cli()
    account = AccountManager.get(miner)
    submitted_deployments = []
    
    # Get initial nonce and manage it manually for batch submission
    current_nonce = get_nonce(api, account.address)
    
    print(f"\n{Colors.format_info('Submitting batch of contract deployments...')}")
    print(f"{Colors.format_info('Starting nonce')}: {Colors.format_dim(str(current_nonce))}")
    
    for i, contract_file in enumerate(contract_files):
        try:
            # Get contract file path
            if not os.path.isabs(contract_file):
                contract_path = os.path.join(os.path.dirname(__file__), '..', contract_file)
            else:
                contract_path = contract_file
            
            if not os.path.exists(contract_path):
                print(f"  {i+1:3d}/{len(contract_files)} - SKIPPED: File not found - {contract_path}")
                continue
            
            # Use managed nonce for batch submission
            nonce = current_nonce + i
            contract_name = f"stress-contract-{i+1:03d}"
            
            deployment_info = DeploymentInfo(
                miner=miner,
                contract_name=contract_name,
                contract_file=contract_file,
                nonce=nonce
            )
            
            # Calculate fee based on contract size
            with open(contract_path, 'r') as f:
                contract_code = f.read().strip()
            contract_size = len(contract_code)
            base_fee = max(contract_size, 10000)
            fee = int(base_fee * 1.1)
            
            # Use raw CLI + API
            cmd = cli.publish_contract(account.private_key, fee, nonce, contract_name, contract_path)
            txid = submit_tx(api, cmd)
            
            deployment_info.txid = txid
            deployment_info.status = TransactionStatus.SUBMITTED
            submitted_deployments.append(deployment_info)
            
            print(f"  {i+1:3d}/{len(contract_files)} - TX: {txid[:8]}... - Contract: {contract_name} - Nonce: {nonce} - File: {os.path.basename(contract_file)}")
            
            # Small delay to avoid overwhelming the network
            time.sleep(0.1)
            
        except Exception as e:
            deployment_info.status = TransactionStatus.FAILED
            deployment_info.error = str(e)
            submitted_deployments.append(deployment_info)
            print(f"  {i+1:3d}/{len(contract_files)} - FAILED: {str(e)}")
    
    return submitted_deployments

def verify_deployments(submitted_deployments: list) -> dict:
    """Verify all submitted deployments using raw APIs"""
    verification_results = VerificationResults()
    
    print(f"\n{Colors.format_info('Verifying deployments...')}")
    
    for deployment_info in submitted_deployments:
        if deployment_info.status != TransactionStatus.SUBMITTED:
            verification_results.failed_deployments.append(deployment_info)
            continue
        
        api = get_api(deployment_info.miner)
        
        # Use typed API call with proper error handling
        tx_status = get_tx_status_typed(api, deployment_info.txid)
        
        if tx_status == TxStatus.SUCCESS:
            deployment_info.status = TransactionStatus.CONFIRMED
            verification_results.confirmed_deployments.append(deployment_info)
        elif tx_status in [TxStatus.ABORT_BY_RESPONSE, TxStatus.ABORT_BY_POST_CONDITION]:
            deployment_info.status = TransactionStatus.FAILED
            deployment_info.error = f"Transaction failed with status: {tx_status.value}"
            verification_results.failed_deployments.append(deployment_info)
        elif tx_status == TxStatus.UNKNOWN:
            deployment_info.status = TransactionStatus.PENDING
            verification_results.pending_deployments.append(deployment_info)
        else:
            deployment_info.status = TransactionStatus.PENDING
            verification_results.pending_deployments.append(deployment_info)
    
    return {
        'confirmed': len(verification_results.confirmed_deployments),
        'pending': len(verification_results.pending_deployments),
        'failed': len(verification_results.failed_deployments),
        'total': len(submitted_deployments),
        'details': verification_results
    }

def main():
    """Execute the contract deployment stress test"""
    print(f"{Colors.format_dim('=' * 80)}")
    print(f"{Colors.format_header('STACKS CONTRACT DEPLOYMENT STRESS TEST')}")
    print(f"{Colors.format_dim('=' * 80)}")
    
    # Configuration
    NUM_DEPLOYMENTS = 30  # Test up to 30 deployments to reach expected failure point
    
    # Raw minimal setup
    miners = MinerManager()
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not miners.snapshot_restore("auto"):
            raise RuntimeError("Failed to start miners")
        
        # Generate contract files
        print(f"\n{Colors.format_header('Generating Contract Deployments')}")
        print(f"{Colors.format_info('Number of deployments')}: {Colors.format_dim(str(NUM_DEPLOYMENTS))}")
        
        contract_files = generate_contract_files(NUM_DEPLOYMENTS)
        print(f"{Colors.format_info('Contract files')}:")
        for i, contract_file in enumerate(contract_files):
            print(f"  {i+1}. {contract_file}")
        
        # Submit deployments from MINER1
        print(f"\n{Colors.format_header('Submitting Deployments')}")
        test_miner = MinerName.MINER1
        submitted_deployments = submit_deployment_batch(test_miner, contract_files)
        
        successful_submissions = [d for d in submitted_deployments if d.status == TransactionStatus.SUBMITTED]
        failed_submissions = [d for d in submitted_deployments if d.status == TransactionStatus.FAILED]
        
        print(f"\n{Colors.format_info('Submission Results')}:")
        print(f"  Successful: {Colors.format_success(str(len(successful_submissions)))}")
        print(f"  Failed: {Colors.format_error(str(len(failed_submissions)))}")
        
        if failed_submissions:
            print(f"\n{Colors.format_header('Failed Submissions')}:")
            for deployment in failed_submissions[:3]:  # Show first 3 failures
                print(f"  Contract: {deployment.contract_name}, Error: {deployment.error}")
        
        # Wait for some confirmations
        print(f"\n{Colors.format_header('Waiting for confirmations...')}")
        time.sleep(60)  # Give time for transactions to be processed
        
        # Verify deployments
        verification_results = verify_deployments(submitted_deployments)
        
        print(f"\n{Colors.format_header('Verification Results')}")
        print(f"  Total submitted: {Colors.format_dim(str(verification_results['total']))}")
        print(f"  Confirmed: {Colors.format_success(str(verification_results['confirmed']))}")
        print(f"  Pending: {Colors.format_warn(str(verification_results['pending']))}")
        print(f"  Failed: {Colors.format_error(str(verification_results['failed']))}")
        
        success_rate = (verification_results['confirmed'] / verification_results['total']) * 100 if verification_results['total'] > 0 else 0
        print(f"  Success rate: {Colors.format_info(f'{success_rate:.1f}%')}")
        
        # Show some deployment details
        if verification_results['confirmed'] > 0:
            print(f"\n{Colors.format_header('Sample Confirmed Deployments')}")
            confirmed_deployments = verification_results['details'].confirmed_deployments[:3]  # Show first 3
            for deployment in confirmed_deployments:
                print(f"  TXID: {deployment.txid}")
                print(f"    Contract: {deployment.contract_name}")
                print(f"    File: {deployment.contract_file}")
        
        # Test deployed contracts
        if verification_results['confirmed'] > 0:
            print(f"\n{Colors.format_header('Testing Deployed Contracts')}")
            api = get_api(MinerName.MINER1)
            account = AccountManager.get(MinerName.MINER1)
            
            confirmed_deployments = verification_results['details'].confirmed_deployments
            for deployment in confirmed_deployments[:2]:  # Test first 2
                try:
                    print(f"\n{Colors.format_subheader(f'Testing {deployment.contract_name}')}")
                    # Try to call a function
                    result = api.call_read_only_function(
                        account.address, 
                        deployment.contract_name, 
                        "calc-function-0001",  # This function should exist in test contracts
                        account.address, 
                        []
                    )
                    print(f"  Function call successful: {result}")
                except Exception as e:
                    print(f"  Function call failed: {e}")
        
        return verification_results['confirmed'] > 0
        
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