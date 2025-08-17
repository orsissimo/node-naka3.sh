#!/usr/bin/env python3

import os
import sys
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_api, get_cli, submit_tx, get_nonce, get_block_height, wait_for_confirmation
from utils.config import AccountManager, MinerName
from utils.miners import MinerManager
from utils.logger import Colors

def main():
    """Execute the NFT contract deployment and interaction test"""
    print(f"{Colors.format_dim('=' * 60)}")
    print(f"{Colors.format_header('CYBERPUNK NFT CONTRACT DEPLOYMENT AND INTERACTIONS TEST')}")
    print(f"{Colors.format_dim('=' * 60)}")
    
    # Raw minimal setup
    miners = MinerManager()
    api = get_api(MinerName.MINER1)
    cli = get_cli()
    account = AccountManager.get(MinerName.MINER1)
    
    try:
        # Start the node
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not miners.snapshot_restore("auto"):
            raise RuntimeError("Failed to start miners")
        
        # Step 1: Deploy cyberpunk NFT contract
        print(f"\n{Colors.format_header('Step 1: Deploy cyberpunk NFT contract')}")
        print(f"{Colors.format_info('Contract')}: {Colors.format_dim('cyberpunk2140a')}")
        print(f"{Colors.format_info('File')}: {Colors.format_dim('contracts/cyberpunk2140a.clar')}")
        
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        cmd = cli.publish_contract(account.private_key, 50000, initial_nonce, "cyberpunk2140a", 
                                 os.path.join(os.path.dirname(__file__), "..", "contracts/cyberpunk2140a.clar"))
        deploy_txid = submit_tx(api, cmd)
        print(f"{Colors.format_success('Contract deployed')}: {Colors.format_info(deploy_txid)}")
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract deployment confirmation timeout")
        print(f"{Colors.format_success('Contract cyberpunk2140a deployment confirmed!')}")
        
        # Step 2: Read max token count  
        print(f"\n{Colors.format_header('Step 2: Read max token count')}")
        max_tokens = api.call_read_only_function(account.address, "cyberpunk2140a", "get-last-token-id", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(max_tokens, indent=2))}")
        
        # Step 3: Read mint price
        print(f"\n{Colors.format_header('Step 3: Read mint price')}")
        mint_price = api.call_read_only_function(account.address, "cyberpunk2140a", "get-mint-price", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(mint_price, indent=2))}")
        
        # Step 4: Read available count
        print(f"\n{Colors.format_header('Step 4: Read available count')}")
        available_count = api.call_read_only_function(account.address, "cyberpunk2140a", "get-available-count", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(available_count, indent=2))}")
        
        # Step 5: Read initial minted count
        print(f"\n{Colors.format_header('Step 5: Read initial minted count')}")
        initial_minted = api.call_read_only_function(account.address, "cyberpunk2140a", "get-minted-count", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(initial_minted, indent=2))}")
        
        # Step 6: Read collection attribute
        print(f"\n{Colors.format_header('Step 6: Read collection attribute')}")
        collection_attr = api.call_read_only_function(account.address, "cyberpunk2140a", "get-collection-attribute", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(collection_attr, indent=2))}")
        
        # Step 7: Check if collection data is frozen
        print(f"\n{Colors.format_header('Step 7: Check collection data frozen')}")
        data_frozen = api.call_read_only_function(account.address, "cyberpunk2140a", "is-collection-data-frozen", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(data_frozen, indent=2))}")
        
        # Step 8: Set token URI
        print(f"\n{Colors.format_header('Step 8: Set token URI')}")
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        cmd = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "set-token-uri", 
                              ['"https://cyberpunk2140.com/metadata/{id}.json"'])
        set_uri_txid = submit_tx(api, cmd)
        print(f"{Colors.format_success('Contract call submitted')}: {Colors.format_info(set_uri_txid)}")
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        print(f"{Colors.format_success('set-token-uri call confirmed!')}")
        
        # Step 9: Set collection attribute
        print(f"\n{Colors.format_header('Step 9: Set collection attribute')}")
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        cmd = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "set-collection-attribute", 
                              ['u"Cyberpunk 2140 NFT Collection"'])
        set_attr_txid = submit_tx(api, cmd)
        print(f"{Colors.format_success('Contract call submitted')}: {Colors.format_info(set_attr_txid)}")
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        print(f"{Colors.format_success('set-collection-attribute call confirmed!')}")
        
        # Step 10: Set collection icon data
        print(f"\n{Colors.format_header('Step 10: Set collection icon data')}")
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        cmd = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "set-collection-icon-data", 
                              ["0x89504e470d0a1a0a0000000d49484452"])
        set_icon_txid = submit_tx(api, cmd)
        print(f"{Colors.format_success('Contract call submitted')}: {Colors.format_info(set_icon_txid)}")
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        print(f"{Colors.format_success('set-collection-icon-data call confirmed!')}")
        
        # Step 11: Set tokens data
        print(f"\n{Colors.format_header('Step 11: Set tokens data')}")
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        cmd = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "set-tokens", 
                              ['(list {id: u1, data: 0x89504e470d0a1a0a, attribute: u"First Token"} {id: u2, data: 0x89504e470d0a1a0b, attribute: u"Second Token"})'])
        set_tokens_txid = submit_tx(api, cmd)
        print(f"{Colors.format_success('Contract call submitted')}: {Colors.format_info(set_tokens_txid)}")
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        print(f"{Colors.format_success('set-tokens call confirmed!')}")
        
        # Step 12: Mint cyberpunk NFT
        print(f"\n{Colors.format_header('Step 12: Mint cyberpunk NFT')}")
        initial_nonce = get_nonce(api, account.address)
        initial_height = get_block_height(api)
        
        cmd = cli.call_contract(account.private_key, 5000, initial_nonce, account.address, "cyberpunk2140a", "mint", [])
        mint_txid = submit_tx(api, cmd)
        print(f"{Colors.format_success('Contract call submitted')}: {Colors.format_info(mint_txid)}")
        
        if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
            raise RuntimeError("Contract call confirmation timeout")
        print(f"{Colors.format_success('mint call confirmed!')}")
        
        # Step 13: Read minted count after mint
        print(f"\n{Colors.format_header('Step 13: Read minted count after mint')}")
        final_minted = api.call_read_only_function(account.address, "cyberpunk2140a", "get-minted-count", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(final_minted, indent=2))}")
        
        # Step 14: Read collection attribute after setting
        print(f"\n{Colors.format_header('Step 14: Read collection attribute after setting')}")
        final_collection_attr = api.call_read_only_function(account.address, "cyberpunk2140a", "get-collection-attribute", account.address, [])
        print(f"{Colors.format_success('Read-only call successful')}")
        print(f"{Colors.format_info('Response')}: {Colors.format_dim(json.dumps(final_collection_attr, indent=2))}")
        
        # Final summary
        print(f"\n{Colors.format_dim('=' * 60)}")
        print(f"{Colors.format_header('FINAL RESULT')}")
        print(f"{Colors.format_dim('=' * 60)}")
        
        print(f"{Colors.format_info('Deploy TXID')}: {Colors.format_dim(deploy_txid)}")
        print(f"{Colors.format_info('Set URI TXID')}: {Colors.format_dim(set_uri_txid)}")
        print(f"{Colors.format_info('Set Attribute TXID')}: {Colors.format_dim(set_attr_txid)}")
        print(f"{Colors.format_info('Set Icon TXID')}: {Colors.format_dim(set_icon_txid)}")
        print(f"{Colors.format_info('Set Tokens TXID')}: {Colors.format_dim(set_tokens_txid)}")
        print(f"{Colors.format_info('Mint TXID')}: {Colors.format_dim(mint_txid)}")
        
        return True
        
    except Exception as e:
        print(f"\n{Colors.format_error('✗ TEST FAILED')}: {Colors.format_error(str(e))}")
        return False
        
    finally:
        # Cleanup
        print(f"\n{Colors.format_header('Cleaning up...')}")
        miners.stop()
        miners.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)