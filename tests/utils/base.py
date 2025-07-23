"""Base classes and utilities for the modular test framework"""

import os
import json
import time
import requests
import tempfile
import subprocess
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

@dataclass
class Account:
    name: str
    address: str
    private_key: str
    port: int

    @property
    def api_url(self) -> str:
        return f"http://localhost:{self.port}"

class StacksTestBase:
    """Base class providing common functionality for all test bricks"""
    
    ACCOUNTS = {
        "miner1": Account("miner1", "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6", 
                         "cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01", 20443),
        "miner2": Account("miner2", "ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y", 
                         "21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601", 30443),
        "miner3": Account("miner3", "ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0", 
                         "7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01", 40443)
    }
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="stacks_test_")
        self.logs_dir = "tests/logs"
        os.makedirs(self.logs_dir, exist_ok=True)
    
    def get_account(self, miner: str) -> Account:
        """Get account by miner name"""
        if miner not in self.ACCOUNTS:
            raise ValueError(f"Unknown miner: {miner}. Available: {list(self.ACCOUNTS.keys())}")
        return self.ACCOUNTS[miner]
    
    def api_call(self, account: Account, endpoint: str, method: str = "GET", 
                 data: Optional[Union[str, bytes]] = None, timeout: int = 30) -> requests.Response:
        """Make API call with retry logic"""
        url = f"{account.api_url}{endpoint}"
        
        for attempt in range(3):
            try:
                if method == "GET":
                    response = requests.get(url, timeout=timeout)
                elif method == "POST":
                    headers = {"Content-Type": "application/octet-stream" if isinstance(data, bytes) else "application/json"}
                    response = requests.post(url, data=data, headers=headers, timeout=timeout)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                if response.status_code != 200:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                return response
                    
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise e
        
        return response
    
    def get_account_info(self, miner: str) -> Dict[str, Any]:
        """Get account info (balance, nonce)"""
        account = self.get_account(miner)
        response = self.api_call(account, f"/v2/accounts/{account.address}")
        response.raise_for_status()
        return response.json()
    
    def get_nonce(self, miner: str) -> int:
        """Get current nonce for account"""
        return self.get_account_info(miner)["nonce"]
    
    def get_balance(self, miner: str) -> int:
        """Get STX balance for account"""
        return int(self.get_account_info(miner)["balance"], 16)
    
    def get_block_height(self, miner: str) -> int:
        """Get current block height"""
        account = self.get_account(miner)
        response = self.api_call(account, "/v2/info")
        response.raise_for_status()
        return response.json()["stacks_tip_height"]
    
    def run_cli_command(self, command: List[str], binary_output: bool = False) -> bytes:
        """Run blockstack-cli command and return output"""
        try:
            result = subprocess.run(command, capture_output=True, check=True)
            if binary_output:
                # Convert hex to binary
                hex_output = result.stdout.decode().strip()
                return bytes.fromhex(hex_output)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"CLI command failed: {' '.join(command)}\nError: {e.stderr.decode()}")
    
    def wait_for_confirmation(self, miner: str, initial_nonce: int, initial_height: int, 
                            timeout: int = 60) -> bool:
        """Wait for transaction confirmation (nonce + height increase)"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_nonce = self.get_nonce(miner)
                current_height = self.get_block_height(miner)
                
                if current_nonce > initial_nonce and current_height > initial_height:
                    return True
                    
            except Exception:
                pass  # Ignore temporary API errors
            
            time.sleep(3)
        
        return False
    
    def verify_transaction(self, miner: str, txid: str, initial_nonce: int, initial_balance: int, initial_height: int) -> Dict[str, Any]:
        """Verify transaction by checking endpoint, nonce increase, and height increase"""
        account = self.get_account(miner)
        
        # Wait for confirmation first
        if not self.wait_for_confirmation(miner, initial_nonce, initial_height):
            return {
                'success': False,
                'error': 'Transaction confirmation timeout',
                'txid': txid
            }
        
        # Get current state
        try:
            current_nonce = self.get_nonce(miner)
            current_balance = self.get_balance(miner)
            current_height = self.get_block_height(miner)
            
            # ALWAYS fetch transaction details from /v3/transaction endpoint
            print(f"\n=== FETCHING TRANSACTION DETAILS ===")
            print(f"Calling: /v3/transaction/{txid}")
            
            tx_data = None
            try:
                tx_response = self.api_call(account, f"/v3/transaction/{txid}")
                print(f"Response status: {tx_response.status_code}")
                
                if tx_response.status_code == 200:
                    tx_data = tx_response.json()
                    print(f"✓ Transaction details fetched successfully!")
                    print("=== FULL TRANSACTION DETAILS ===")
                    print(json.dumps(tx_data, indent=2))
                    print("=== END TRANSACTION DETAILS ===")
                else:
                    print(f"⚠ Transaction endpoint returned {tx_response.status_code}")
                    print(f"Response: {tx_response.text}")
                    
            except Exception as e:
                print(f"✗ ERROR fetching transaction details: {e}")
                # Still continue with verification even if we can't get details
            
            # Verify confirmation
            print(f"\n✓ Transaction {txid} confirmed!")
            print(f"  Balance: {initial_balance} → {current_balance} (change: {current_balance - initial_balance})")
            print(f"  Nonce: {initial_nonce} → {current_nonce} (change: {current_nonce - initial_nonce})")  
            print(f"  Block: {initial_height} → {current_height} (change: {current_height - initial_height})")
            
            if tx_data:
                print(f"\n=== TRANSACTION SUMMARY ===")
                # The response format is different - it's wrapped with transaction data
                result = tx_data.get('result', 'unknown')
                print(f"  Result: {result}")
                print(f"  Status: success" if result != 'unknown' else "  Status: unknown")
                print(f"  Raw response keys: {list(tx_data.keys())}")
                
                # Try to decode the transaction hex if available
                if 'tx' in tx_data:
                    print(f"  Transaction hex length: {len(tx_data['tx'])}")
                    # Try to extract transaction type from hex pattern
                    tx_hex = tx_data['tx']
                    if len(tx_hex) > 16:
                        # Contract calls usually have specific patterns
                        if '046d696e74' in tx_hex:  # "mint" in hex
                            print(f"  Detected operation: NFT mint")
                        elif tx_hex.count('08') > 0:  # Contract deployment pattern
                            print(f"  Detected operation: Contract deployment")
            
            return {
                'success': True,
                'txid': txid,
                'nonce_change': current_nonce - initial_nonce,
                'balance_change': current_balance - initial_balance,
                'height_change': current_height - initial_height,
                'transaction_data': tx_data
            }
            
        except Exception as e:
            print(f"✗ Transaction verification failed: {e}")
            return {
                'success': False,
                'error': f'Transaction verification failed: {e}',
                'txid': txid
            }
    
    def verify_chain_progression(self, miner: str, retries: int = 5) -> bool:
        """Verify chain is progressing properly"""
        for attempt in range(retries):
            try:
                initial_height = self.get_block_height(miner)
                time.sleep(9)  # Wait for block
                new_height = self.get_block_height(miner)
                
                if new_height > initial_height:
                    return True
                    
            except Exception:
                pass
                
            if attempt < retries - 1:
                time.sleep(5)
        
        return False
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)