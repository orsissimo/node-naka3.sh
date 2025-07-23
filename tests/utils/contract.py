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
        
        # Get initial state for verification
        initial_nonce = self.get_nonce(miner) if nonce is None else nonce
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        print(f"\n=== Contract Deployment ===")
        print(f"Contract: {contract_name}")
        print(f"File: {contract_file}")
        print(f"Initial balance: {initial_balance}")
        print(f"Using nonce: {initial_nonce}")
        
        # Use higher fee for contracts (especially NFTs need more gas)
        fee = "20000" if "nft" in contract_file.lower() or "nft" in contract_name.lower() else "1000"
        cmd = ["blockstack-cli", "--testnet", "publish", account.private_key, fee, str(initial_nonce), contract_name, contract_file]
        tx_binary = self.run_cli_command(cmd, binary_output=True)
        response = self.api_call(account, "/v2/transactions", "POST", tx_binary)
        response.raise_for_status()
        
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
            cmd.extend(args)
        
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
    
    def deploy_and_test(self, miner: str, contract_file: str, contract_name: str, test_functions: List[Dict] = None) -> Dict[str, Any]:
        account = self.get_account(miner)
        initial_nonce = self.get_nonce(miner)
        
        # Generate unique contract name with nonce like test-contract.py does
        dynamic_contract_name = f"{contract_name}{initial_nonce}"
        
        # Deploy contract (verification is built into deploy method now)
        try:
            deploy_txid = self.deploy(miner, contract_file, dynamic_contract_name, initial_nonce)
        except Exception as e:
            return {'success': False, 'error': f'Contract deployment failed: {e}'}
        
        results = {'success': True, 'deploy_txid': deploy_txid, 'contract_address': account.address, 'contract_name': dynamic_contract_name, 'function_results': []}
        
        if test_functions:
            # Add brief delay for contract to be available
            print("\n=== Contract Function Tests ===")
            time.sleep(3)
            current_nonce = self.get_nonce(miner)
            
            for func in test_functions:
                try:
                    if func['type'] == 'read':
                        print(f"\n--- Reading {func['name']} ---")
                        result = self.read(miner, account.address, dynamic_contract_name, func['name'], func.get('args'))
                        print(f"✓ Read result: {result}")
                    elif func['type'] == 'public':
                        # Call method (verification is built into call method now)
                        result = self.call(miner, account.address, dynamic_contract_name, func['name'], func.get('args'), current_nonce)
                        current_nonce += 1
                    
                    results['function_results'].append({'function': func['name'], 'type': func['type'], 'success': True, 'result': result})
                except Exception as e:
                    print(f"✗ Function {func['name']} failed: {e}")
                    results['function_results'].append({'function': func['name'], 'type': func['type'], 'success': False, 'error': str(e)})
        
        return results
    
    def batch_deploy(self, miner: str, contracts: List[Dict]) -> List[Dict[str, Any]]:
        results = []
        initial_nonce = self.get_nonce(miner)
        initial_height = self.get_block_height(miner)
        
        for i, contract in enumerate(contracts):
            try:
                txid = self.deploy(miner, contract['file'], contract['name'], initial_nonce + i)
                results.append({'success': True, 'txid': txid, 'contract': contract, 'nonce': initial_nonce + i})
            except Exception as e:
                results.append({'success': False, 'error': str(e), 'contract': contract, 'nonce': initial_nonce + i})
        
        if results:
            self.wait_for_confirmation(miner, initial_nonce + len(contracts) - 1, initial_height, timeout=120)
        return results