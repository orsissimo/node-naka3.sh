"""Base classes and utilities for the modular test framework"""

import os
import json
import time
import requests
import tempfile
import subprocess
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

class Colors:
    """ANSI color codes for consistent terminal output"""
    # Main colors
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    
    # Reset
    RESET = '\033[0m'
    
    @staticmethod
    def format_header(text: str) -> str:
        """Format main section headers"""
        return f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}"
    
    @staticmethod
    def format_subheader(text: str) -> str:
        """Format subsection headers"""
        return f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}"
    
    @staticmethod
    def format_success(text: str) -> str:
        """Format success messages"""
        return f"{Colors.GREEN}{text}{Colors.RESET}"
    
    @staticmethod
    def format_warning(text: str) -> str:
        """Format warning messages"""
        return f"{Colors.YELLOW}{text}{Colors.RESET}"
    
    @staticmethod
    def format_error(text: str) -> str:
        """Format error messages"""
        return f"{Colors.RED}{text}{Colors.RESET}"
    
    @staticmethod
    def format_info(text: str) -> str:
        """Format info messages"""
        return f"{Colors.WHITE}{text}{Colors.RESET}"
    
    @staticmethod
    def format_dim(text: str) -> str:
        """Format secondary/dim text"""
        return f"{Colors.DIM}{text}{Colors.RESET}"

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
        self.logs_dir = "logs"
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
                
                # We no longer check status code here; the handler will do it.
                # Just return the response object directly.
                return response
                    
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise e
        
        # This part is now less likely to be reached, but is a safe fallback.
        return response

    def handle_api_response(self, response: requests.Response) -> Any:
        """
        Centralized handler for all API responses.

        This function checks the response status. On success (200), it intelligently
        parses and returns the body content (JSON or text). On failure, it
        parses the detailed JSON error from the API and raises a descriptive
        RuntimeError.

        Args:
            response: The requests.Response object from an API call.

        Raises:
            RuntimeError: If the response status code is not 200.

        Returns:
            The parsed JSON content as a dictionary or the plain text response.
        """
        if response.status_code != 200:
            try:
                # Attempt to parse the detailed error JSON from the Stacks API
                error_details = response.json()
                reason = error_details.get('reason', 'Unknown API error')
                reason_data = error_details.get('reason_data', {})
                error_message = f"API Error ({response.status_code}): {reason} - Details: {reason_data}"
            except json.JSONDecodeError:
                # Fallback for non-JSON errors (e.g., server proxy errors)
                error_message = f"API Error ({response.status_code}): {response.text}"
            
            # Log the detailed error before raising
            print(f"{Colors.format_error('✗ API call failed')}: {Colors.format_error(error_message)}")
            raise RuntimeError(error_message)

        # Handle successful responses
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return response.json()
        else:
            # This handles plain text responses, like txids, and strips the surrounding quotes
            return response.text.strip('"')

    def get_account_info(self, miner: str) -> Dict[str, Any]:
        """Get account info (balance, nonce)"""
        account = self.get_account(miner)
        response = self.api_call(account, f"/v2/accounts/{account.address}")
        return self.handle_api_response(response)
    
    def get_nonce(self, miner: str) -> int:
        """Get current nonce for account"""
        return self.get_account_info(miner)["nonce"]
    
    def get_balance(self, miner: str, address: Optional[str] = None) -> int:
        """Get STX balance for account or any address"""
        target_address = address or self.get_account(miner).address
        account_to_query_from = self.get_account(miner)
        
        response = self.api_call(account_to_query_from, f"/v2/accounts/{target_address}")
        account_info = self.handle_api_response(response)
        
        balance_hex = account_info.get('balance', '0x0')
        return int(balance_hex, 16) if balance_hex.startswith('0x') else int(balance_hex)
    
    def get_block_height(self, miner: str) -> int:
        """Get current block height"""
        account = self.get_account(miner)
        response = self.api_call(account, "/v2/info")
        info_data = self.handle_api_response(response)
        return info_data["stacks_tip_height"]
    
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
            
            time.sleep(1)
        
        return False
    
    def wait_for_block_increase(self, miner: str, initial_height: int, timeout: int = 30) -> int:
        """Wait for block height to increase beyond initial_height"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_height = self.get_block_height(miner)
                if current_height > initial_height:
                    return current_height
            except Exception:
                pass  # Ignore temporary API errors
            
            # Brief pause to avoid hammering the API (necessary for polling)
            time.sleep(1)
        
        return initial_height  # Return original height if no increase detected
    
    def wait_for_miners_ready(self) -> bool:
        """Wait for all miners to be ready by checking /v2/info endpoint"""
        miners_to_check = ["miner1", "miner2", "miner3"]
        ready_count = 0
        max_attempts = 10
        
        for attempt in range(max_attempts):
            ready_count = 0
            for miner in miners_to_check:
                try:
                    account = self.get_account(miner)
                    response = self.api_call(account, "/v2/info", timeout=5)
                    if response.status_code == 200:
                        info = response.json()
                        # Check if miner is responding and has a valid height
                        if info.get("stacks_tip_height", 0) >= 0:
                            ready_count += 1
                except Exception:
                    pass  # Ignore errors, will retry
            
            if ready_count == len(miners_to_check):
                print(f"{Colors.format_success(f'✓ All {ready_count} miners are ready')}")
                return True
            
            print(f"{Colors.format_dim(f'Miners ready: {ready_count}/{len(miners_to_check)}, retrying in 1s...')}")
            time.sleep(1)  # Brief pause before retry (necessary for initialization check)
        
        print(f"{Colors.format_warning(f'⚠ Only {ready_count}/{len(miners_to_check)} miners ready after {max_attempts} attempts')}")
        return ready_count > 0  # Return True if at least one miner is ready
    
    def wait_for_nonce_increase(self, miner: str, initial_nonce: int, expected_increase: int, timeout: int = 30) -> int:
        """Wait for nonce to increase by expected_increase amount"""
        target_nonce = initial_nonce + expected_increase
        start_time = time.time()
        last_error = ""
        
        while time.time() - start_time < timeout:
            try:
                current_nonce = self.get_nonce(miner)
                if current_nonce >= target_nonce:
                    return current_nonce
                # Reset error on successful API call
                last_error = ""
            except Exception as e:
                # Store the last error but continue trying
                last_error = str(e)
                pass
            
            time.sleep(1)
        
        # If timeout is reached, check the final nonce one last time.
        # If it still fails, raise an error with the last known issue.
        try:
            return self.get_nonce(miner)
        except Exception as final_e:
            raise RuntimeError(f"Failed to get final nonce after timeout. Last known error: {last_error or str(final_e)}")
    
    def verify_transaction_no_wait(self, miner: str, txid: str, recipient_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifies a transaction by fetching its details directly without waiting.
        This is a non-blocking status check designed for forensic analysis.

        It returns a dictionary with a 'success' flag and detailed information.

        Args:
            miner: The name of the miner node to query.
            txid: The ID of the transaction to verify.
            recipient_address: (Optional) Not used in this function but kept for signature consistency.

        Returns:
            A dictionary containing the verification result.
            - On success: {'success': True, 'txid': ..., 'transaction_data': ...}
            - On failure: {'success': False, 'txid': ..., 'error': ...}
        """
        account = self.get_account(miner)
        
        try:
            # Print headers for clear logging during test runs
            print(f"\n{Colors.format_subheader('=== FETCHING TRANSACTION DETAILS ===')}")
            print(f"Calling: {Colors.format_dim(f'/v3/transaction/{txid}')}")
            
            # Make the API call
            response = self.api_call(account, f"/v3/transaction/{txid}")
            
            # Special handling for 404: this is a specific, meaningful state where the
            # transaction was not found. It's not a server error.
            if response.status_code == 404:
                error_msg = f"Transaction not found (404)."
                print(f"{Colors.format_warning(f'⚠ {error_msg}')}")
                return {
                    'success': False,
                    'error': error_msg,
                    'txid': txid,
                    'transaction_data': {'tx_status': 'not_found'}
                }

            # For all other statuses (200 OK or other errors like 500),
            # use the centralized handler. It will return JSON on success
            # or raise a detailed exception on failure.
            tx_data = self.handle_api_response(response)
            
            # Log the successful fetch and the full data for debugging
            print(f"{Colors.format_success('✓ Transaction details fetched successfully!')}")
            print(f"{Colors.format_subheader('--- FULL TRANSACTION DETAILS ---')}")
            print(f"{Colors.format_dim(json.dumps(tx_data, indent=2))}")
            print(f"{Colors.format_subheader('--- END TRANSACTION DETAILS ---')}")
            
            # Return the structured success response
            return {
                'success': True,
                'txid': txid,
                'transaction_data': tx_data
            }
                
        except Exception as e:
            # This block catches any other failure, such as a connection error
            # or an exception raised by handle_api_response.
            error_str = str(e)
            print(f"{Colors.format_error('✗ ERROR fetching transaction details')}: {Colors.format_error(error_str)}")
            return {
                'success': False,
                'error': f'Failed to verify transaction: {error_str}',
                'txid': txid
            }
    
    def verify_transaction(self, miner: str, txid: str, initial_nonce: int, initial_balance: int, initial_height: int, recipient_address: Optional[str] = None) -> Dict[str, Any]:
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
            
            # Get recipient balance if tracking transfers
            current_recipient_balance = None
            if recipient_address:
                try:
                    response = self.api_call(account, f"/v2/accounts/{recipient_address}")
                    response.raise_for_status()
                    account_info = response.json()
                    balance_hex = account_info.get('balance', '0x0')
                    current_recipient_balance = int(balance_hex, 16) if balance_hex.startswith('0x') else int(balance_hex)
                except Exception as e:
                    print(f"{Colors.format_warning(f'⚠ Could not get recipient balance')}: {Colors.format_error(str(e))}")
                    current_recipient_balance = None
            
            # ALWAYS fetch transaction details from /v3/transaction endpoint
            print(f"\n{Colors.format_subheader('=== FETCHING TRANSACTION DETAILS ===')}")
            print(f"Calling: {Colors.format_dim(f'/v3/transaction/{txid}')}")
            
            tx_data = None
            try:
                tx_response = self.api_call(account, f"/v3/transaction/{txid}")
                print(f"Response status: {Colors.format_info(str(tx_response.status_code))}")
                
                if tx_response.status_code == 200:
                    tx_data = tx_response.json()
                    print(f"{Colors.format_success('✓ Transaction details fetched successfully!')}")
                    print(f"{Colors.format_subheader('=== FULL TRANSACTION DETAILS ===')}")
                    print(f"{Colors.format_dim(json.dumps(tx_data, indent=2))}")
                    print(f"{Colors.format_subheader('=== END TRANSACTION DETAILS ===')}")
                else:
                    print(f"{Colors.format_warning(f'⚠ Transaction endpoint returned {tx_response.status_code}')}")
                    print(f"Response: {Colors.format_error(tx_response.text)}")
                    
            except Exception as e:
                print(f"{Colors.format_error(f'✗ ERROR fetching transaction details')}: {Colors.format_error(str(e))}")
                # Still continue with verification even if we can't get details
            
            # Verify confirmation
            print(f"\n{Colors.format_success(f'✓ Transaction {txid} confirmed!')}")
            print(f"  Balance: {Colors.format_dim(f'{initial_balance} → {current_balance}')} (change: {Colors.format_info(str(current_balance - initial_balance))})")
            print(f"  Nonce: {Colors.format_dim(f'{initial_nonce} → {current_nonce}')} (change: {Colors.format_info(str(current_nonce - initial_nonce))})")  
            print(f"  Block: {Colors.format_dim(f'{initial_height} → {current_height}')} (change: {Colors.format_info(str(current_height - initial_height))})")
            
            if tx_data:
                print(f"\n{Colors.format_subheader('=== TRANSACTION SUMMARY ===')}")
                # The response format is different - it's wrapped with transaction data
                result = tx_data.get('result', 'unknown')
                print(f"  Result: {Colors.format_info(result)}")
                print(f"  Status: {Colors.format_success('success')}" if result != 'unknown' else f"  Status: {Colors.format_warning('unknown')}")
                print(f"  Raw response keys: {Colors.format_dim(str(list(tx_data.keys())))}")
                
                # Try to decode the transaction hex if available
                if 'tx' in tx_data:
                    print(f"  Transaction hex length: {Colors.format_dim(str(len(tx_data['tx'])))}")
                    # Try to extract transaction type from hex pattern
                    tx_hex = tx_data['tx']
                    if len(tx_hex) > 16:
                        # Check the 'tx_type' field from the API response for accurate identification
                        tx_type = tx_data.get('transaction', {}).get('tx_type', 'unknown')
                        if tx_type == 'token_transfer':
                            print(f"  Detected operation: {Colors.format_success('Token Transfer')}")
                        elif tx_type == 'contract_call':
                            function_name = tx_data.get('transaction', {}).get('contract_call', {}).get('function_name', 'unknown')
                            print(f"  Detected operation: {Colors.format_success(f'Contract Call: {function_name}')}")
                        elif tx_type == 'smart_contract':
                            print(f"  Detected operation: {Colors.format_success('Contract Deployment')}")
                        else:
                            print(f"  Detected operation: {Colors.format_info(tx_type)}")
            
            result = {
                'success': True,
                'txid': txid,
                'nonce_change': current_nonce - initial_nonce,
                'balance_change': current_balance - initial_balance,
                'height_change': current_height - initial_height,
                'transaction_data': tx_data
            }
            
            # Add recipient balance change if tracking transfers
            if recipient_address and current_recipient_balance is not None:
                # We need initial recipient balance - get it from the method signature
                # For now, just add the current recipient balance
                result['recipient_balance'] = current_recipient_balance
                result['recipient_address'] = recipient_address
            
            return result
            
        except Exception as e:
            print(f"{Colors.format_error(f'✗ Transaction verification failed')}: {Colors.format_error(str(e))}")
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