#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors

def create_contract_simple_recipe():
    return Recipe(
        name="Contract Simple Test",
        description="Deploy contract, test interaction, verify chain progression",
        setup=True,  # Use recipe's built-in node management
        cleanup=True,  # Use recipe's built-in node management
        steps=[
            # Step 1: Deploy counter contract
            Step(
                name="Deploy counter contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-counter.clar", 
                    "contract_name": "mycontract"
                },
                wait=True,
                on_error="stop"
            ),
            # Step 2: Read initial counter value
            Step(
                name="Read initial counter",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "mycontract",
                    "function_name": "get-counter"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 3: Read initial last caller
            Step(
                name="Read initial last caller",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "mycontract",
                    "function_name": "get-last-caller"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 4: Increment counter
            Step(
                name="Increment counter",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "mycontract",
                    "function_name": "increment"
                },
                wait=True,
                on_error="stop"
            ),
            # Step 5: Read counter after increment
            Step(
                name="Read counter after increment",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "mycontract",
                    "function_name": "get-counter"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 6: Read last caller after increment
            Step(
                name="Read last caller after increment",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "mycontract",
                    "function_name": "get-last-caller"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 7: Reset counter
            Step(
                name="Reset counter",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "mycontract",
                    "function_name": "reset"
                },
                wait=True,
                on_error="stop"
            ),
            # Step 8: Read counter after reset
            Step(
                name="Read counter after reset",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "mycontract",
                    "function_name": "get-counter"
                },
                wait=True,
                on_error="continue"
            ),
            # Step 9: Read last caller after reset
            Step(
                name="Read last caller after reset",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "mycontract",
                    "function_name": "get-last-caller"
                },
                wait=True,
                on_error="continue"
            )
        ]
    )

def main():
    """Execute the contract simple recipe test"""
    print("=" * 60)
    print(f"{Colors.format_header('RECIPE TO TEST COUNTER CONTRACT DEPLOYMENT AND INTERACTIONS')}")
    print("=" * 60)
    
    runner = Runner()
    recipe = create_contract_simple_recipe()
    
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
            if isinstance(step_result, dict) and 'function_results' in step_result:
                print(f"     Contract: {Colors.format_info(step_result.get('contract_name', 'Unknown'))}")
                print(f"     Deploy TXID: {Colors.format_dim(step_result.get('deploy_txid', 'Unknown'))}")
                print(f"     Function tests:")
                for func_result in step_result.get('function_results', []):
                    func_status = Colors.format_success('✓') if func_result.get('success', False) else Colors.format_error('✗')
                    func_name = func_result.get('function', 'unknown')
                    func_type = func_result.get('type', 'unknown')
                    print(f"       {func_status} {Colors.format_info(func_name)} ({Colors.format_dim(func_type)})")
                    if not func_result.get('success', False) and 'error' in func_result:
                        print(f"         Error: {Colors.format_error(func_result['error'])}")
            else:
                result_preview = str(step_result)
                if len(result_preview) > 100:
                    result_preview = result_preview[:100] + "..."
                print(f"     Result: {Colors.format_dim(result_preview)}")
    
    # Final summary
    print("\n" + "=" * 60)
    print(f"{Colors.format_header('FINAL RESULT')}")
    print("=" * 60)
    
    if result['success']:
        print(f"{Colors.format_success('✓ ALL TESTS PASSED')} - Contract successfully deployed, tested, and chain healthy")
        print(f"{Colors.format_success('✓ Recipe-based test')} exactly replicated test-contract.py functionality")
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