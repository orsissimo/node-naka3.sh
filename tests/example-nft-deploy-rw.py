#!/usr/bin/env python3

import os
import sys
import time
import json
import subprocess
from typing import Dict, Any, Optional

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config import ACCOUNTS, Account
from utils.stacks_core_api import StacksCoreAPIWrapper
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.node_manager import NodeManager
from utils.colors import Colors, logger

class NFTTester:
    """Direct NFT contract testing without recipes framework"""
    
    def __init__(self):
        self.node_manager = NodeManager()
        self.api = StacksCoreAPIWrapper(base_url="http://localhost:20443")
        self.cli = BlockstackCLIWrapper()
        self.miner1 = ACCOUNTS["miner1"]
        
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
    
    def deploy_contract(self, miner: str, contract_file: str, contract_name: str) -> str:
        """Deploy contract and return transaction ID"""
        account = ACCOUNTS[miner]
        api = StacksCoreAPIWrapper(base_url=account.api_url)
        
        # Get contract file path
        if not os.path.isabs(contract_file):
            contract_path = os.path.join(os.path.dirname(__file__), '..', contract_file)
        else:
            contract_path = contract_file
        
        if not os.path.exists(contract_path):
            raise FileNotFoundError(f"Contract file not found: {contract_path}")
        
        # Get initial state
        initial_nonce = self.get_nonce(miner)
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        print(f"\n{Colors.format_header('=== CONTRACT DEPLOYMENT ===')}")
        print(f"{Colors.format_info('Contract')}: {Colors.format_dim(contract_name)}")
        print(f"{Colors.format_info('File')}: {Colors.format_dim(contract_path)}")
        print(f"{Colors.format_info('Account')}: {Colors.format_dim(account.address)}")
        print(f"{Colors.format_info('Initial balance')}: {Colors.format_dim(str(initial_balance))}")
        print(f"{Colors.format_info('Using nonce')}: {Colors.format_dim(str(initial_nonce))}")
        
        # Calculate fee based on contract size
        with open(contract_path, 'r') as f:
            contract_code = f.read().strip()
        
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
        
        print(f"{Colors.format_success(f'Contract deployment submitted')}: {Colors.format_info(txid)}")
        
        # Wait for confirmation
        if not self.wait_for_confirmation(miner, initial_nonce, initial_height):
            raise RuntimeError("Contract deployment confirmation timeout")
        
        print(f"{Colors.format_success(f'Contract {contract_name} deployed successfully!')}")
        return txid
    
    def read_contract(self, miner: str, contract_address: str, contract_name: str, function_name: str) -> Dict[str, Any]:
        """Call read-only contract function"""
        account = ACCOUNTS[miner]
        api = StacksCoreAPIWrapper(base_url=account.api_url)
        
        print(f"\n{Colors.format_subheader('--- CONTRACT READ CALL ---')}")
        print(f"{Colors.format_info('Contract')}: {Colors.format_dim(f'{contract_address}.{contract_name}')}")
        print(f"{Colors.format_info('Function')}: {Colors.format_dim(function_name)}")
        
        result = api.call_read_only_function(contract_address, contract_name, function_name, account.address, [])
        
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(result, indent=2))}")
        
        return result
    
    def call_contract(self, miner: str, contract_address: str, contract_name: str, function_name: str, args: list = []) -> str:
        """Call contract function and return transaction ID"""
        account = ACCOUNTS[miner]
        api = StacksCoreAPIWrapper(base_url=account.api_url)
        
        # Get initial state
        initial_nonce = self.get_nonce(miner)
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        print(f"\n{Colors.format_header('=== CONTRACT CALL ===')}")
        print(f"{Colors.format_info('Contract')}: {Colors.format_dim(f'{contract_address}.{contract_name}')}")
        print(f"{Colors.format_info('Function')}: {Colors.format_dim(function_name)}")
        if args:
            print(f"{Colors.format_info('Arguments')}: {Colors.format_dim(str(args))}")
        print(f"{Colors.format_info('Initial balance')}: {Colors.format_dim(str(initial_balance))}")
        print(f"{Colors.format_info('Using nonce')}: {Colors.format_dim(str(initial_nonce))}")
        
        fee = "5000"
        print(f"{Colors.format_info('Using fee')}: {Colors.format_dim(f'{fee} µSTX')}")
        
        # Build and run CLI command
        cmd = self.cli.call_contract(account.private_key, int(fee), initial_nonce, contract_address, contract_name, function_name, args)
        
        print(f"{Colors.format_info('Creating transaction binary...')}")
        tx_binary = self.run_cli_command(cmd, binary_output=True)
        
        print(f"{Colors.format_info('Submitting contract call...')}")
        txid = api.post_raw_transaction(tx_binary)
        
        print(f"{Colors.format_success('Contract call submitted')}: {Colors.format_info(txid)}")
        
        # Wait for confirmation
        if not self.wait_for_confirmation(miner, initial_nonce, initial_height):
            raise RuntimeError("Contract call confirmation timeout")
        
        print(f"{Colors.format_success(f'Contract call {function_name} confirmed!')}")
        return txid

