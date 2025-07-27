#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step

def create_cyberpunk_nft_recipe():
    return Recipe(
        name="Cyberpunk NFT Test",
        description="Deploy cyberpunk NFT contract, mint tokens, test interactions",
        setup=True,  # Use recipe's built-in node management
        cleanup=True,  # Use recipe's built-in node management
        steps=[
            # Step 1: Deploy cyberpunk NFT contract
            Step(
                name="Deploy cyberpunk NFT contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/cyberpunk2140a.clar",
                    "contract_name": "cyberpunk2140a"
                },
                wait=True,
                on_error="stop"
            ),
            # Step 2: Read max token count
            Step(
                name="Read max token count",
                module="contract", 
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-last-token-id"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 3: Read mint price
            Step(
                name="Read mint price",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-mint-price"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 4: Read available count
            Step(
                name="Read available count",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-available-count"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 5: Read minted count
            Step(
                name="Read initial minted count",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-minted-count"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 6: Read user balance before mint
            Step(
                name="Read user balance before mint",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-balance",
                    "args": ["'STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 7: Read collection attributes
            Step(
                name="Read collection attribute",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-collection-attribute"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 8: Check if collection data is frozen
            Step(
                name="Check collection data frozen",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "is-collection-data-frozen"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 9: Mint cyberpunk NFT
            Step(
                name="Mint cyberpunk NFT",
                module="contract",
                method="call", 
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "mint"
                },
                wait=True,
                on_error="stop"
            ),
            # Step 10: Read minted count after mint
            Step(
                name="Read minted count after mint",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-minted-count"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 11: Read user balance after mint
            Step(
                name="Read user balance after mint",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-balance",
                    "args": ["'STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 12: Read minted IDs list
            Step(
                name="Read minted IDs list",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-minted-ids"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 13: Read partner percent
            Step(
                name="Read partner percent",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-partner-percent"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 14: Read royalty percent
            Step(
                name="Read royalty percent",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-royalty-percent"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 15: Read partner address
            Step(
                name="Read partner address",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-partner-address"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 16: Read team address
            Step(
                name="Read team address",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "get-team-address"
                },
                wait=True,
                on_error="continue"
            )
        ]
    )

def main():
    """Execute the cyberpunk NFT recipe test"""
    print("=" * 60)
    print("RECIPE TO TEST CYBERPUNK NFT CONTRACT")
    print("=" * 60)
    
    runner = Runner()
    recipe = create_cyberpunk_nft_recipe()
    
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
            result_preview = str(step_result)
            if len(result_preview) > 100:
                result_preview = result_preview[:100] + "..."
            print(f"     Result: {result_preview}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    
    if result['success']:
        print("✓ ALL TESTS PASSED - Cyberpunk NFT successfully deployed, minted, and tested")
        print("✓ Recipe-based test using direct contract calls for custom functionality")
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