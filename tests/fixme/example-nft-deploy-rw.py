#!/usr/bin/env python3

import os
import sys
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_block_height, wait_for_confirmation
from utils.config import AccountManager, Miner
from utils.miners import MinerManager
from utils.logger import logger
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.stacks_core_api import StacksCoreAPIWrapper

def main():
    """Execute the NFT contract deployment and interaction test"""
    logger.dim('=' * 60)
    logger.header('CYBERPUNK NFT CONTRACT DEPLOYMENT AND INTERACTIONS TEST')
    logger.dim('=' * 60)
    
    # Raw minimal setup
    miners = MinerManager()
    account = AccountManager.get(Miner.MINER1)
    api = StacksCoreAPIWrapper(base_url=account.api_url)
    cli = BlockstackCLIWrapper()
    
    try:
        # Start miners
        logger.stacks('Starting miners...')
        if not miners.snapshot_restore_auto():
            raise RuntimeError("Failed to start miners")
        
        # Step 1: Deploy cyberpunk NFT contract
        logger.header('Step 1: Deploy cyberpunk NFT contract')
        logger.standard('Contract', 'cyberpunk2140a')
        logger.standard('File', 'contracts/cyberpunk2140a.clar')
        
        account_info = api.get_account_info(account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)
        
        tx_hex = cli.publish_contract(account.private_key, 50000, initial_nonce, "cyberpunk2140a", 
                                    os.path.join(os.path.dirname(__file__), "..", "contracts/cyberpunk2140a.clar"))
        deploy_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        logger.standard('Contract deployed', deploy_txid)
        logger.success('Contract deployed successfully')
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract deployment confirmation timeout")
        logger.success('Contract cyberpunk2140a deployment confirmed!')
        
        # Step 2: Read max token count  
        logger.header('Step 2: Read max token count')
        max_tokens = api.call_read_only_function(account.address, "cyberpunk2140a", "get-last-token-id", account.address, [])
        logger.success('Read-only call successful')
        logger.standard('Response', json.dumps(max_tokens, indent=2))
        
        # Step 3: Read mint price
        logger.header('Step 3: Read mint price')
        mint_price = api.call_read_only_function(account.address, "cyberpunk2140a", "get-mint-price", account.address, [])
        logger.success('Read-only call successful')
        logger.standard('Response', json.dumps(mint_price, indent=2))
        
        # Step 4: Read available count
        logger.header('Step 4: Read available count')
        available_count = api.call_read_only_function(account.address, "cyberpunk2140a", "get-available-count", account.address, [])
        logger.success('Read-only call successful')
        logger.standard('Response', json.dumps(available_count, indent=2))
        
        # Step 5: Read initial minted count
        logger.header('Step 5: Read initial minted count')
        initial_minted = api.call_read_only_function(account.address, "cyberpunk2140a", "get-minted-count", account.address, [])
        logger.success('Read-only call successful')
        logger.standard('Response', json.dumps(initial_minted, indent=2))
        
        # Step 6: Read collection attribute
        logger.header('Step 6: Read collection attribute')
        collection_attr = api.call_read_only_function(account.address, "cyberpunk2140a", "get-collection-attribute", account.address, [])
        logger.success('Read-only call successful')
        logger.standard('Response', json.dumps(collection_attr, indent=2))
        
        # Step 7: Check if collection data is frozen
        logger.header('Step 7: Check collection data frozen')
        data_frozen = api.call_read_only_function(account.address, "cyberpunk2140a", "is-collection-data-frozen", account.address, [])
        logger.success('Read-only call successful')
        logger.standard('Response', json.dumps(data_frozen, indent=2))
        
        # Step 8: Set token URI
        logger.header('Step 8: Set token URI')
        account_info = api.get_account_info(account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)
        
        tx_hex = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "set-token-uri", 
                                 ['"https://cyberpunk2140.com/metadata/{id}.json"'])
        set_uri_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        logger.standard('Contract call submitted', set_uri_txid)
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        logger.success('set-token-uri call confirmed!')
        
        # Step 9: Set collection attribute
        logger.header('Step 9: Set collection attribute')
        account_info = api.get_account_info(account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)
        
        tx_hex = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "set-collection-attribute", 
                                 ['u"Cyberpunk 2140 NFT Collection"'])
        set_attr_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        logger.standard('Contract call submitted', set_attr_txid)
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        logger.success('set-collection-attribute call confirmed!')
        
        # Step 10: Set collection icon data
        logger.header('Step 10: Set collection icon data')
        account_info = api.get_account_info(account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)
        
        tx_hex = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "set-collection-icon-data", 
                                 ["0x89504e470d0a1a0a0000000d49484452"])
        set_icon_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        logger.standard('Contract call submitted', set_icon_txid)
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        logger.success('set-collection-icon-data call confirmed!')
        
        # Step 11: Set tokens data
        logger.header('Step 11: Set tokens data')
        account_info = api.get_account_info(account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)
        
        tx_hex = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "set-tokens", 
                              ['(list {id: u1, data: 0x89504e470d0a1a0a, attribute: u"First Token"} {id: u2, data: 0x89504e470d0a1a0b, attribute: u"Second Token"})'])
        set_tokens_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        logger.standard('Contract call submitted', set_tokens_txid)
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        logger.success('set-tokens call confirmed!')
        
        # Step 12: Mint cyberpunk NFT
        logger.header('Step 12: Mint cyberpunk NFT')
        account_info = api.get_account_info(account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)
        
        tx_hex = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "mint", [])
        mint_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        logger.standard('Contract call submitted', mint_txid)
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        logger.success('mint call confirmed!')
        
        # Step 13: Read minted count after mint
        logger.header('Step 13: Read minted count after mint')
        final_minted = api.call_read_only_function(account.address, "cyberpunk2140a", "get-minted-count", account.address, [])
        logger.success('Read-only call successful')
        logger.standard('Response', json.dumps(final_minted, indent=2))
        
        # Step 14: Read collection attribute after setting
        logger.header('Step 14: Read collection attribute after setting')
        final_collection_attr = api.call_read_only_function(account.address, "cyberpunk2140a", "get-collection-attribute", account.address, [])
        logger.success('Read-only call successful')
        logger.standard('Response', json.dumps(final_collection_attr, indent=2))
        
        # Final summary
        logger.dim('=' * 60)
        logger.header('FINAL RESULT')
        logger.dim('=' * 60)
        
        logger.standard('Deploy TXID', deploy_txid)
        logger.standard('Set URI TXID', set_uri_txid)
        logger.standard('Set Attribute TXID', set_attr_txid)
        logger.standard('Set Icon TXID', set_icon_txid)
        logger.standard('Set Tokens TXID', set_tokens_txid)
        logger.standard('Mint TXID', mint_txid)
        
        return True
        
    except Exception as e:
        logger.error(f'TEST FAILED: {str(e)}')
        return False
        
    finally:
        # Cleanup
        logger.header('Cleaning up...')
        miners.stop()
        miners.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)