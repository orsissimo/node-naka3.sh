#!/usr/bin/env python3

import os
import sys
import time
import subprocess
from typing import Dict, Any, Optional, List
from abc import ABC

from .config import MinerName, AccountManager, Account
from .stacks_core_api import StacksCoreAPIWrapper
from .blockstack_cli import BlockstackCLIWrapper
from .node_manager import NodeManager
from .logger import Colors, logger


class BaseTestClass(ABC):
    """Base class for all test classes providing common operations and utilities."""
    
    def __init__(self):
        self.node_manager = NodeManager()
        self.cli = BlockstackCLIWrapper()
        
        # Pre-load all account references for convenience
        self.miner1 = AccountManager.get(MinerName.MINER1)
        self.miner2 = AccountManager.get(MinerName.MINER2)
        self.miner3 = AccountManager.get(MinerName.MINER3)
        
        # Cache API wrappers for performance
        self._api_cache = {}
        
    def wait_for_miners_ready(self, timeout: int = 60) -> bool:
        """Wait for all miner APIs to become responsive with proper error handling."""
        logger.info("Verifying all miner endpoints are ready...")
        start_time = time.time()
        all_miners = [MinerName.MINER1, MinerName.MINER2, MinerName.MINER3]
        
        while time.time() - start_time < timeout:
            ready_miners = []
            for miner in all_miners:
                try:
                    api = self.get_api(miner)
                    info = api.get_info()
                    if info and 'stacks_tip_height' in info:
                        ready_miners.append(miner)
                except Exception as e:
                    # Continue trying - connection errors are expected initially
                    pass
            
            if len(ready_miners) == len(all_miners):
                logger.info(Colors.format_stacks(f"All {len(all_miners)} miners are ready."))
                return True
            
            logger.debug(f"Miners ready: {len(ready_miners)}/{len(all_miners)}. Waiting...")
            time.sleep(3)  # Wait a bit longer between checks
            
        logger.error(Colors.format_fail(f"Timeout: Only {len(ready_miners)}/{len(all_miners)} miners became ready."))
        return False
        
    def get_api(self, miner: MinerName) -> StacksCoreAPIWrapper:
        """Get cached API wrapper for a miner."""
        if miner not in self._api_cache:
            account = AccountManager.get(miner)
            self._api_cache[miner] = StacksCoreAPIWrapper(base_url=account.api_url)
        return self._api_cache[miner]
    
    def get_account_info(self, miner: MinerName) -> Dict[str, Any]:
        """Get account info (balance, nonce)."""
        account = AccountManager.get(miner)
        api = self.get_api(miner)
        return api.get_account_info(account.address)
    
    def get_nonce(self, miner: MinerName) -> int:
        """Get current nonce for account."""
        return self.get_account_info(miner)["nonce"]
    
    def get_balance(self, miner: MinerName) -> int:
        """Get STX balance for account."""
        account_info = self.get_account_info(miner)
        balance_hex = account_info.get('balance', '0x0')
        return int(balance_hex, 16) if balance_hex.startswith('0x') else int(balance_hex)
    
    def get_block_height(self, miner: MinerName) -> int:
        """Get current block height."""
        api = self.get_api(miner)
        info_data = api.get_info()
        return info_data["stacks_tip_height"]
    
    def wait_for_confirmation(self, miner: MinerName, initial_nonce: int, initial_height: int, timeout: int = 60) -> bool:
        """Wait for transaction confirmation (nonce + height increase)."""
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
    
    def run_cli_command(self, command: list, binary_output: bool = False) -> bytes:
        """Run blockstack-cli command and return output."""
        try:
            result = subprocess.run(command, capture_output=True, check=True)
            if binary_output:
                hex_output = result.stdout.decode().strip()
                return bytes.fromhex(hex_output)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"CLI command failed: {' '.join(command)}\\nError: {e.stderr.decode()}")
    
    def submit_transaction(self, miner: MinerName, cli_command: list) -> str:
        """Submit a transaction using CLI and API. Returns transaction ID."""
        api = self.get_api(miner)
        
        # Create transaction binary
        tx_binary = self.run_cli_command(cli_command, binary_output=True)
        
        # Submit transaction
        txid = api.post_raw_transaction(tx_binary)
        return txid
    
    def transfer_stx(self, from_miner: MinerName, to_address: str, amount: int, memo: str = "", fee: int = 180) -> str:
        """Transfer STX tokens. Returns transaction ID."""
        account = AccountManager.get(from_miner)
        nonce = self.get_nonce(from_miner)
        
        # Build CLI command
        cmd = self.cli.token_transfer(account.private_key, fee, nonce, to_address, amount, memo)
        
        # Submit transaction
        return self.submit_transaction(from_miner, cmd)
    
    def deploy_contract(self, miner: MinerName, contract_file: str, contract_name: str, fee: Optional[int] = None) -> str:
        """Deploy a contract. Returns transaction ID."""
        account = AccountManager.get(miner)
        nonce = self.get_nonce(miner)
        
        # Get contract file path
        if not os.path.isabs(contract_file):
            contract_path = os.path.join(os.path.dirname(__file__), '..', contract_file)
        else:
            contract_path = contract_file
        
        if not os.path.exists(contract_path):
            raise FileNotFoundError(f"Contract file not found: {contract_path}")
        
        # Calculate fee if not provided
        if fee is None:
            with open(contract_path, 'r') as f:
                contract_code = f.read().strip()
            contract_size = len(contract_code)
            base_fee = max(contract_size, 10000)
            fee = int(base_fee * 1.1)
        
        # Build CLI command
        cmd = self.cli.publish_contract(account.private_key, fee, nonce, contract_name, contract_path)
        
        # Submit transaction
        return self.submit_transaction(miner, cmd)
    
    def call_contract(self, miner: MinerName, contract_address: str, contract_name: str, 
                     function_name: str, args: List[str] = None, fee: int = 10000) -> str:
        """Call a contract function. Returns transaction ID."""
        account = AccountManager.get(miner)
        nonce = self.get_nonce(miner)
        
        if args is None:
            args = []
        
        # Build CLI command
        cmd = self.cli.call_contract(account.private_key, fee, nonce, 
                                   contract_address, contract_name, function_name, args)
        
        # Submit transaction
        return self.submit_transaction(miner, cmd)
    
    def read_contract(self, miner: MinerName, contract_address: str, contract_name: str, 
                     function_name: str, args: List[str] = None) -> Dict[str, Any]:
        """Read from a contract function (read-only call)."""
        api = self.get_api(miner)
        account = AccountManager.get(miner)
        
        if args is None:
            args = []
        
        # Call using the same pattern as the original working code
        return api.call_read_only_function(contract_address, contract_name, function_name, account.address, args)
    
    def get_transaction_status(self, miner: MinerName, txid: str) -> Dict[str, Any]:
        """Get transaction status and details."""
        api = self.get_api(miner)
        return api.get_transaction_by_id(txid)
    
    def wait_for_transaction_success(self, miner: MinerName, txid: str, timeout: int = 120) -> bool:
        """Wait for a specific transaction to succeed."""
        start_time = time.time()
        
        # Give the network some time to process the transaction before checking
        time.sleep(5)
        
        while time.time() - start_time < timeout:
            try:
                tx_info = self.get_transaction_status(miner, txid)
                tx_status = tx_info.get('tx_status', 'unknown')
                
                if tx_status == 'success':
                    logger.debug(f"Transaction {txid} succeeded")
                    return True
                elif tx_status in ['abort_by_response', 'abort_by_post_condition']:
                    logger.warning(f"Transaction {txid} failed with status: {tx_status}")
                    return False
                else:
                    logger.debug(f"Transaction {txid} status: {tx_status}, continuing to wait...")
                    
            except Exception as e:
                # Transaction might not be found yet or network issues
                if "404" in str(e):
                    logger.debug(f"Transaction {txid} not found yet, continuing to wait...")
                else:
                    logger.debug(f"Error checking transaction {txid}: {str(e)}")
            
            time.sleep(5)  # Check less frequently to reduce log spam
        
        logger.warning(f"Timeout waiting for transaction {txid} to complete")
        return False
    
    def start_node(self, mode: str = "auto") -> bool:
        """Start the node in specified mode and wait for readiness."""
        logger.info(Colors.format_stacks(f"Starting node in {mode} mode..."))
        if not self.node_manager.start_node(mode):
            return False
        
        # Wait for miners to be ready using our improved method
        return self.wait_for_miners_ready()
    
    def stop_node(self):
        """Stop the node."""
        logger.info(Colors.format_stacks("Stopping node..."))
        self.node_manager.stop_node()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info(Colors.format_grey("Cleaning up..."))
        self.node_manager.cleanup()
    
    def print_test_header(self, test_name: str):
        """Print a formatted test header."""
        separator = "=" * 80
        print(f"{Colors.format_dim(separator)}")
        print(f"{Colors.format_header(test_name.upper())}")
        print(f"{Colors.format_dim(separator)}")
    
    def print_test_section(self, section_name: str):
        """Print a formatted test section header."""
        print(f"\\n{Colors.format_header(section_name)}")
    
    def print_test_info(self, label: str, value: str):
        """Print formatted test information."""
        print(f"{Colors.format_info(label)}: {Colors.format_dim(value)}")
    
    def print_test_success(self, message: str):
        """Print a success message."""
        print(f"{Colors.format_success('✓')} {message}")
    
    def print_test_error(self, message: str):
        """Print an error message."""
        print(f"{Colors.format_error('✗')} {message}")
    
    def print_test_warning(self, message: str):
        """Print a warning message."""
        print(f"{Colors.format_warn('⚠')} {message}")