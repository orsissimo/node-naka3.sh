#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors

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
            # Step 6: Read collection attributes
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
            # Step 7: Check if collection data is frozen
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
            # Step 8: Set token URI (write function)
            Step(
                name="Set token URI",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "set-token-uri",
                    "args": ["\"https://cyberpunk2140.com/metadata/{id}.json\""]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 10: Set collection attribute (write function)
            Step(
                name="Set collection attribute",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "set-collection-attribute",
                    "args": ["u\"Cyberpunk 2140 NFT Collection\""]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 11: Set collection icon data (write function)
            Step(
                name="Set collection icon data",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "set-collection-icon-data",
                    "args": ["0x89504e470d0a1a0a0000000d49484452"]  # Sample PNG header bytes
                },
                wait=True,
                on_error="continue"
            ),
            # Step 12: Set tokens (write function)
            Step(
                name="Set tokens data",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "cyberpunk2140a",
                    "function_name": "set-tokens",
                    "args": ["(list {id: u1, data: 0x89504e470d0a1a0a, attribute: u\"First Token\"} {id: u2, data: 0x89504e470d0a1a0b, attribute: u\"Second Token\"})"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 13: Mint cyberpunk NFT
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
                on_error="continue"
            ),
            # Step 12: Read minted count after mint
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
            # Step 13: Read collection attribute after setting
            Step(
                name="Read collection attribute after setting",
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
        ]
    )

def main():
    """Execute the cyberpunk NFT recipe test"""
    print("=" * 60)
    print(f"{Colors.format_header('RECIPE TO TEST CYBERPUNK NFT CONTRACT')}")
    print("=" * 60)
    
    runner = Runner()
    recipe = create_cyberpunk_nft_recipe()
    
    # Run the recipe with built-in node management
    result = runner.run(recipe)
    
    # Print results summary  
    print("\n" + "=" * 60)
    print(f"{Colors.format_header('RECIPE EXECUTION RESULTS')}")
    print("=" * 60)
    
    print(f"Recipe: {Colors.format_info(result['name'])}")
    print(f"Overall Success: {Colors.format_success('✓ PASSED') if result['success'] else Colors.format_error('✗ FAILED')}")
    duration_text = f"{result.get('duration', 0):.2f} seconds"
    print(f"Duration: {Colors.format_dim(duration_text)}")
    print(f"Setup Success: {Colors.format_success('✓') if result.get('setup_success', False) else Colors.format_error('✗')}")
    print(f"Cleanup Success: {Colors.format_success('✓') if result.get('cleanup_success', False) else Colors.format_error('✗')}")
    
    steps_count = len(result.get('steps', []))
    print(f"\n{Colors.format_subheader(f'Step Results ({steps_count} steps)')}")
    for i, step in enumerate(result.get('steps', []), 1):
        status = Colors.format_success('✓ PASSED') if step.get('success', False) else Colors.format_error('✗ FAILED')
        duration = step.get('duration', 0)
        retries = step.get('retries', 0)
        duration_retries_text = f"{duration:.2f}s, {retries} retries"
        print(f"  {Colors.format_info(f'{i}.')} {Colors.format_dim(step.get('name', 'Unknown'))}: {status} ({Colors.format_dim(duration_retries_text)})")
        
        if not step.get('success', False) and 'error' in step:
            print(f"     Error: {Colors.format_error(step['error'])}")
        elif step.get('success', False) and 'result' in step:
            step_result = step['result']
            result_preview = str(step_result)
            if len(result_preview) > 100:
                result_preview = result_preview[:100] + "..."
            print(f"     Result: {Colors.format_dim(result_preview)}")
    
    # Final summary
    print("\n" + "=" * 60)
    print(f"{Colors.format_header('FINAL RESULT')}")
    print("=" * 60)
    
    if result['success']:
        print(f"{Colors.format_success('✓ ALL TESTS PASSED')} - Cyberpunk NFT successfully deployed, minted, and tested")
        print(f"{Colors.format_success('✓ Recipe-based test')} using direct contract calls for custom functionality")
        return True
    else:
        print(f"{Colors.format_error('✗ TESTS FAILED')} - Recipe execution encountered errors")
        failed_steps = [step for step in result.get('steps', []) if not step.get('success', False)]
        if failed_steps:
            print(f"{Colors.format_warning('Failed steps:')}")
            for step in failed_steps:
                print(f"  - {Colors.format_error(step.get('name', 'Unknown'))}: {Colors.format_error(step.get('error', 'No error details'))}")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)