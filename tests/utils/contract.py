import os
import json
import time
from typing import Optional, Dict, Any, List
from .base import StacksTestBase, Colors

class Contract(StacksTestBase):
    
    def deploy(self, miner: str, contract_file: str, contract_name: str, nonce: Optional[int] = None) -> str:
        # Handle relative paths from tests directory
        if not os.path.isabs(contract_file):
            # Try from current directory first
            if not os.path.exists(contract_file):
                # Try from tests directory
                test_path = os.path.join(os.path.dirname(__file__), '..', contract_file)
                if os.path.exists(test_path):
                    contract_file = test_path
                else:
                    raise FileNotFoundError(f"Contract file not found: {contract_file}")
        elif not os.path.exists(contract_file):
            raise FileNotFoundError(f"Contract file not found: {contract_file}")
        
        account = self.get_account(miner)
        
        # Validate contract file content
        try:
            with open(contract_file, 'r') as f:
                contract_code = f.read().strip()
            if not contract_code:
                raise ValueError("Contract file is empty")
            print(f"{Colors.format_success(f'✓ Contract file loaded ({len(contract_code)} characters)')}")
        except Exception as e:
            print(f"{Colors.format_error(f'✗ Error reading contract file')}: {Colors.format_error(str(e))}")
            raise
        
        # Get initial state for verification
        initial_nonce = self.get_nonce(miner) if nonce is None else nonce
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        print(f"\n{Colors.format_header('=== CONTRACT DEPLOYMENT ===')}")
        print(f"Contract: {Colors.format_info(contract_name)}")
        print(f"File: {Colors.format_dim(contract_file)}")
        print(f"Initial balance: {Colors.format_dim(str(initial_balance))}")
        print(f"Using nonce: {Colors.format_dim(str(initial_nonce))}")
        print(f"Account: {Colors.format_info(account.address)}")
        
        # Calculate dynamic fee based on contract size
        # Stacks requires approximately 1 µSTX per byte for contract deployment
        contract_size = len(contract_code)
        base_fee = max(contract_size, 10000)  # At least 1 µSTX per byte, minimum 10k
        
        # Add buffer for safety (10% extra)
        fee = str(int(base_fee * 1.1))
            
        print(f"Using fee: {Colors.format_success(f'{fee} µSTX')}")
        
        cmd = ["blockstack-cli", "--testnet", "publish", account.private_key, fee, str(initial_nonce), contract_name, contract_file]
        
        print(f"{Colors.format_dim('Creating contract deployment transaction...')}")
        print(f"Command: {Colors.format_dim(' '.join(cmd))}")
        
        try:
            tx_binary = self.run_cli_command(cmd, binary_output=True)
            print(f"{Colors.format_success(f'✓ Transaction binary created (length: {len(tx_binary)} bytes)')}")
        except Exception as e:
            print(f"{Colors.format_error('✗ Failed to create transaction binary')}: {Colors.format_error(str(e))}")
            raise
        
        print(f"{Colors.format_dim(f'Submitting transaction to {account.api_url}/v2/transactions...')}")
        
        try:
            response = self.api_call(account, "/v2/transactions", "POST", tx_binary)
            print(f"Response status: {Colors.format_info(str(response.status_code))}")
            
            if response.status_code != 200:
                print(f"{Colors.format_error('✗ Transaction submission failed')}")
                print(f"Response headers: {Colors.format_dim(str(dict(response.headers)))}")
                try:
                    error_data = response.json()
                    print(f"Error details: {Colors.format_error(json.dumps(error_data, indent=2))}")
                except:
                    print(f"Error text: {Colors.format_error(response.text)}")
                
            response.raise_for_status()
        except Exception as e:
            print(f"{Colors.format_error('✗ API call failed')}: {Colors.format_error(str(e))}")
            raise
        
        txid = response.text.strip('"')
        print(f"{Colors.format_success(f'✓ Contract deployment submitted')}: {Colors.format_info(txid)}")
        
        # Verify the transaction
        verification = self.verify_transaction(miner, txid, initial_nonce, initial_balance, initial_height)
        if not verification['success']:
            raise RuntimeError(f"Contract deployment verification failed: {verification['error']}")
        
        return txid
    
    def read(self, miner: str, contract_address: str, contract_name: str, function_name: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        account = self.get_account(miner)
        request_data = {"sender": account.address, "arguments": args or []}
        endpoint = f"/v2/contracts/call-read/{contract_address}/{contract_name}/{function_name}"
        
        print(f"\n{Colors.format_subheader('--- CONTRACT READ CALL ---')}")
        print(f"URL: {Colors.format_dim(f'{account.api_url}{endpoint}')}")
        print(f"Payload: {Colors.format_dim(json.dumps(request_data, indent=2))}")
        
        try:
            response = self.api_call(account, endpoint, "POST", json.dumps(request_data))
            if response.status_code == 200:
                data = response.json()
                print(f"{Colors.format_success('✓ Read-only call successful')}")
                print(f"Response: {Colors.format_info(json.dumps(data, indent=2))}")
                return data
            else:
                print(f"{Colors.format_error(f'✗ Read-only call failed: HTTP {response.status_code}')}")
                try:
                    error_data = response.json()
                    print(f"Error details: {Colors.format_error(json.dumps(error_data, indent=2))}")
                except:
                    print(f"Error text: {Colors.format_error(response.text)}")
                response.raise_for_status()
        except Exception as e:
            print(f"{Colors.format_error('✗ Contract read error')}: {Colors.format_error(str(e))}")
            raise
    
    def call(self, miner: str, contract_address: str, contract_name: str, function_name: str, args: Optional[List[str]] = None, nonce: Optional[int] = None) -> str:
        account = self.get_account(miner)
        
        # Get initial state for verification
        initial_nonce = self.get_nonce(miner) if nonce is None else nonce
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        print(f"\n{Colors.format_header('=== CONTRACT CALL ===')}")
        print(f"Contract: {Colors.format_info(f'{contract_address}.{contract_name}')}")
        print(f"Function: {Colors.format_success(function_name)}")
        print(f"Args: {Colors.format_dim(str(args or []))}")
        print(f"Initial balance: {Colors.format_dim(str(initial_balance))}")
        print(f"Using nonce: {Colors.format_dim(str(initial_nonce))}")
        
        # Use higher fee for complex contract calls
        if "huge" in contract_name.lower() or "mega" in contract_name.lower():
            fee = "50000"  # High fee for huge contracts
        elif "nft" in contract_name.lower():
            fee = "25000"  # Higher fee for NFT contract calls
        else:
            fee = "5000"  # Standard fee for regular contracts
        print(f"Using fee: {Colors.format_success(f'{fee} µSTX')}")
        
        cmd = ["blockstack-cli", "--testnet", "contract-call", account.private_key, fee, str(initial_nonce), contract_address, contract_name, function_name]
        if args:
            # Each argument must be prefixed with -e
            for arg in args:
                cmd.extend(["-e", arg])
        
        print(f"Command: {Colors.format_dim(' '.join(cmd))}")
        print(f"{Colors.format_dim('Creating transaction binary...')}")
        tx_binary = self.run_cli_command(cmd, binary_output=True)
        print(f"{Colors.format_dim('Submitting contract call...')}")
        response = self.api_call(account, "/v2/transactions", "POST", tx_binary)
        response.raise_for_status()
        
        txid = response.text.strip('"')
        print(f"{Colors.format_success('✓ Contract call submitted')}: {Colors.format_info(txid)}")
        
        # Verify the transaction
        verification = self.verify_transaction(miner, txid, initial_nonce, initial_balance, initial_height)
        if not verification['success']:
            raise RuntimeError(f"Contract call verification failed: {verification['error']}")
        
        return txid
