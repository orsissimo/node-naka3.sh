import os
import json
import time
from typing import Optional, Dict, Any, List
from .base import StacksTestBase

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
            print(f"✓ Contract file loaded ({len(contract_code)} characters)")
        except Exception as e:
            print(f"✗ Error reading contract file: {e}")
            raise
        
        # Get initial state for verification
        initial_nonce = self.get_nonce(miner) if nonce is None else nonce
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        print(f"\n=== Contract Deployment ===")
        print(f"Contract: {contract_name}")
        print(f"File: {contract_file}")
        print(f"Initial balance: {initial_balance}")
        print(f"Using nonce: {initial_nonce}")
        print(f"Account: {account.address}")
        
        # Use appropriate fee for contracts - higher for NFTs, reasonable for others
        if "nft" in contract_file.lower() or "nft" in contract_name.lower() or "cyberpunk" in contract_name.lower():
            fee = "50000"  # Higher fee for complex NFT contracts
        else:
            fee = "10000"  # Standard fee for contracts
            
        print(f"Using fee: {fee} µSTX")
        
        cmd = ["blockstack-cli", "--testnet", "publish", account.private_key, fee, str(initial_nonce), contract_name, contract_file]
        
        print(f"Creating contract deployment transaction...")
        print(f"Command: {' '.join(cmd)}")
        
        try:
            tx_binary = self.run_cli_command(cmd, binary_output=True)
            print(f"✓ Transaction binary created (length: {len(tx_binary)} bytes)")
        except Exception as e:
            print(f"✗ Failed to create transaction binary: {e}")
            raise
        
        print(f"Submitting transaction to {account.api_url}/v2/transactions...")
        
        try:
            response = self.api_call(account, "/v2/transactions", "POST", tx_binary)
            print(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"✗ Transaction submission failed")
                print(f"Response headers: {dict(response.headers)}")
                try:
                    error_data = response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error text: {response.text}")
                
            response.raise_for_status()
        except Exception as e:
            print(f"✗ API call failed: {e}")
            raise
        
        txid = response.text.strip('"')
        print(f"✓ Contract deployment submitted: {txid}")
        
        # Verify the transaction
        verification = self.verify_transaction(miner, txid, initial_nonce, initial_balance, initial_height)
        if not verification['success']:
            raise RuntimeError(f"Contract deployment verification failed: {verification['error']}")
        
        return txid
    
    def read(self, miner: str, contract_address: str, contract_name: str, function_name: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        account = self.get_account(miner)
        request_data = {"sender": account.address, "arguments": args or []}
        endpoint = f"/v2/contracts/call-read/{contract_address}/{contract_name}/{function_name}"
        
        print(f"\n--- Contract Read Call ---")
        print(f"URL: {account.api_url}{endpoint}")
        print(f"Payload: {json.dumps(request_data, indent=2)}")
        
        try:
            response = self.api_call(account, endpoint, "POST", json.dumps(request_data))
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Read-only call successful")
                print(f"Response: {json.dumps(data, indent=2)}")
                return data
            else:
                print(f"✗ Read-only call failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error text: {response.text}")
                response.raise_for_status()
        except Exception as e:
            print(f"✗ Contract read error: {e}")
            raise
    
    def call(self, miner: str, contract_address: str, contract_name: str, function_name: str, args: Optional[List[str]] = None, nonce: Optional[int] = None) -> str:
        account = self.get_account(miner)
        
        # Get initial state for verification
        initial_nonce = self.get_nonce(miner) if nonce is None else nonce
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        print(f"\n=== Contract Call ===")
        print(f"Contract: {contract_address}.{contract_name}")
        print(f"Function: {function_name}")
        print(f"Args: {args or []}")
        print(f"Initial balance: {initial_balance}")
        print(f"Using nonce: {initial_nonce}")
        
        # Use higher fee for NFT contract calls
        fee = "20000" if "nft" in contract_name.lower() else "1000"
        cmd = ["blockstack-cli", "--testnet", "contract-call", account.private_key, fee, str(initial_nonce), contract_address, contract_name, function_name]
        if args:
            # Each argument must be prefixed with -e
            for arg in args:
                cmd.extend(["-e", arg])
        
        tx_binary = self.run_cli_command(cmd, binary_output=True)
        response = self.api_call(account, "/v2/transactions", "POST", tx_binary)
        response.raise_for_status()
        
        txid = response.text.strip('"')
        print(f"✓ Contract call submitted: {txid}")
        
        # Verify the transaction
        verification = self.verify_transaction(miner, txid, initial_nonce, initial_balance, initial_height)
        if not verification['success']:
            raise RuntimeError(f"Contract call verification failed: {verification['error']}")
        
        return txid
