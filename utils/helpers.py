#!/usr/bin/env python3

import subprocess
import time
from typing import Dict, Any, List, Optional
from .config import AccountManager, MinerName, TransactionStatus, TestResult, TxStatus, ApiError, AccountInfo, ApiResult
from .stacks_core_api import StacksCoreAPIWrapper
from .blockstack_cli import BlockstackCLIWrapper
from .logger import Colors, logger

def get_api(miner: MinerName) -> StacksCoreAPIWrapper:
    """Get API for miner (saves 2 lines)"""
    account = AccountManager.get(miner)
    return StacksCoreAPIWrapper(base_url=account.api_url)

def get_cli() -> BlockstackCLIWrapper:
    """Get CLI wrapper"""
    return BlockstackCLIWrapper()

def run_cli_tx(cmd: List[str]) -> bytes:
    """Run CLI command and return transaction binary (saves 4 lines)"""
    result = subprocess.run(cmd, capture_output=True, check=True)
    hex_output = result.stdout.decode().strip()
    return bytes.fromhex(hex_output)

def submit_tx(api: StacksCoreAPIWrapper, cli_cmd: List[str]) -> str:
    """CLI -> binary -> submit (saves 6 lines)"""
    tx_binary = run_cli_tx(cli_cmd)
    return api.post_raw_transaction(tx_binary)

def get_nonce(api: StacksCoreAPIWrapper, account_address: str) -> int:
    """Get current nonce for account (pass API instance for performance)"""
    account_info = get_account_info_typed(api, account_address)
    return account_info.nonce

def get_nonce_for_miner(miner: MinerName) -> int:
    """Convenience wrapper - creates API instance"""
    api = get_api(miner)
    account = AccountManager.get(miner)
    return get_nonce(api, account.address)

def get_balance(api: StacksCoreAPIWrapper, account_address: str) -> int:
    """Get STX balance for account (pass API instance for performance)"""
    account_info = get_account_info_typed(api, account_address)
    return account_info.balance

def get_balance_for_miner(miner: MinerName) -> int:
    """Convenience wrapper - creates API instance"""
    api = get_api(miner)
    account = AccountManager.get(miner)
    return get_balance(api, account.address)

def get_block_height(api: StacksCoreAPIWrapper) -> int:
    """Get current block height (pass API instance for performance)"""
    info_data = api.get_info()
    return info_data["stacks_tip_height"]

def wait_for_confirmation(api: StacksCoreAPIWrapper, account_address: str, initial_nonce: int, initial_height: int, timeout: int = 60) -> bool:
    """Wait for transaction confirmation (nonce + height increase)"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            current_nonce = get_nonce(api, account_address)
            current_height = get_block_height(api)
            
            if current_nonce > initial_nonce and current_height > initial_height:
                return True
                
        except Exception:
            pass
        
        time.sleep(1)
    
    return False

def wait_for_confirmation_miner(miner: MinerName, initial_nonce: int, initial_height: int, timeout: int = 60) -> bool:
    """Convenience wrapper for wait_for_confirmation"""
    api = get_api(miner)
    account = AccountManager.get(miner)
    return wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout)

def submit_transfer(api: StacksCoreAPIWrapper, cli: BlockstackCLIWrapper, private_key: str, nonce: int, to_address: str, amount: int, memo: str = "", fee: int = 180) -> str:
    """Submit STX transfer and return transaction ID (pass instances for performance)"""
    cmd = cli.token_transfer(private_key, fee, nonce, to_address, amount, memo)
    return submit_tx(api, cmd)

def safe_api_call(func, *args, **kwargs) -> ApiResult:
    """Safely call API function and return typed result with full IDE support"""
    try:
        result = func(*args, **kwargs)
        return ApiResult(success=True, data=result)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return ApiResult(success=False, error=ApiError.NOT_FOUND, error_message=error_msg)
        elif "timeout" in error_msg.lower():
            return ApiResult(success=False, error=ApiError.TIMEOUT, error_message=error_msg)
        elif "connection" in error_msg.lower():
            return ApiResult(success=False, error=ApiError.CONNECTION_ERROR, error_message=error_msg)
        else:
            return ApiResult(success=False, error=ApiError.UNKNOWN_ERROR, error_message=error_msg)

def get_account_info_typed(api: StacksCoreAPIWrapper, account_address: str) -> AccountInfo:
    """Get typed account info with full IDE autocompletion support"""
    account_data = api.get_account_info(account_address)
    balance_hex = account_data.get('balance', '0x0')
    balance = int(balance_hex, 16) if balance_hex.startswith('0x') else int(balance_hex)
    
    return AccountInfo(
        address=account_address,
        balance=balance,
        nonce=account_data["nonce"]
    )

def get_tx_status_typed(api: StacksCoreAPIWrapper, txid: str) -> TxStatus:
    """Get typed transaction status with full IDE autocompletion support"""
    try:
        tx_details = api.get_transaction_by_id(txid)
        tx_status_str = tx_details.get('tx_status', 'unknown')
        
        # Convert string to enum with full IDE support
        if tx_status_str == 'success':
            return TxStatus.SUCCESS
        elif tx_status_str == 'abort_by_response':
            return TxStatus.ABORT_BY_RESPONSE
        elif tx_status_str == 'abort_by_post_condition':
            return TxStatus.ABORT_BY_POST_CONDITION
        elif tx_status_str == 'pending':
            return TxStatus.PENDING
        else:
            return TxStatus.UNKNOWN
    except Exception:
        return TxStatus.UNKNOWN