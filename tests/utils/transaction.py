import time
import json
import os
from typing import Optional, Dict, Any
from .base import StacksTestBase, Colors
from .exceptions import BatchProcessingError

class Transaction(StacksTestBase):
    
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
                    limit_found_at_nonce = nonce
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