def main():
    """Execute the NFT contract deployment and interaction test"""
    print(f"{Colors.format_dim('=' * 60)}")
    print(f"{Colors.format_header('CYBERPUNK NFT CONTRACT DEPLOYMENT AND INTERACTIONS TEST')}")
    print(f"{Colors.format_dim('=' * 60)}")
    
    tester = NFTTester()
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not tester.node_manager.start_node():
            raise RuntimeError("Failed to start miners")
        
        # Step 1: Deploy cyberpunk NFT contract
        print(f"\n{Colors.format_header('Step 1: Deploy cyberpunk NFT contract')}")
        deploy_txid = tester.deploy_contract("miner1", "contracts/cyberpunk2140a.clar", "cyberpunk2140a")
        
        # Step 2: Read max token count  
        print(f"\n{Colors.format_header('Step 2: Read max token count')}")
        max_tokens = tester.read_contract("miner1", tester.miner1.address, "cyberpunk2140a", "get-last-token-id")
        
        # Step 3: Read mint price
        print(f"\n{Colors.format_header('Step 3: Read mint price')}")
        mint_price = tester.read_contract("miner1", tester.miner1.address, "cyberpunk2140a", "get-mint-price")
        
        # Step 4: Read available count
        print(f"\n{Colors.format_header('Step 4: Read available count')}")
        available_count = tester.read_contract("miner1", tester.miner1.address, "cyberpunk2140a", "get-available-count")
        
        # Step 5: Read initial minted count
        print(f"\n{Colors.format_header('Step 5: Read initial minted count')}")
        initial_minted = tester.read_contract("miner1", tester.miner1.address, "cyberpunk2140a", "get-minted-count")
        
        # Step 6: Read collection attribute
        print(f"\n{Colors.format_header('Step 6: Read collection attribute')}")
        collection_attr = tester.read_contract("miner1", tester.miner1.address, "cyberpunk2140a", "get-collection-attribute")
        
        # Step 7: Check if collection data is frozen
        print(f"\n{Colors.format_header('Step 7: Check collection data frozen')}")
        data_frozen = tester.read_contract("miner1", tester.miner1.address, "cyberpunk2140a", "is-collection-data-frozen")
        
        # Step 8: Set token URI
        print(f"\n{Colors.format_header('Step 8: Set token URI')}")
        set_uri_txid = tester.call_contract("miner1", tester.miner1.address, "cyberpunk2140a", "set-token-uri", ["\"https://cyberpunk2140.com/metadata/{id}.json\""])
        
        # Step 9: Set collection attribute
        print(f"\n{Colors.format_header('Step 9: Set collection attribute')}")
        set_attr_txid = tester.call_contract("miner1", tester.miner1.address, "cyberpunk2140a", "set-collection-attribute", ["u\"Cyberpunk 2140 NFT Collection\""])
        
        # Step 10: Set collection icon data
        print(f"\n{Colors.format_header('Step 10: Set collection icon data')}")
        set_icon_txid = tester.call_contract("miner1", tester.miner1.address, "cyberpunk2140a", "set-collection-icon-data", ["0x89504e470d0a1a0a0000000d49484452"])
        
        # Step 11: Set tokens data
        print(f"\n{Colors.format_header('Step 11: Set tokens data')}")
        set_tokens_txid = tester.call_contract("miner1", tester.miner1.address, "cyberpunk2140a", "set-tokens", ["(list {id: u1, data: 0x89504e470d0a1a0a, attribute: u\"First Token\"} {id: u2, data: 0x89504e470d0a1a0b, attribute: u\"Second Token\"})"])
        
        # Step 12: Mint cyberpunk NFT
        print(f"\n{Colors.format_header('Step 12: Mint cyberpunk NFT')}")
        mint_txid = tester.call_contract("miner1", tester.miner1.address, "cyberpunk2140a", "mint")
        
        # Step 13: Read minted count after mint
        print(f"\n{Colors.format_header('Step 13: Read minted count after mint')}")
        final_minted = tester.read_contract("miner1", tester.miner1.address, "cyberpunk2140a", "get-minted-count")
        
        # Step 14: Read collection attribute after setting
        print(f"\n{Colors.format_header('Step 14: Read collection attribute after setting')}")
        final_collection_attr = tester.read_contract("miner1", tester.miner1.address, "cyberpunk2140a", "get-collection-attribute")
        
        # Final summary
        print(f"\n{Colors.format_dim('=' * 60)}")
        print(f"{Colors.format_header('FINAL RESULT')}")
        print(f"{Colors.format_dim('=' * 60)}")
        
        print(f"{Colors.format_info('Deploy TXID')}: {Colors.format_dim(deploy_txid)}")
        print(f"{Colors.format_info('Set URI TXID')}: {Colors.format_dim(set_uri_txid)}")
        print(f"{Colors.format_info('Set Attribute TXID')}: {Colors.format_dim(set_attr_txid)}")
        print(f"{Colors.format_info('Set Icon TXID')}: {Colors.format_dim(set_icon_txid)}")
        print(f"{Colors.format_info('Set Tokens TXID')}: {Colors.format_dim(set_tokens_txid)}")
        print(f"{Colors.format_info('Mint TXID')}: {Colors.format_dim(mint_txid)}")
        
        return True
        
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