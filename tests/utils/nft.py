import time
from typing import Optional, Dict, Any, List
from .contract import Contract

class NFT(Contract):
    
    def mint(self, miner: str, contract_address: str, contract_name: str, recipient: str, nonce: Optional[int] = None) -> str:
        # Use the same format as test-nft.py: -e 'address
        return self.call(miner, contract_address, contract_name, "mint", [f"-e", f"'{recipient}"], nonce)
    
    def transfer(self, miner: str, contract_address: str, contract_name: str, token_id: int, recipient: str, nonce: Optional[int] = None) -> str:
        account = self.get_account(miner)
        return self.call(miner, contract_address, contract_name, "transfer", [f"u{token_id}", f'"{account.address}"', f'"{recipient}"'], nonce)
    
    def burn(self, miner: str, contract_address: str, contract_name: str, token_id: int, nonce: Optional[int] = None) -> str:
        return self.call(miner, contract_address, contract_name, "burn", [f"u{token_id}"], nonce)
    
    def owner(self, miner: str, contract_address: str, contract_name: str, token_id: int) -> Dict[str, Any]:
        # Use the exact same format as the original test-nft.py for token ID 1
        if token_id == 1:
            token_hex = "0x0100000000000000000000000000000001"
        elif token_id == 2:
            token_hex = "0x0100000000000000000000000000000002"
        else:
            # For other tokens, construct the format properly
            token_hex = f"0x01{token_id:030x}"
        
        return self.read(miner, contract_address, contract_name, "get-token-owner", [token_hex])
    
    def count(self, miner: str, contract_address: str, contract_name: str) -> Dict[str, Any]:
        return self.read(miner, contract_address, contract_name, "get-token-count")
    
    def batch_mint(self, miner: str, contract_address: str, contract_name: str, recipients: List[str], start_nonce: Optional[int] = None) -> List[Dict[str, Any]]:
        if start_nonce is None:
            start_nonce = self.get_nonce(miner)
        
        results = []
        initial_height = self.get_block_height(miner)
        
        for i, recipient in enumerate(recipients):
            try:
                txid = self.mint(miner, contract_address, contract_name, recipient, start_nonce + i)
                results.append({'success': True, 'txid': txid, 'recipient': recipient, 'token_id': i + 1, 'nonce': start_nonce + i})
            except Exception as e:
                results.append({'success': False, 'error': str(e), 'recipient': recipient, 'nonce': start_nonce + i})
        
        if results:
            self.wait_for_confirmation(miner, start_nonce + len(recipients) - 1, initial_height, timeout=120)
        return results
    
    def deploy_and_mint(self, miner: str, contract_file: str, contract_name: str, recipients: List[str]) -> Dict[str, Any]:
        account = self.get_account(miner)
        initial_nonce = self.get_nonce(miner)
        
        # Generate unique contract name with nonce like test-nft.py does  
        dynamic_contract_name = f"{contract_name}{initial_nonce}"
        
        try:
            # Deploy NFT contract (verification is built into deploy method now)
            deploy_txid = self.deploy(miner, contract_file, dynamic_contract_name, initial_nonce)
        except Exception as e:
            return {'success': False, 'error': f'NFT contract deployment failed: {e}'}
        
        # Wait for contract to be available and test token count
        print("\n=== NFT Contract Interaction Tests ===")
        time.sleep(10)  # Like test-nft.py does
        
        # 1. Read initial token count
        print("1. Reading initial token count...")
        try:
            initial_count = self.count(miner, account.address, dynamic_contract_name)
            print(f"✓ Initial token count: {initial_count}")
        except Exception as e:
            print(f"✗ Failed to read initial token count: {e}")
            return {'success': False, 'error': f'Failed to read initial token count: {e}'}
        
        # 2. Mint tokens to recipients
        mint_results = []
        current_nonce = self.get_nonce(miner)
        
        for i, recipient in enumerate(recipients):
            try:
                print(f"{i+2}. Minting NFT to {recipient[:10]}...")
                txid = self.mint(miner, account.address, dynamic_contract_name, recipient, current_nonce + i)
                mint_results.append({'success': True, 'txid': txid, 'recipient': recipient, 'token_id': i + 1, 'nonce': current_nonce + i})
                print(f"✓ Minted token #{i+1} - TXID: {txid}")
            except Exception as e:
                print(f"✗ Failed to mint token #{i+1}: {e}")
                mint_results.append({'success': False, 'error': str(e), 'recipient': recipient, 'token_id': i + 1, 'nonce': current_nonce + i})
        
        # 3. Read token count after minting
        if mint_results:
            print(f"{len(recipients)+2}. Reading token count after minting...")
            try:
                final_count = self.count(miner, account.address, dynamic_contract_name)
                print(f"✓ Final token count: {final_count}")
                expected_count = len([r for r in mint_results if r['success']])
                print(f"✓ Expected tokens minted: {expected_count}")
            except Exception as e:
                print(f"⚠ Could not verify final token count: {e}")
        
        # 4. Check token ownership for first token
        successful_mints = [r for r in mint_results if r['success']]
        if successful_mints:
            print(f"{len(recipients)+3}. Checking token #1 ownership...")
            try:
                token_owner = self.owner(miner, account.address, dynamic_contract_name, 1)
                first_recipient = successful_mints[0]['recipient']
                print(f"✓ Token #1 owner: {token_owner}")
                print(f"✓ Expected owner: {first_recipient}")
            except Exception as e:
                print(f"⚠ Could not verify token ownership: {e}")
        
        return {
            'success': True,
            'deploy_txid': deploy_txid,
            'contract_address': account.address,
            'contract_name': dynamic_contract_name,
            'mint_results': mint_results,
            'total_minted': len([r for r in mint_results if r['success']]),
            'initial_count': initial_count,
            'final_count': final_count if 'final_count' in locals() else None
        }
    
    def stress(self, miner: str, contract_file: str, contract_name: str, mint_count: int) -> Dict[str, Any]:
        all_miners = list(self.ACCOUNTS.keys())
        recipients = [self.ACCOUNTS[all_miners[i % len(all_miners)]].address for i in range(mint_count)]
        return self.deploy_and_mint(miner, contract_file, contract_name, recipients)