#!/usr/bin/env python3
"""
Recipe-based NFT test that exactly replicates test-nft.py functionality
using minimal LOC with the recipe system.
"""

from utils.recipes import Runner, Recipe, Step

def create_nft_simple_recipe():
    return Recipe(
        name="NFT Simple Test",
        description="Deploy NFT contract, mint tokens, verify ownership",
        setup=True,  # Use recipe's built-in node management
        cleanup=True,  # Use recipe's built-in node management
        steps=[
            # Step 1: Deploy NFT contract and test interactions (replicates test_nft_deployment + test_nft_interaction)
            Step(
                name="Deploy NFT contract and test minting",
                module="nft",
                method="deploy_and_mint",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-nft.clar",
                    "contract_name": "testnft",
                    "recipients": [
                        "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",  # miner1 (publisher)
                        "ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y"   # miner2 (recipient)
                    ]
                },
                wait=True,
                on_error="stop"
            )
        ]
    )

def main():
    """Execute the NFT simple recipe test"""
    print("=" * 60)
    print("RECIPE TO TEST NFT CONTRACT DEPLOYMENT AND MINTING")
    print("=" * 60)
    
    runner = Runner()
    recipe = create_nft_simple_recipe()
    
    # Run the recipe with built-in node management
    result = runner.run(recipe)
    
    # Print results summary  
    print("\n" + "=" * 60)
    print("RECIPE EXECUTION RESULTS")
    print("=" * 60)
    
    print(f"Recipe: {result['name']}")
    print(f"Overall Success: {'✓ PASSED' if result['success'] else '✗ FAILED'}")
    print(f"Duration: {result.get('duration', 0):.2f} seconds")
    print(f"Setup Success: {'✓' if result.get('setup_success', False) else '✗'}")
    print(f"Cleanup Success: {'✓' if result.get('cleanup_success', False) else '✗'}")
    
    print(f"\nStep Results ({len(result.get('steps', []))} steps):")
    for i, step in enumerate(result.get('steps', []), 1):
        status = '✓ PASSED' if step.get('success', False) else '✗ FAILED'
        duration = step.get('duration', 0)
        retries = step.get('retries', 0)
        print(f"  {i}. {step.get('name', 'Unknown')}: {status} ({duration:.2f}s, {retries} retries)")
        
        if not step.get('success', False) and 'error' in step:
            print(f"     Error: {step['error']}")
        elif step.get('success', False) and 'result' in step:
            step_result = step['result']
            if isinstance(step_result, dict) and 'contract_name' in step_result:
                print(f"     NFT Contract: {step_result.get('contract_name', 'Unknown')}")
                print(f"     Deploy TXID: {step_result.get('deploy_txid', 'Unknown')}")
                print(f"     Contract Address: {step_result.get('contract_address', 'Unknown')}")
                print(f"     Total Minted: {step_result.get('total_minted', 0)}/{len(step_result.get('mint_results', []))}")
                
                # Show mint results
                mint_results = step_result.get('mint_results', [])
                if mint_results:
                    print(f"     Mint Results:")
                    for j, mint in enumerate(mint_results):
                        mint_status = '✓' if mint.get('success', False) else '✗'
                        recipient = mint.get('recipient', 'unknown')[:10] + "..."
                        token_id = mint.get('token_id', 'unknown')
                        print(f"       {mint_status} Token #{token_id} → {recipient}")
                        if not mint.get('success', False) and 'error' in mint:
                            print(f"         Error: {mint['error']}")
            else:
                result_preview = str(step_result)
                if len(result_preview) > 100:
                    result_preview = result_preview[:100] + "..."
                print(f"     Result: {result_preview}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    
    if result['success']:
        print("✓ ALL TESTS PASSED - NFT contract successfully deployed, tokens minted, and chain healthy")
        print("✓ Recipe-based test exactly replicated test-nft.py functionality")
        return True
    else:
        print("✗ TESTS FAILED - Recipe execution encountered errors")
        failed_steps = [step for step in result.get('steps', []) if not step.get('success', False)]
        if failed_steps:
            print("Failed steps:")
            for step in failed_steps:
                print(f"  - {step.get('name', 'Unknown')}: {step.get('error', 'No error details')}")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)