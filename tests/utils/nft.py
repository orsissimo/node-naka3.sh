from typing import Optional, Dict, Any
from .contract import Contract

class NFT(Contract):
    """SIP-009 compliant NFT standard methods"""
    
    def get_owner(self, miner: str, contract_address: str, contract_name: str, token_id: int) -> Dict[str, Any]:
        """SIP-009 standard: get-owner function"""
        # Convert token_id to proper Clarity uint format (32 hex chars)
        clarity_token_id = f"0x01{token_id:031x}"
        return self.read(miner, contract_address, contract_name, "get-owner", [clarity_token_id])
    
    def transfer(self, miner: str, contract_address: str, contract_name: str, token_id: int, sender: str, recipient: str, nonce: Optional[int] = None) -> str:
        """SIP-009 standard: transfer function"""
        return self.call(miner, contract_address, contract_name, "transfer", [f"u{token_id}", f'"{sender}"', f'"{recipient}"'], nonce)
    
    def get_last_token_id(self, miner: str, contract_address: str, contract_name: str) -> Dict[str, Any]:
        """SIP-009 standard: get-last-token-id function"""
        return self.read(miner, contract_address, contract_name, "get-last-token-id")
    
    def get_token_uri(self, miner: str, contract_address: str, contract_name: str, token_id: int) -> Dict[str, Any]:
        """SIP-009 standard: get-token-uri function"""
        # Convert token_id to proper Clarity uint format (32 hex chars)
        clarity_token_id = f"0x01{token_id:031x}"
        return self.read(miner, contract_address, contract_name, "get-token-uri", [clarity_token_id])
