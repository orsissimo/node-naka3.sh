import time
import json
from typing import Optional, Dict, Any
from .base import StacksTestBase, Colors

class Transaction(StacksTestBase):
    
    def transfer(self, from_miner: str, to_address: str, amount: int, 
                memo: Optional[str] = None, nonce: Optional[int] = None, silent: bool = False) -> str:
        account = self.get_account(from_miner)
        
        # Get initial state for verification (like test-transaction.py does)
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
        response.raise_for_status()
        
        txid = response.text.strip('"')
        if not silent:
            print(f"{Colors.format_success(f'✓ Transaction ID: {txid}')}")
        
        # Use consolidated verification with recipient tracking
        verification = self.verify_transaction(from_miner, txid, initial_nonce, initial_sender_balance, initial_height, to_address)
        if not verification['success']:
            raise RuntimeError(f"Transfer verification failed: {verification['error']}")
        
        return txid
    
    
    def batch(self, from_miner: str, transfers: list, wait_between: bool = False) -> list:
        """Submit multiple transactions rapidly to be included in the same block"""
        account = self.get_account(from_miner)
        initial_nonce = self.get_nonce(from_miner)
        initial_height = self.get_block_height(from_miner)
        
        print(f"\n{Colors.format_header(f'=== BATCH TRANSFER ({len(transfers)} transactions) ===')}")
        print(f"Starting nonce: {Colors.format_dim(str(initial_nonce))}")
        print(f"Block height: {Colors.format_dim(str(initial_height))}")
        
        # Phase 1: Prepare all transactions as binary data
        prepared_txs = []
        for i, t in enumerate(transfers):
            try:
                nonce = initial_nonce + i
                cmd = ["blockstack-cli", "--testnet", "token-transfer", account.private_key, "180", str(nonce), t['to'], str(t['amount'])]
                if t.get('memo'):
                    cmd.append(t['memo'])
                
                tx_binary = self.run_cli_command(cmd, binary_output=True)
                prepared_txs.append({
                    'binary': tx_binary,
                    'transfer': t,
                    'nonce': nonce,
                    'index': i
                })
                amount_text = f"{t['amount']} µSTX"
                to_text = f"{t['to'][:10]}..."
                print(f"{Colors.format_success(f'✓ Prepared tx {i+1}')}: {Colors.format_info(amount_text)} to {Colors.format_dim(to_text)} (nonce {Colors.format_dim(str(nonce))})")
            except Exception as e:
                print(f"{Colors.format_error(f'✗ Failed to prepare tx {i+1}')}: {Colors.format_error(str(e))}")
                prepared_txs.append({
                    'error': str(e),
                    'transfer': t,
                    'nonce': initial_nonce + i,
                    'index': i
                })
        
        # Phase 2: Submit all transactions rapidly without waiting
        results = []
        submitted_txs = []
        
        print(f"\n{Colors.format_subheader(f'Submitting {len(prepared_txs)} transactions rapidly...')}")
        start_time = time.time()
        
        for tx_data in prepared_txs:
            if 'error' in tx_data:
                results.append({'success': False, 'error': tx_data['error'], 'transfer': tx_data['transfer'], 'nonce': tx_data['nonce']})
                continue
                
            try:
                response = self.api_call(account, "/v2/transactions", "POST", tx_data['binary'])
                response.raise_for_status()
                
                txid = response.text.strip('"')
                submitted_txs.append(txid)
                results.append({'success': True, 'txid': txid, 'transfer': tx_data['transfer'], 'nonce': tx_data['nonce']})
                submitted_index = tx_data['index'] + 1
                print(f"{Colors.format_success(f'✓ Submitted tx {submitted_index}')}: {Colors.format_dim(txid)}")
                
            except Exception as e:
                failed_index = tx_data['index'] + 1
                print(f"{Colors.format_error(f'✗ Failed to submit tx {failed_index}')}: {Colors.format_error(str(e))}")
                results.append({'success': False, 'error': str(e), 'transfer': tx_data['transfer'], 'nonce': tx_data['nonce']})
        
        submission_time = time.time() - start_time
        successful_submissions = len([r for r in results if r.get('success', False)])
        
        print(f"{Colors.format_success(f'✓ Batch submission complete')}: {Colors.format_info(f'{successful_submissions}/{len(transfers)}')} transactions submitted in {Colors.format_dim(f'{submission_time:.2f}s')}")
        
        # Phase 3: Wait for confirmation and verify all batch transactions
        if successful_submissions > 0:
            print(f"{Colors.format_subheader('Waiting for batch transactions to be confirmed...')}")
            
            # Wait for the final nonce to reach expected value (initial + successful submissions)
            final_nonce = self.wait_for_nonce_increase(from_miner, initial_nonce, successful_submissions, timeout=30)
            final_height = self.get_block_height(from_miner)
            
            if final_nonce >= initial_nonce + successful_submissions:
                print(f"{Colors.format_success('✓ All batch transactions confirmed')} (nonce: {Colors.format_dim(f'{initial_nonce} → {final_nonce}')})")
                print(f"{Colors.format_success('✓ Block height')}: {Colors.format_dim(f'{initial_height} → {final_height}')}")
                
                # Now verify each transaction individually using the existing verify_transaction method
                verified_count = 0
                same_block_count = 0
                
                for i, result in enumerate(results):
                    if result.get('success', False):
                        print(f"\n{Colors.format_subheader(f'Verifying batch transaction {i+1}/{len(results)}')}: {Colors.format_dim(result['txid'])}")
                        try:
                            # Use the existing verify_transaction method but skip the confirmation wait
                            # since we already waited for all transactions
                            verification = self.verify_transaction_direct(
                                from_miner, 
                                result['txid'], 
                                result['transfer'].get('to')
                            )
                            
                            if verification.get('success', False):
                                verified_count += 1
                                tx_data = verification.get('transaction_data', {})
                                if 'index_block_hash' in tx_data:
                                    # Check if this transaction is in the same block as others
                                    # For simplicity, we'll count transactions in the final block
                                    same_block_count += 1
                                    print(f"{Colors.format_success(f'✓ Transaction {i+1} verified and included in block')}")
                                else:
                                    print(f"{Colors.format_warning(f'⚠ Transaction {i+1} verified but block info unavailable')}")
                            else:
                                print(f"{Colors.format_error(f'✗ Transaction {i+1} verification failed')}: {Colors.format_error(verification.get('error', 'Unknown error'))}")
                        except Exception as e:
                            print(f"{Colors.format_error(f'✗ Transaction {i+1} verification error')}: {Colors.format_error(str(e))}")
                
                print(f"\n{Colors.format_success('✓ Batch verification complete')}: {Colors.format_info(f'{verified_count}/{successful_submissions}')} transactions verified")
                print(f"{Colors.format_success('✓')} {Colors.format_info(f'{same_block_count}/{successful_submissions}')} transactions confirmed in blocks")
                
                # Show final account state for the batch sender
                print(f"\n{Colors.format_header('=== FINAL BATCH SENDER ACCOUNT STATE ===')}")
                try:
                    account = self.get_account(from_miner)
                    response = self.api_call(account, f"/v2/accounts/{account.address}")
                    response.raise_for_status()
                    final_account_info = response.json()
                    print(f"Account: {Colors.format_info(account.address)}")
                    print(f"Final nonce: {Colors.format_success(str(final_account_info.get('nonce', 'unknown')))}")
                    print(f"Final balance: {Colors.format_success(str(final_account_info.get('balance', 'unknown')))}")
                    print(f"{Colors.format_subheader('=== FULL ACCOUNT INFO ===')}")
                    print(f"{Colors.format_dim(json.dumps(final_account_info, indent=2))}")
                    print(f"{Colors.format_subheader('=== END ACCOUNT INFO ===')}")
                except Exception as e:
                    print(f"{Colors.format_warning(f'⚠ Could not fetch final account state')}: {Colors.format_error(str(e))}")
            else:
                print(f"{Colors.format_warning(f'⚠ Expected nonce {initial_nonce + successful_submissions}, got {final_nonce}')}")
                print(f"{Colors.format_warning('⚠ Some batch transactions may have failed')}")
        
        return results
    
    def status(self, miner: str, tx_id: str) -> Dict[str, Any]:
        account = self.get_account(miner)
        response = self.api_call(account, f"/extended/v1/tx/{tx_id}")
        response.raise_for_status()
        return response.json()