#!/usr/bin/env python3

import os
import sys
import time
import json
import subprocess
from typing import Dict, Any, Optional

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config import MinerName
from utils.base_test import BaseTestClass
from utils.logger import Colors, logger

class ContractTester(BaseTestClass):
    """Direct contract testing without recipes framework"""
    
    def __init__(self):
        super().__init__()
    
    def deploy_contract_with_details(self, miner: MinerName, contract_file: str, contract_name: str) -> str:
        """Deploy contract with detailed logging and return transaction ID"""
        print(f"\n{Colors.format_header('=== CONTRACT DEPLOYMENT ===')}")
        print(f"{Colors.format_info('Contract')}: {Colors.format_dim(contract_name)}")
        print(f"{Colors.format_info('File')}: {Colors.format_dim(contract_file)}")
        print(f"{Colors.format_info('Miner')}: {Colors.format_dim(miner.value)}")
        
        # Get initial state for nonce-based confirmation
        initial_nonce = self.get_nonce(miner)
        initial_height = self.get_block_height(miner)
        
        # Use BaseTestClass deploy_contract method
        txid = self.deploy_contract(miner, contract_file, contract_name)
        print(f"{Colors.format_success('Contract deployed')}: {Colors.format_info(txid)}")
        
        # Wait for confirmation using the original working approach
        print(f"\n{Colors.format_info('Waiting for confirmation...')}")
        if self.wait_for_confirmation(miner, initial_nonce, initial_height, timeout=120):
            print(f"{Colors.format_success(f'Contract {contract_name} deployment confirmed!')}")
            return txid
        else:
            raise RuntimeError("Contract deployment confirmation timeout")
    
    def read_contract_with_details(self, miner: MinerName, contract_address: str, contract_name: str, function_name: str) -> Dict[str, Any]:
        """Call read-only contract function with detailed logging"""
        print(f"\n{Colors.format_subheader('--- CONTRACT READ CALL ---')}")
        print(f"{Colors.format_info('Contract')}: {Colors.format_dim(f'{contract_address}.{contract_name}')}")
        print(f"{Colors.format_info('Function')}: {Colors.format_dim(function_name)}")
        
        # Use BaseTestClass read_contract method
        result = self.read_contract(miner, contract_address, contract_name, function_name)
        
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(result, indent=2))}")
        
        return result
    
    def call_contract_with_details(self, miner: MinerName, contract_address: str, contract_name: str, function_name: str) -> str:
        """Call contract function with detailed logging and return transaction ID"""
        print(f"\n{Colors.format_header('=== CONTRACT CALL ===')}")
        print(f"{Colors.format_info('Contract')}: {Colors.format_dim(f'{contract_address}.{contract_name}')}")
        print(f"{Colors.format_info('Function')}: {Colors.format_dim(function_name)}")
        
        # Get initial state for nonce-based confirmation
        initial_nonce = self.get_nonce(miner)
        initial_height = self.get_block_height(miner)
        
        # Use BaseTestClass call_contract method
        txid = self.call_contract(miner, contract_address, contract_name, function_name)
        print(f"{Colors.format_success('Contract call submitted')}: {Colors.format_info(txid)}")
        
        # Wait for confirmation using the original working approach
        print(f"\n{Colors.format_info('Waiting for confirmation...')}")
        if self.wait_for_confirmation(miner, initial_nonce, initial_height, timeout=120):
            print(f"{Colors.format_success(f'{function_name} call confirmed!')}")
            return txid
        else:
            raise RuntimeError("Contract call confirmation timeout")

def main():
    """Execute the contract deployment and interaction test"""
    print(f"{Colors.format_dim('=' * 60)}")
    print(f"{Colors.format_header('CONTRACT COUNTER DEPLOYMENT AND INTERACTIONS TEST')}")
    print(f"{Colors.format_dim('=' * 60)}")
    
    tester = ContractTester()
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not tester.start_node():
            raise RuntimeError("Failed to start miners")
        
        # Step 1: Deploy counter contract
        print(f"\n{Colors.format_header('Step 1: Deploy counter contract')}")
        deploy_txid = tester.deploy_contract_with_details(MinerName.MINER1, "contracts/contract-counter.clar", "mycontract")
        
        # Step 2: Read initial counter value  
        print(f"\n{Colors.format_header('Step 2: Read initial counter')}")
        initial_counter = tester.read_contract_with_details(MinerName.MINER1, tester.miner1.address, "mycontract", "get-counter")
        
        # Step 3: Read initial last caller
        print(f"\n{Colors.format_header('Step 3: Read initial last caller')}")
        initial_caller = tester.read_contract_with_details(MinerName.MINER1, tester.miner1.address, "mycontract", "get-last-caller")
        
        # Step 4: Increment counter
        print(f"\n{Colors.format_header('Step 4: Increment counter')}")
        increment_txid = tester.call_contract_with_details(MinerName.MINER1, tester.miner1.address, "mycontract", "increment")
        
        # Step 5: Read counter after increment
        print(f"\n{Colors.format_header('Step 5: Read counter after increment')}")
        after_increment_counter = tester.read_contract_with_details(MinerName.MINER1, tester.miner1.address, "mycontract", "get-counter")
        
        # Step 6: Read last caller after increment
        print(f"\n{Colors.format_header('Step 6: Read last caller after increment')}")
        after_increment_caller = tester.read_contract_with_details(MinerName.MINER1, tester.miner1.address, "mycontract", "get-last-caller")
        
        # Step 7: Reset counter
        print(f"\n{Colors.format_header('Step 7: Reset counter')}")
        reset_txid = tester.call_contract_with_details(MinerName.MINER1, tester.miner1.address, "mycontract", "reset")
        
        # Step 8: Read counter after reset
        print(f"\n{Colors.format_header('Step 8: Read counter after reset')}")
        after_reset_counter = tester.read_contract_with_details(MinerName.MINER1, tester.miner1.address, "mycontract", "get-counter")
        
        # Step 9: Read last caller after reset
        print(f"\n{Colors.format_header('Step 9: Read last caller after reset')}")
        after_reset_caller = tester.read_contract_with_details(MinerName.MINER1, tester.miner1.address, "mycontract", "get-last-caller")
        
        # Final summary
        print(f"\n{Colors.format_dim('=' * 60)}")
        print(f"{Colors.format_header('FINAL RESULT')}")
        print(f"{Colors.format_dim('=' * 60)}")
        
        print(f"{Colors.format_info('Deploy TXID')}: {Colors.format_dim(deploy_txid)}")
        print(f"{Colors.format_info('Increment TXID')}: {Colors.format_dim(increment_txid)}")
        print(f"{Colors.format_info('Reset TXID')}: {Colors.format_dim(reset_txid)}")
        
        return True
        
    except Exception as e:
        print(f"\n{Colors.format_error('✗ TEST FAILED')}: {Colors.format_error(str(e))}")
        return False
        
    finally:
        # Cleanup
        print(f"\n{Colors.format_header('Cleaning up...')}")
        tester.stop_node()
        tester.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)