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
    
    def _extract_expected_nonce(self, error_str: str) -> Optional[int]:
        """Extract expected nonce from TooMuchChaining error message."""
        import re
        # Look for pattern like "expected': 26" in the error
        match = re.search(r"'expected':\s*(\d+)", error_str)
        if match:
            return int(match.group(1))
        return None

    def batch_deploy(self, from_miner: str, contracts: list, context: Optional[dict] = None) -> bool:
        """
        Submits contract deployments until the 'TooMuchChaining' limit is reached.
        This method is designed to be the first step in a multi-step recipe.
        It stores its findings in the provided 'context' dictionary for the
        next step to analyze.
        """
        if context is None:
            raise ValueError("A 'context' dictionary must be provided to the batch_deploy method.")

        account = self.get_account(from_miner)
        initial_nonce = self.get_nonce(from_miner)
        
        print(f"\n{Colors.format_header(f'=== BATCH CONTRACT DEPLOYMENT (until limit found) ===')}")
        print(f"Starting nonce: {Colors.format_dim(str(initial_nonce))}")

        # Phase 1: Preparation
        prepared_deployments = []
        for i, contract_file in enumerate(contracts):
            try:
                nonce = initial_nonce + i
                contract_name = f"stress-contract-{nonce}"
                
                # Calculate dynamic fee based on contract size
                if not os.path.isabs(contract_file):
                    test_path = os.path.join(os.path.dirname(__file__), '..', contract_file)
                    if os.path.exists(test_path):
                        contract_file = test_path
                
                with open(contract_file, 'r') as f:
                    contract_code = f.read().strip()
                
                contract_size = len(contract_code)
                base_fee = max(contract_size, 10000)
                fee = str(int(base_fee * 1.1))
                
                cmd = ["blockstack-cli", "--testnet", "publish", account.private_key, fee, str(nonce), contract_name, contract_file]
                deployment_binary = self.run_cli_command(cmd, binary_output=True)
                prepared_deployments.append({
                    'binary': deployment_binary, 
                    'contract_file': contract_file, 
                    'nonce': nonce,
                    'name': contract_name,
                    'fee': fee
                })
                
            except Exception as e:
                raise RuntimeError(f"Failed to prepare contract deployment for nonce {initial_nonce + i}: {e}")
        
        # Phase 2: Intelligent Submission
        successful_submissions = []
        limit_found_at_nonce = -1
        
        print(f"\n{Colors.format_subheader(f'Submitting contract deployments until mempool chaining limit is reached...')}")
        
        for deployment_data in prepared_deployments:
            nonce = deployment_data['nonce']
            contract_name = deployment_data['name']
            try:
                response = self.api_call(account, "/v2/transactions", "POST", deployment_data['binary'])
                txid = self.handle_api_response(response)
                successful_submissions.append({
                    'txid': txid, 
                    'contract_file': deployment_data['contract_file'], 
                    'nonce': nonce,
                    'name': contract_name
                })
                print(f"{Colors.format_success(f'✓ Deployed contract (nonce {nonce})')}: {Colors.format_dim(contract_name)} - {Colors.format_dim(txid)}")
                
            except Exception as e:
                error_str = str(e)
                if "TooMuchChaining" in error_str or "Nonce would exceed chaining limit" in error_str:
                    print(f"\n{Colors.format_success('✓ LIMIT FOUND')}: Node correctly rejected deployment with nonce {nonce}.")
                    print(f"  Reason: {Colors.format_warning(error_str)}")
                    
                    # Parse expected nonce from error message for immediate retry
                    expected_nonce = self._extract_expected_nonce(error_str)
                    current_block_height = self.get_block_height(from_miner)
                    
                    print(f"  Failed nonce: {nonce}, Expected nonce in error: {expected_nonce}")
                    print(f"  Last successful nonce: {successful_submissions[-1]['nonce'] if successful_submissions else 'none'}")
                    
                    # IMMEDIATE RETRY in same block
                    if expected_nonce is not None:
                        print(f"\n{Colors.format_header('=== IMMEDIATE RETRY IN SAME BLOCK ===')}")
                        
                        # Check block height hasn't proceeded
                        retry_block_height = self.get_block_height(from_miner)
                        if retry_block_height != current_block_height:
                            print(f"{Colors.format_error('✗ BLOCK PROCEEDED DURING RETRY SETUP!')}")
                            raise RuntimeError("Block proceeded during mempool testing - test must be restarted")
                        
                        # Find the deployment to retry with expected nonce
                        retry_deployment = None
                        for deploy_data in prepared_deployments:
                            if deploy_data['nonce'] == expected_nonce:
                                retry_deployment = deploy_data
                                break
                        
                        if retry_deployment:
                            print(f"Retrying contract deployment with nonce {expected_nonce} immediately...")
                            try:
                                # Double-check block height before submission
                                final_check_height = self.get_block_height(from_miner)
                                if final_check_height != current_block_height:
                                    print(f"{Colors.format_error('✗ BLOCK PROCEEDED DURING RETRY!')}")
                                    raise RuntimeError("Block proceeded during mempool testing - test must be restarted")
                                
                                response = self.api_call(account, "/v2/transactions", "POST", retry_deployment['binary'])
                                retry_txid = self.handle_api_response(response)
                                print(f"{Colors.format_success(f'✓ IMMEDIATE RETRY SUCCESS (nonce {expected_nonce})')}: {Colors.format_dim(retry_deployment['name'])} - {Colors.format_dim(retry_txid)}")
                                
                                # Add to successful submissions
                                successful_submissions.append({
                                    'txid': retry_txid, 
                                    'contract_file': retry_deployment['contract_file'], 
                                    'nonce': expected_nonce,
                                    'name': retry_deployment['name']
                                })
                                
                                # IMMEDIATELY try nonce +1 after successful retry
                                next_nonce = expected_nonce + 1
                                print(f"Now trying contract deployment nonce {next_nonce} immediately...")
                                
                                # Check block height again
                                next_check_height = self.get_block_height(from_miner)
                                if next_check_height != current_block_height:
                                    print(f"{Colors.format_error('✗ BLOCK PROCEEDED DURING NEXT RETRY!')}")
                                    raise RuntimeError("Block proceeded during mempool testing - test must be restarted")
                                
                                # Find deployment for next nonce
                                next_deployment = None
                                for deploy_data in prepared_deployments:
                                    if deploy_data['nonce'] == next_nonce:
                                        next_deployment = deploy_data
                                        break
                                
                                if next_deployment:
                                    try:
                                        response = self.api_call(account, "/v2/transactions", "POST", next_deployment['binary'])
                                        next_txid = self.handle_api_response(response)
                                        print(f"{Colors.format_success(f'✓ NEXT NONCE SUCCESS (nonce {next_nonce})')}: {Colors.format_dim(next_deployment['name'])} - {Colors.format_dim(next_txid)}")
                                        successful_submissions.append({
                                            'txid': next_txid, 
                                            'contract_file': next_deployment['contract_file'], 
                                            'nonce': next_nonce,
                                            'name': next_deployment['name']
                                        })
                                        
                                        # Continue the loop to try even more nonces
                                        print(f"Continuing to test higher nonces...")
                                        
                                    except Exception as next_e:
                                        next_error = str(next_e)
                                        print(f"{Colors.format_warning(f'✗ NEXT NONCE FAILED (nonce {next_nonce})')}: {next_error}")
                                        if "TooMuchChaining" in next_error:
                                            print(f"  Confirmed: Limit is now at nonce {next_nonce}")
                                else:
                                    print(f"{Colors.format_warning(f'⚠ No prepared deployment found for next nonce {next_nonce}')}")
                                
                            except Exception as retry_e:
                                retry_error = str(retry_e)
                                print(f"{Colors.format_error(f'✗ IMMEDIATE RETRY FAILED')}: {retry_error}")
                        else:
                            print(f"{Colors.format_warning(f'⚠ Could not find prepared deployment for nonce {expected_nonce}')}")
                    
                    limit_found_at_nonce = nonce
                    context['retry_info'] = {
                        'expected_nonce': expected_nonce,
                        'failed_nonce': nonce,
                        'retry_nonce': expected_nonce,
                        'block_height_when_failed': current_block_height,
                        'immediate_retry_attempted': expected_nonce is not None
                    }
                    break
                else:
                    print(f"{Colors.format_error(f'✗ UNEXPECTED ERROR at nonce {nonce}')}")
                    raise e
        
        # Phase 3: Wait for submitted deployments to confirm
        if successful_submissions:
            print(f"\n{Colors.format_subheader('Waiting for submitted contract deployments to confirm...')}")
            last_submitted_nonce = successful_submissions[-1]['nonce']
            self.wait_for_nonce_increase(from_miner, last_submitted_nonce, 1, timeout=60)
            print("Confirmation wait complete.")

        # Phase 4: Store the results in the shared context
        context['batch_report'] = {
            "status": "LimitFound" if limit_found_at_nonce != -1 else "CompletedWithoutLimit",
            "successful_submissions": successful_submissions,
            "limit_nonce": limit_found_at_nonce,
            "from_miner": from_miner
        }
        
        # This step is successful if it completes without an unexpected error.
        return True
