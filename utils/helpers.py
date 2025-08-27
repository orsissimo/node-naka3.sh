#!/usr/bin/env python3

import subprocess
import time
from typing import Dict, Any, List, Optional
from .config import AccountManager, Miner, TransactionStatus, TestResult, TxStatus, ApiError, AccountInfo, ApiResult
from .stacks_core_api import StacksCoreAPI, StacksCoreAPIWrapper
from .blockstack_cli import BlockstackCLIWrapper
from .logger import Colors, logger

def prepare_cli_binary(cmd: List[str]) -> bytes:
    """Prepare CLI command and return transaction binary"""
    result = subprocess.run(cmd, capture_output=True, check=True)
    hex_output = result.stdout.decode().strip()
    return bytes.fromhex(hex_output)

def submit_cli_command(api: StacksCoreAPI, cli_cmd: List[str]) -> str:
    """Execute CLI command and submit to blockchain"""
    tx_binary = prepare_cli_binary(cli_cmd)
    return api.post_raw_transaction(tx_binary)

def wait_for_confirmation(api: StacksCoreAPI, account_address: str, initial_nonce: int, initial_height: int, timeout: int = 60) -> bool:
    """Wait for transaction confirmation using smart block-based polling"""
    start_time = time.time()
    last_checked_height = initial_height
    
    while time.time() - start_time < timeout:
        try:
            current_height = api.get_info().stacks_tip_height
            
            # Only check nonce when block height increases (more efficient)
            if current_height > last_checked_height:
                account_info = api.get_account_info(account_address)
                current_nonce = account_info.nonce
                
                if current_nonce > initial_nonce and current_height > initial_height:
                    return True
                    
                last_checked_height = current_height
                # Short sleep after block change
                time.sleep(1)
            else:
                # Longer sleep when no new blocks (more efficient)
                time.sleep(3)
                
        except Exception:
            time.sleep(2)
    
    return False

