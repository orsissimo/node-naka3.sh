#!/usr/bin/env python3

import os
import sys
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_api, get_cli, submit_tx_hex, get_nonce, get_block_height, wait_for_confirmation
from utils.config import AccountManager, Miner
from utils.miners import MinerManager
from utils.logger import Colors

def main():
    """Execute the contract deployment and interaction test"""
    print(f"{Colors.format_dim('=' * 60)}")
    print(f"{Colors.format_header('CONTRACT COUNTER DEPLOYMENT AND INTERACTIONS TEST')}")
    print(f"{Colors.format_dim('=' * 60)}")
    
    # Raw minimal setup
    miners = MinerManager()
    api = get_api(Miner.MINER1)
    cli = get_cli()
    account = AccountManager.get(Miner.MINER1)
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not miners.snapshot_restore_auto():
            raise RuntimeError("Failed to start miners")
        
        # Step 1: Deploy counter contract
        print(f"\n{Colors.format_header('Step 1: Deploy counter contract')}")
        print(f"{Colors.format_info('Contract')}: {Colors.format_dim('mycontract')}")
        print(f"{Colors.format_info('File')}: {Colors.format_dim('contracts/contract-counter.clar')}")
        
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        tx_hex = cli.publish_contract(account.private_key, 5000, initial_nonce, "mycontract", 
                                    os.path.join(os.path.dirname(__file__), "..", "contracts/contract-counter.clar"))
        deploy_txid = submit_tx_hex(api, tx_hex)
        print(f"{Colors.format_success('Contract deployed')}: {Colors.format_info(deploy_txid)}")
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract deployment confirmation timeout")
        print(f"{Colors.format_success('Contract mycontract deployment confirmed!')}")
        
        # Step 2: Read initial counter value  
        print(f"\n{Colors.format_header('Step 2: Read initial counter')}")
        initial_counter = api.call_read_only_function(account.address, "mycontract", "get-counter", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(initial_counter, indent=2))}")
        
        # Step 3: Read initial last caller
        print(f"\n{Colors.format_header('Step 3: Read initial last caller')}")
        initial_caller = api.call_read_only_function(account.address, "mycontract", "get-last-caller", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(initial_caller, indent=2))}")
        
        # Step 4: Increment counter
        print(f"\n{Colors.format_header('Step 4: Increment counter')}")
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        tx_hex = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "mycontract", "increment", [])
        increment_txid = submit_tx_hex(api, tx_hex)
        print(f"{Colors.format_success('Contract call submitted')}: {Colors.format_info(increment_txid)}")
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        print(f"{Colors.format_success('increment call confirmed!')}")
        
        # Step 5: Read counter after increment
        print(f"\n{Colors.format_header('Step 5: Read counter after increment')}")
        after_increment_counter = api.call_read_only_function(account.address, "mycontract", "get-counter", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(after_increment_counter, indent=2))}")
        
        # Step 6: Read last caller after increment
        print(f"\n{Colors.format_header('Step 6: Read last caller after increment')}")
        after_increment_caller = api.call_read_only_function(account.address, "mycontract", "get-last-caller", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(after_increment_caller, indent=2))}")
        
        # Step 7: Reset counter
        print(f"\n{Colors.format_header('Step 7: Reset counter')}")
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        tx_hex = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "mycontract", "reset", [])
        reset_txid = submit_tx_hex(api, tx_hex)
        print(f"{Colors.format_success('Contract call submitted')}: {Colors.format_info(reset_txid)}")
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        print(f"{Colors.format_success('reset call confirmed!')}")
        
        # Step 8: Read counter after reset
        print(f"\n{Colors.format_header('Step 8: Read counter after reset')}")
        after_reset_counter = api.call_read_only_function(account.address, "mycontract", "get-counter", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(after_reset_counter, indent=2))}")
        
        # Step 9: Read last caller after reset
        print(f"\n{Colors.format_header('Step 9: Read last caller after reset')}")
        after_reset_caller = api.call_read_only_function(account.address, "mycontract", "get-last-caller", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(after_reset_caller, indent=2))}")
        
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
        miners.stop()
        miners.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)