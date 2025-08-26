#!/usr/bin/env python3

import subprocess
import time
from typing import Dict, Any, List, Optional
from .config import AccountManager, Miner, TransactionStatus, TestResult, TxStatus, ApiError, AccountInfo, ApiResult
from .stacks_core_api import StacksCoreAPIWrapper
from .blockstack_cli import BlockstackCLIWrapper
from .logger import Colors, logger

def prepare_cli_binary(cmd: List[str]) -> bytes:
    """Prepare CLI command and return transaction binary"""
    result = subprocess.run(cmd, capture_output=True, check=True)
    hex_output = result.stdout.decode().strip()
    return bytes.fromhex(hex_output)

def submit_cli_command(api: StacksCoreAPIWrapper, cli_cmd: List[str]) -> str:
    """Execute CLI command and submit to blockchain"""
    tx_binary = prepare_cli_binary(cli_cmd)
    return api.post_raw_transaction(tx_binary)

def wait_for_confirmation(api: StacksCoreAPIWrapper, account_address: str, initial_nonce: int, initial_height: int, timeout: int = 60) -> bool:
    """Wait for transaction confirmation using smart block-based polling"""
    start_time = time.time()
    last_checked_height = initial_height
    
    while time.time() - start_time < timeout:
        try:
            current_height = get_block_height(api)
            
            # Only check nonce when block height increases (more efficient)
            if current_height > last_checked_height:
                account_info = get_account_info_typed(api, account_address)
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



def get_account_info_typed(api: StacksCoreAPIWrapper, account_address: str) -> AccountInfo:
    """Get typed account info with autocompletion"""
    account_data = api.get_account_info(account_address)
    balance_hex = account_data.get('balance', '0x0')
    balance = int(balance_hex, 16) if balance_hex.startswith('0x') else int(balance_hex)
    
    return AccountInfo(
        address=account_address,
        balance=balance,
        nonce=account_data["nonce"]
    )

def get_tx_status_typed(api: StacksCoreAPIWrapper, txid: str) -> TxStatus:
    """Get typed transaction status"""
    try:
        tx_details = api.get_transaction_by_id(txid)
        tx_status_str = tx_details.get('tx_status', 'unknown')
        
        # Convert string to enum
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

def get_block_height(api: StacksCoreAPIWrapper) -> int:
    """Get current block height with clear function name"""
    info_data = api.get_info()
    return info_data["stacks_tip_height"]

def safe_api_call(func, *args, **kwargs) -> ApiResult:
    """Safely call API function and return typed result"""
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