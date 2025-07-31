import time
import json
import os
from typing import Optional, Dict, Any
from .base import StacksTestBase, Colors
from .exceptions import BatchProcessingError

class Transaction(StacksTestBase):
    
    def __init__(self):
        super().__init__()
        self.submitted_transactions = []  # Store submitted transaction IDs for later verification
    
    def transfer(self, from_miner: str, to_address: str, amount: int, 
                memo: Optional[str] = None, nonce: Optional[int] = None, silent: bool = False) -> str:
        account = self.get_account(from_miner)
        
        initial_nonce = self.get_nonce(from_miner) if nonce is None else nonce
        initial_sender_balance = self.get_balance(from_miner)
        initial_recipient_balance = self.get_balance(from_miner, to_address)
        initial_height = self.get_block_height(from_miner)
        
        if not silent:
            print(f"\n{Colors.format_header('=== STX TRANSFER ===')}")
            print(f"From: {Colors.format_info(account.address)}")
            print(f"To: {Colors.format_info(to_address)}")
            print(f"Amount: {Colors.format_success(f'{amount} µSTX')}")
            if memo:
                print(f"Memo: {Colors.format_dim(memo)}")
            print(f"Sender balance before: {Colors.format_dim(str(initial_sender_balance))}")
            print(f"Recipient balance before: {Colors.format_dim(str(initial_recipient_balance))}")
            print(f"Using nonce: {Colors.format_dim(str(initial_nonce))}")
        
        cmd = ["blockstack-cli", "--testnet", "token-transfer", account.private_key, "180", str(initial_nonce), to_address, str(amount)]
        if memo:
            cmd.append(memo)
        
        if not silent:
            print(f"{Colors.format_dim('Creating transaction...')}")
        tx_binary = self.run_cli_command(cmd, binary_output=True)
        
        if not silent:
            print(f"{Colors.format_dim('Submitting transaction...')}")
        response = self.api_call(account, "/v2/transactions", "POST", tx_binary)
        txid = self.handle_api_response(response)
        
        if not silent:
            print(f"{Colors.format_success(f'✓ Transaction ID: {txid}')}")
        
        verification = self.verify_transaction(from_miner, txid, initial_nonce, initial_sender_balance, initial_height, to_address)
        if not verification['success']:
            raise RuntimeError(f"Transfer verification failed: {verification['error']}")
        
        return txid
    
    def batch(self, from_miner: str, transfers: list, context: Optional[dict] = None) -> bool:
        """
        Submits transactions until the 'TooMuchChaining' limit is reached.
        This method is designed to be the first step in a multi-step recipe.
        It stores its findings in the provided 'context' dictionary for the
        next step to analyze.
        """
        if context is None:
            raise ValueError("A 'context' dictionary must be provided to the batch method.")

        account = self.get_account(from_miner)
        initial_nonce = self.get_nonce(from_miner)
        
        print(f"\n{Colors.format_header(f'=== BATCH SUBMISSION (until limit found) ===')}")
        print(f"Starting nonce: {Colors.format_dim(str(initial_nonce))}")

        # Phase 1: Preparation
        prepared_txs = []
        for i, t in enumerate(transfers):
            try:
                nonce = initial_nonce + i
                cmd = ["blockstack-cli", "--testnet", "token-transfer", account.private_key, "180", str(nonce), t['to'], str(t['amount']), t.get('memo', '')]
                tx_binary = self.run_cli_command(cmd, binary_output=True)
                prepared_txs.append({'binary': tx_binary, 'transfer': t, 'nonce': nonce})
            except Exception as e:
                raise RuntimeError(f"Failed to prepare transaction for nonce {initial_nonce + i}: {e}")
        
        # Phase 2: Intelligent Submission
        successful_submissions = []
        limit_found_at_nonce = -1
        
        print(f"\n{Colors.format_subheader(f'Submitting transactions until mempool chaining limit is reached...')}")
        
        for tx_data in prepared_txs:
            nonce = tx_data['nonce']
            try:
                response = self.api_call(account, "/v2/transactions", "POST", tx_data['binary'])
                txid = self.handle_api_response(response)
                successful_submissions.append({'txid': txid, 'transfer': tx_data['transfer'], 'nonce': nonce})
                print(f"{Colors.format_success(f'✓ Submitted tx (nonce {nonce})')}: {Colors.format_dim(txid)}")
            except Exception as e:
                error_str = str(e)
                if "TooMuchChaining" in error_str or "Nonce would exceed chaining limit" in error_str:
                    print(f"\n{Colors.format_success('✓ LIMIT FOUND')}: Node correctly rejected transaction with nonce {nonce}.")
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
                        
                        # Find the transaction to retry with expected nonce
                        retry_tx = None
                        for tx_data in prepared_txs:
                            if tx_data['nonce'] == expected_nonce:
                                retry_tx = tx_data
                                break
                        
                        if retry_tx:
                            print(f"Retrying with nonce {expected_nonce} immediately...")
                            try:
                                # Double-check block height before submission
                                final_check_height = self.get_block_height(from_miner)
                                if final_check_height != current_block_height:
                                    print(f"{Colors.format_error('✗ BLOCK PROCEEDED DURING RETRY!')}")
                                    raise RuntimeError("Block proceeded during mempool testing - test must be restarted")
                                
                                response = self.api_call(account, "/v2/transactions", "POST", retry_tx['binary'])
                                retry_txid = self.handle_api_response(response)
                                print(f"{Colors.format_success(f'✓ IMMEDIATE RETRY SUCCESS (nonce {expected_nonce})')}: {Colors.format_dim(retry_txid)}")
                                
                                # Add to successful submissions
                                successful_submissions.append({'txid': retry_txid, 'transfer': retry_tx['transfer'], 'nonce': expected_nonce})
                                
                                # IMMEDIATELY try nonce +1 after successful retry
                                next_nonce = expected_nonce + 1
                                print(f"Now trying nonce {next_nonce} immediately...")
                                
                                # Check block height again
                                next_check_height = self.get_block_height(from_miner)
                                if next_check_height != current_block_height:
                                    print(f"{Colors.format_error('✗ BLOCK PROCEEDED DURING NEXT RETRY!')}")
                                    raise RuntimeError("Block proceeded during mempool testing - test must be restarted")
                                
                                # Find or create transaction for next nonce
                                next_tx = None
                                for tx_data in prepared_txs:
                                    if tx_data['nonce'] == next_nonce:
                                        next_tx = tx_data
                                        break
                                
                                if next_tx:
                                    try:
                                        response = self.api_call(account, "/v2/transactions", "POST", next_tx['binary'])
                                        next_txid = self.handle_api_response(response)
                                        print(f"{Colors.format_success(f'✓ NEXT NONCE SUCCESS (nonce {next_nonce})')}: {Colors.format_dim(next_txid)}")
                                        successful_submissions.append({'txid': next_txid, 'transfer': next_tx['transfer'], 'nonce': next_nonce})
                                        
                                        # Continue the loop to try even more nonces
                                        print(f"Continuing to test higher nonces...")
                                        
                                    except Exception as next_e:
                                        next_error = str(next_e)
                                        print(f"{Colors.format_warning(f'✗ NEXT NONCE FAILED (nonce {next_nonce})')}: {next_error}")
                                        if "TooMuchChaining" in next_error:
                                            print(f"  Confirmed: Limit is now at nonce {next_nonce}")
                                        # Don't break - let the outer logic handle this
                                else:
                                    print(f"{Colors.format_warning(f'⚠ No prepared tx found for next nonce {next_nonce}')}")
                                
                            except Exception as retry_e:
                                retry_error = str(retry_e)
                                print(f"{Colors.format_error(f'✗ IMMEDIATE RETRY FAILED')}: {retry_error}")
                                # Continue with original logic - store retry info for later analysis
                        else:
                            print(f"{Colors.format_warning(f'⚠ Could not find prepared tx for nonce {expected_nonce}')}")
                    
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
        
        # Phase 3: Wait for submitted transactions to confirm
        if successful_submissions:
            print(f"\n{Colors.format_subheader('Waiting for submitted transactions to confirm...')}")
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
    
    def sponsored_transfer(self, origin_miner: str, sponsor_miner: str, to_address: str, 
                           amount: int, sponsor_nonce: int) -> str:
        """Creates and submits a sponsored transaction, allowing us to test sponsor nonce limits."""
        
        origin_account = self.get_account(origin_miner)
        sponsor_account = self.get_account(sponsor_miner)
        
        print(f"\n{Colors.format_header('=== SPONSORED STX TRANSFER ===')}")
        print(f"Origin: {Colors.format_info(origin_account.address)}")
        print(f"Sponsor: {Colors.format_info(sponsor_account.address)}")
        print(f"Sponsor Nonce: {Colors.format_dim(str(sponsor_nonce))}")
        
        cmd_create = [
            "blockstack-cli", "--testnet", "make-token-transfer",
            origin_account.private_key, to_address, str(amount), "sponsored-tx"
        ]
        unsigned_hex = self.run_cli_command(cmd_create).decode().strip()

        cmd_sponsor = [
            "blockstack-cli", "--testnet", "sponsor-tx",
            sponsor_account.private_key, "2000", str(sponsor_nonce), unsigned_hex
        ]
        
        print(f"{Colors.format_dim('Creating sponsored transaction binary...')}")
        tx_binary = self.run_cli_command(cmd_sponsor, binary_output=True)
        
        print(f"{Colors.format_dim('Submitting sponsored transaction...')}")
        response = self.api_call(sponsor_account, "/v2/transactions", "POST", tx_binary)
        txid = self.handle_api_response(response)
        
        print(f"{Colors.format_success('✓ Sponsored transaction submitted (this should not happen in this test)')}")
        return txid

    def status(self, miner: str, tx_id: str) -> Dict[str, Any]:
        account = self.get_account(miner)
        response = self.api_call(account, f"/extended/v1/tx/{tx_id}")
        return self.handle_api_response(response)
    
    def _extract_expected_nonce(self, error_str: str) -> Optional[int]:
        """Extract expected nonce from TooMuchChaining error message."""
        import re
        # Look for pattern like "expected': 26" in the error
        match = re.search(r"'expected':\s*(\d+)", error_str)
        if match:
            return int(match.group(1))
        return None

    def submit_no_wait(self, target_miner: str, from_miner: str, to_address: str, 
                          amount: int, memo: Optional[str] = None, nonce: Optional[int] = None) -> str:
        """Submit transaction to specific miner's endpoint without waiting for confirmation"""
        from_account = self.get_account(from_miner)
        target_account = self.get_account(target_miner)
        
        # Use provided nonce or get current nonce
        if nonce is not None:
            use_nonce = nonce
        else:
            use_nonce = self.get_nonce(from_miner)
            
        initial_height = self.get_block_height(target_miner)
        
        print(f"\n{Colors.format_header('=== SUBMITTING UNPROCESSED TX ===')}")
        print(f"Target Miner: {Colors.format_info(target_miner)} (endpoint: {target_account.api_url})")
        print(f"From Account: {Colors.format_info(from_account.address)}")
        print(f"To Address: {Colors.format_info(to_address)}")
        print(f"Amount: {Colors.format_success(f'{amount} µSTX')}")
        print(f"Current Block Height: {Colors.format_dim(str(initial_height))}")
        print(f"Using nonce: {Colors.format_dim(str(use_nonce))}")
        
        # Create transaction
        cmd = ["blockstack-cli", "--testnet", "token-transfer", from_account.private_key, 
               "180", str(use_nonce), to_address, str(amount)]
        if memo:
            cmd.append(memo)
        
        print(f"{Colors.format_dim('Creating transaction binary...')}")
        tx_binary = self.run_cli_command(cmd, binary_output=True)
        
        # Submit to specific miner's endpoint
        print(f"{Colors.format_dim(f'Submitting to {target_miner} endpoint...')}")
        response = self.api_call(target_account, "/v2/transactions", "POST", tx_binary)
        txid = self.handle_api_response(response)
        
        print(f"{Colors.format_success(f'✓ Transaction submitted to {target_miner}: {txid}')}")
        print(f"{Colors.format_warning('⚠ NOT waiting for confirmation - keeping in mempool')}")
        
        # Store transaction info for later verification
        self.submitted_transactions.append({
            'txid': txid,
            'from_miner': from_miner,
            'target_miner': target_miner,
            'to_address': to_address,
            'amount': amount,
            'nonce': use_nonce,
            'memo': memo
        })
        
        return txid

    def verify_previous_transactions(self, query_miner: str, check_stopped_miner: bool = False, 
                                   check_resumed_miner: bool = False) -> Dict[str, Any]:
        """Verify previously submitted transactions using verify_transaction_no_wait from base.py"""
        
        if check_stopped_miner:
            print(f"\n{Colors.format_header('=== VERIFYING TXS WHILE MINER2 IS STOPPED ===')}")
            print(f"Query Miner: {Colors.format_info(query_miner)} (checking from active miner)")
        elif check_resumed_miner:
            print(f"\n{Colors.format_header('=== VERIFYING TXS AFTER MINER2 RESUMED ===')}")
            print(f"Query Miner: {Colors.format_info(query_miner)} (checking from resumed miner)")
        else:
            print(f"\n{Colors.format_header('=== VERIFYING PREVIOUS TRANSACTIONS ===')}")
            print(f"Query Miner: {Colors.format_info(query_miner)}")
        
        if not self.submitted_transactions:
            print(f"{Colors.format_warning('⚠ No previous transactions to verify')}")
            return {"success": False, "error": "No transactions submitted"}
        
        print(f"Transactions to verify: {Colors.format_info(str(len(self.submitted_transactions)))}")
        
        verification_results = []
        for i, tx_info in enumerate(self.submitted_transactions, 1):
            txid = tx_info['txid']
            print(f"\n{Colors.format_subheader(f'Verifying Transaction {i}/{len(self.submitted_transactions)}')}")
            print(f"  TX ID: {Colors.format_dim(txid)}")
            print(f"  From: {Colors.format_dim(tx_info['from_miner'])}")
            print(f"  To: {Colors.format_dim(tx_info['to_address'])}")
            print(f"  Amount: {Colors.format_dim(str(tx_info['amount']))} µSTX")
            print(f"  Nonce: {Colors.format_dim(str(tx_info['nonce']))}")
            
            # Use verify_transaction_no_wait from base.py
            try:
                verification = self.verify_transaction_no_wait(query_miner, txid, tx_info['to_address'])
                verification_results.append({
                    'txid': txid,
                    'verification': verification
                })
                
                if verification['success']:
                    print(f"  Status: {Colors.format_success('✓ TRANSACTION FOUND')}")
                    if 'transaction_data' in verification:
                        tx_data = verification['transaction_data']
                        if isinstance(tx_data, dict) and 'tx_status' in tx_data:
                            status = tx_data['tx_status']
                            print(f"  Chain Status: {Colors.format_info(status)}")
                else:
                    print(f"  Status: {Colors.format_error('✗ TRANSACTION NOT FOUND OR ERROR')}")
                    if 'error' in verification:
                        print(f"  Error: {Colors.format_error(verification['error'])}")
                        
            except Exception as e:
                print(f"  Status: {Colors.format_error('✗ VERIFICATION FAILED')}")
                print(f"  Error: {Colors.format_error(str(e))}")
                verification_results.append({
                    'txid': txid,
                    'verification': {'success': False, 'error': str(e)}
                })
        
        # Summary
        successful_verifications = sum(1 for result in verification_results 
                                     if result['verification']['success'])
        total_verifications = len(verification_results)
        
        print(f"\n{Colors.format_subheader('VERIFICATION SUMMARY')}")
        print(f"Successful verifications: {Colors.format_info(f'{successful_verifications}/{total_verifications}')}")
        
        if check_stopped_miner:
            if successful_verifications == 0:
                print(f"{Colors.format_success('✓ Expected: No transactions found while miner2 stopped')}")
                return {"success": True, "verified_count": successful_verifications, "expected_failure": True}
            else:
                print(f"{Colors.format_warning('⚠ Unexpected: Some transactions found from other miners')}")
                return {"success": True, "verified_count": successful_verifications, "unexpected_success": True}
        elif check_resumed_miner:
            if successful_verifications > 0:
                print(f"{Colors.format_success('✓ Expected: Transactions recovered after miner2 resumed')}")
                return {"success": True, "verified_count": successful_verifications, "recovery_success": True}
            else:
                print(f"{Colors.format_warning('⚠ Transactions still not found after resume')}")
                return {"success": True, "verified_count": successful_verifications, "recovery_partial": True}
        else:
            return {"success": True, "verified_count": successful_verifications}
        
        return {"success": True, "verified_count": successful_verifications}