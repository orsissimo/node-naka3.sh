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
                name="Deploy 16KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-16kb.clar",
                    "contract_name": "contract-16kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 24KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-24kb.clar",
                    "contract_name": "contract-24kb"
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
                name="Deploy 60KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-60kb.clar",
                    "contract_name": "contract-60kb"
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
                name="Deploy 100KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-100kb.clar",
                    "contract_name": "contract-100kb"
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
            
            # Test medium contracts
            Step(
                name="Deploy 160KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner2",
                    "contract_file": "contracts/contract-160kb.clar",
                    "contract_name": "contract-160kb"
                },
                wait=True,
                on_error="continue"
            ),
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
                name="Deploy 240KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner2",
                    "contract_file": "contracts/contract-240kb.clar",
                    "contract_name": "contract-240kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 300KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner2",
                    "contract_file": "contracts/contract-300kb.clar",
                    "contract_name": "contract-300kb"
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
                name="Deploy 500KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner2",
                    "contract_file": "contracts/contract-500kb.clar",
                    "contract_name": "contract-500kb"
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
                name="Deploy 700KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner2",
                    "contract_file": "contracts/contract-700kb.clar",
                    "contract_name": "contract-700kb"
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
            Step(
                name="Deploy 900KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner3",
                    "contract_file": "contracts/contract-900kb.clar",
                    "contract_name": "contract-900kb"
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
            Step(
                name="Deploy 3000KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-3000kb.clar",
                    "contract_name": "contract-3000kb"
                },
                wait=True,
                on_error="continue"
            ),
            Step(
                name="Deploy 4000KB contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-4000kb.clar",
                    "contract_name": "contract-4000kb"
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

def extract_size_from_step_name(step_name):
    """Extract size in KB from step name like 'Deploy 2000KB contract'"""
    if "Deploy" in step_name and "KB contract" in step_name:
        try:
            # Extract number between "Deploy " and "KB contract"
            start = step_name.find("Deploy ") + 7
            end = step_name.find("KB contract")
            size_str = step_name[start:end]
            return int(size_str)
        except:
            return None
    return None

def analyze_size_limits(steps):
    """Analyze deployment results to find size limits"""
    deployment_steps = []
    
    # Filter deployment steps and extract sizes
    for step in steps:
        step_name = step.get('name', '')
        if "Deploy" in step_name and "KB contract" in step_name:
            size = extract_size_from_step_name(step_name)
            if size is not None:
                deployment_steps.append({
                    'name': step_name,
                    'size_kb': size,
                    'success': step.get('success', False),
                    'error': step.get('error', '')
                })
    
    # Sort by size
    deployment_steps.sort(key=lambda x: x['size_kb'])
    
    # Find boundary
    last_successful = None
    first_failed = None
    
    for step in deployment_steps:
        if step['success']:
            last_successful = step
        elif first_failed is None:
            first_failed = step
            break
    
    return deployment_steps, last_successful, first_failed

def main():
    """Execute the size limits test recipe"""
    print("=" * 80)
    print(f"{Colors.format_header('FIND EXACT STACKS SIZE LIMITS')}")
    print("=" * 80)
    
    runner = Runner()
    recipe = create_size_limits_recipe()
    result = runner.run(recipe)
    
    # Analyze size limits from results
    deployment_steps, last_successful, first_failed = analyze_size_limits(result.get('steps', []))
    
    # Determine if test was successful (finding a limit is success)
    test_successful = last_successful is not None and first_failed is not None
    
    print(f"\nRecipe: {Colors.format_info(result['name'])}")
    print(f"Overall Success: {Colors.format_success('✓ PASSED') if test_successful else Colors.format_error('✗ FAILED')}")
    duration_text = f"{result.get('duration', 0):.2f} seconds"
    print(f"Duration: {Colors.format_dim(duration_text)}")
    
    print(f"\n{Colors.format_header('SIZE LIMIT ANALYSIS:')}")
    
    for i, step in enumerate(result.get('steps', []), 1):
        status = Colors.format_success('✓') if step.get('success', False) else Colors.format_error('✗')
        print(f"  {i}. {step.get('name', 'Unknown')}: {status}")
        
        if not step.get('success', False) and 'error' in step:
            error_preview = step['error'][:100] + "..." if len(step['error']) > 100 else step['error']
            print(f"     {Colors.format_error(error_preview)}")
    
    # Add size limit findings at the end
    if last_successful and first_failed:
        print(f"\n{Colors.format_success('LIMIT FOUND!')}")
        last_size = f"{last_successful['size_kb']}KB"
        first_size = f"{first_failed['size_kb']}KB"
        size_range = f"{last_successful['size_kb']}KB and {first_failed['size_kb']}KB"
        print(f"   Last successful: {Colors.format_success(last_size)} ({last_successful['name']})")
        print(f"   First failed: {Colors.format_error(first_size)} ({first_failed['name']})")
        print(f"   Size limit is between {Colors.format_info(size_range)}")
        
        if first_failed.get('error'):
            print(f"   Failure reason: {Colors.format_dim(first_failed['error'][:150])}")
            
    elif last_successful and not first_failed:
        print(f"\n{Colors.format_warning('All contracts deployed successfully')}")
        largest_size = f"{last_successful['size_kb']}KB"
        print(f"   Largest successful: {Colors.format_success(largest_size)}")
        print(f"   Need to test larger contracts to find the limit")
        
    elif not last_successful and first_failed:
        print(f"\n{Colors.format_error('All contracts failed to deploy')}")
        first_failure_size = f"{first_failed['size_kb']}KB"
        print(f"   First failure: {Colors.format_error(first_failure_size)}")
        print(f"   Need to test smaller contracts")
        
    else:
        print(f"\n{Colors.format_warning('No deployment results found')}")

if __name__ == "__main__":
    main()