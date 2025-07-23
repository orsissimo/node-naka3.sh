import time
import json
from typing import Optional, Dict, Any
from .base import StacksTestBase

class Transaction(StacksTestBase):
    
    def get_balance_for_address(self, miner: str, address: str) -> int:
        """Get balance for any address using the miner's API"""
        account = self.get_account(miner)
        response = self.api_call(account, f"/v2/accounts/{address}")
        response.raise_for_status()
        account_info = response.json()
        balance_hex = account_info.get('balance', '0x0')
        return int(balance_hex, 16) if balance_hex.startswith('0x') else int(balance_hex)
    
    def transfer(self, from_miner: str, to_address: str, amount: int, 
                memo: Optional[str] = None, nonce: Optional[int] = None) -> str:
        account = self.get_account(from_miner)
        
        # Get initial state for verification (like test-transaction.py does)
        initial_nonce = self.get_nonce(from_miner) if nonce is None else nonce
        initial_sender_balance = self.get_balance(from_miner)
        initial_recipient_balance = self.get_balance_for_address(from_miner, to_address)
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
        
        # Custom verification that includes recipient balance tracking
        verification = self.verify_transfer_transaction(from_miner, to_address, txid, initial_nonce, 
                                                      initial_sender_balance, initial_recipient_balance, initial_height)
        if not verification['success']:
            raise RuntimeError(f"Transfer verification failed: {verification['error']}")
        
        return txid
    
    def verify_transfer_transaction(self, from_miner: str, to_address: str, txid: str, 
                                  initial_nonce: int, initial_sender_balance: int, 
                                  initial_recipient_balance: int, initial_height: int) -> Dict[str, Any]:
        """Custom transfer verification that tracks both sender and recipient balances"""
        account = self.get_account(from_miner)
        
        # Wait for confirmation first
        print("Waiting for confirmation...")
        if not self.wait_for_confirmation(from_miner, initial_nonce, initial_height):
            return {
                'success': False,
                'error': 'Transaction confirmation timeout',
                'txid': txid
            }
        
        try:
            # Get current state for both sender and recipient
            current_nonce = self.get_nonce(from_miner)
            current_sender_balance = self.get_balance(from_miner)
            current_recipient_balance = self.get_balance_for_address(from_miner, to_address)
            current_height = self.get_block_height(from_miner)
            
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
            
            # Display confirmation like test-transaction.py
            print(f"\n✓ Transaction confirmed!")
            print(f"Sender balance: {initial_sender_balance} → {current_sender_balance}")
            print(f"Recipient balance: {initial_recipient_balance} → {current_recipient_balance}")
            print(f"Nonce: {initial_nonce} → {current_nonce}")
            print(f"Block: {initial_height} → {current_height}")
            
            if tx_data:
                print(f"\n=== TRANSACTION SUMMARY ===")
                print(f"  Status: {tx_data.get('tx_status', 'unknown')}")
                print(f"  Type: {tx_data.get('tx_type', 'unknown')}")
                print(f"  Fee: {tx_data.get('fee_rate', 'unknown')}")
                
                if 'token_transfer' in tx_data:
                    tt = tx_data['token_transfer']
                    print(f"  Recipient: {tt.get('recipient_address', 'unknown')}")
                    print(f"  Amount: {tt.get('amount', 'unknown')}")
                    print(f"  Memo: {tt.get('memo', 'none')}")
            
            return {
                'success': True,
                'txid': txid,
                'nonce_change': current_nonce - initial_nonce,
                'sender_balance_change': current_sender_balance - initial_sender_balance,
                'recipient_balance_change': current_recipient_balance - initial_recipient_balance,
                'height_change': current_height - initial_height,
                'transaction_data': tx_data
            }
            
        except Exception as e:
            print(f"✗ Transfer verification failed: {e}")
            return {
                'success': False,
                'error': f'Transfer verification failed: {e}',
                'txid': txid
            }
    
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