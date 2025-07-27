#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors

def create_size_limits_recipe():
    return Recipe(
        name="Find Exact Stacks Size Limits",
        description="Binary search to find exact contract deployment size limits",
        setup=True,
        cleanup=True,
        steps=[
            # Test small contracts (should all pass)
            Step(
                name="Deploy 8KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-8kb.clar",
                    "contract_name": "contract-8kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 40KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-40kb.clar",
                    "contract_name": "contract-40kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 80KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-80kb.clar",
                    "contract_name": "contract-80kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 120KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-120kb.clar",
                    "contract_name": "contract-120kb"
                },
                wait=True,
                on_error="continue"
            ),
            
            # Test medium contracts (start looking for limits)
            Step(
                name="Deploy 200KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner2",
                    "contract_file": "contracts/contract-200kb.clar",
                    "contract_name": "contract-200kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 400KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner2",
                    "contract_file": "contracts/contract-400kb.clar",
                    "contract_name": "contract-400kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 600KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner2",
                    "contract_file": "contracts/contract-600kb.clar",
                    "contract_name": "contract-600kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 800KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner2",
                    "contract_file": "contracts/contract-800kb.clar",
                    "contract_name": "contract-800kb"
                },
                wait=True,
                on_error="continue"
            ),
            
            # Test large contracts (likely to fail somewhere here)
            Step(
                name="Deploy 1000KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner3",
                    "contract_file": "contracts/contract-1000kb.clar",
                    "contract_name": "contract-1000kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 1200KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner3",
                    "contract_file": "contracts/contract-1200kb.clar",
                    "contract_name": "contract-1200kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 1500KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner3",
                    "contract_file": "contracts/contract-1500kb.clar",
                    "contract_name": "contract-1500kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 2000KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-2000kb.clar",
                    "contract_name": "contract-2000kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 2250KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-2250kb.clar",
                    "contract_name": "contract-2250kb"
                },
                wait=True,
                on_error="continue"
            ),            
            # Test working contracts
            Step(
                name="Test 8KB contract function",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "contract-8kb",
                    "function_name": "calc-function-0001",
                    "args": ["u12345"]
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Test 120KB contract function",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "contract-120kb",
                    "function_name": "calc-function-0500",
                    "args": ["u54321"]
                },
                wait=True,
                on_error="continue"
            )
        ]
    )

def main():
    """Execute the size limits test recipe"""
    print("=" * 80)
    print(f"{Colors.format_header('FIND EXACT STACKS SIZE LIMITS')}")
    print("=" * 80)
    
    runner = Runner()
    recipe = create_size_limits_recipe()
    result = runner.run(recipe)
    
    print(f"\nRecipe: {Colors.format_info(result['name'])}")
    print(f"Overall Success: {Colors.format_success('✓ PASSED') if result['success'] else Colors.format_error('✗ FAILED')}")
    duration_text = f"{result.get('duration', 0):.2f} seconds"
    print(f"Duration: {Colors.format_dim(duration_text)}")
    
    print(f"\n{Colors.format_header('SIZE LIMIT ANALYSIS:')}")
    
    for i, step in enumerate(result.get('steps', []), 1):
        status = Colors.format_success('✓') if step.get('success', False) else Colors.format_error('✗')
        print(f"  {i}. {step.get('name', 'Unknown')}: {status}")
        
        if not step.get('success', False) and 'error' in step:
            error_preview = step['error'][:100] + "..." if len(step['error']) > 100 else step['error']
            print(f"     {Colors.format_error(error_preview)}")

if __name__ == "__main__":
    main()