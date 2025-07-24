import time
import json
from typing import Optional, Dict, Any
from .base import StacksTestBase

class Transaction(StacksTestBase):
    
    def transfer(self, from_miner: str, to_address: str, amount: int, 
                memo: Optional[str] = None, nonce: Optional[int] = None) -> str:
        account = self.get_account(from_miner)
        
        # Get initial state for verification (like test-transaction.py does)
        initial_nonce = self.get_nonce(from_miner) if nonce is None else nonce
        initial_sender_balance = self.get_balance(from_miner)
        initial_recipient_balance = self.get_balance(from_miner, to_address)
        initial_height = self.get_block_height(from_miner)
        
        print(f"\n=== STX Transfer ===")
        print(f"From: {account.address}")
        print(f"To: {to_address}")
        print(f"Amount: {amount} µSTX")
        if memo:
            print(f"Memo: {memo}")
        print(f"Sender balance before: {initial_sender_balance}")
        print(f"Recipient balance before: {initial_recipient_balance}")
        print(f"Using nonce: {initial_nonce}")
        
        cmd = ["blockstack-cli", "--testnet", "token-transfer", account.private_key, "180", str(initial_nonce), to_address, str(amount)]
        if memo:
            cmd.append(memo)
        
        print("Creating transaction...")
        tx_binary = self.run_cli_command(cmd, binary_output=True)
        
        print("Submitting transaction...")
        response = self.api_call(account, "/v2/transactions", "POST", tx_binary)
        response.raise_for_status()
        
        txid = response.text.strip('"')
        print(f"✓ Transaction ID: {txid}")
        
        # Use consolidated verification with recipient tracking
        verification = self.verify_transaction(from_miner, txid, initial_nonce, initial_sender_balance, initial_height, to_address)
        if not verification['success']:
            raise RuntimeError(f"Transfer verification failed: {verification['error']}")
        
        return txid
    
    
    def batch(self, from_miner: str, transfers: list, wait_between: bool = False) -> list:
        results = []
        initial_nonce = self.get_nonce(from_miner)
        initial_height = self.get_block_height(from_miner)
        
        print(f"\n=== Batch Transfer ({len(transfers)} transactions) ===")
        
        for i, t in enumerate(transfers):
            try:
                # The transfer method now includes verification, so each transfer is verified
                tx_id = self.transfer(from_miner, t['to'], t['amount'], t.get('memo'), initial_nonce + i)
                results.append({'success': True, 'txid': tx_id, 'transfer': t, 'nonce': initial_nonce + i})
                
                if wait_between and i < len(transfers) - 1:
                    # Additional wait between transfers if requested
                    time.sleep(1)
            except Exception as e:
                print(f"✗ Transfer {i+1} failed: {e}")
                results.append({'success': False, 'error': str(e), 'transfer': t, 'nonce': initial_nonce + i})
        
        successful_transfers = [r for r in results if r.get('success', False)]
        print(f"✓ Batch complete: {len(successful_transfers)}/{len(transfers)} transfers successful")
        
        return results
    
    def status(self, miner: str, tx_id: str) -> Dict[str, Any]:
        account = self.get_account(miner)
        response = self.api_call(account, f"/extended/v1/tx/{tx_id}")
        response.raise_for_status()
        return response.json()
    
    def stress(self, miner: str, count: int, amount: int = 1) -> Dict[str, Any]:
        target = self.ACCOUNTS["miner2" if miner != "miner2" else "miner3"].address
        initial_nonce = self.get_nonce(miner)
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        transfers = [{'to': target, 'amount': amount, 'memo': f'stress_{i}'} for i in range(count)]
        results = self.batch(miner, transfers)
        
        success = self.wait_for_confirmation(miner, initial_nonce + count - 1, initial_height, timeout=120)
        
        return {
            'success': success,
            'transactions': results,
            'initial_balance': initial_balance,
            'final_balance': self.get_balance(miner),
            'count': count
        }