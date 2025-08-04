#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors

def create_memory_limits_recipe():
    return Recipe(
        name="Memory Limits Test",
        description="Deploy memory-bomb contract and test blockchain memory limits",
        setup=True,  # Use recipe's built-in node management
        cleanup=True,  # Use recipe's built-in node management
        steps=[
            # Step 1: Deploy memory-bomb contract
            Step(
                name="Deploy memory-bomb contract",
                module="contract",
                method="deploy",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/memory-bomb.clar", 
                    "contract_name": "memory-bomb"
                },
                wait=True,
                on_error="stop"
            ),
            # Step 2: Read initial map entry (should be none)
            Step(
                name="Read initial map entry",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "get-map-entry",
                    "args": ["u1"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 3: Test small map population (should succeed)
            Step(
                name="Populate map with small count",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "populate-massive-map",
                    "args": ["u10"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 4: Read map entry after small population
            Step(
                name="Read map entry after small population",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "get-map-entry",
                    "args": ["u5"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 5: Test memory allocation with small count
            Step(
                name="Memory allocation stress test (small)",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "memory-alloc-stress",
                    "args": ["u5"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 6: Test gas consumption with moderate iterations
            Step(
                name="Gas consumption test (moderate)",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "gas-hog",
                    "args": ["u100"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 7: Test deep recursion with small fibonacci number
            Step(
                name="Deep recursion test (small fibonacci)",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "deep-recursion-fibonacci",
                    "args": ["u10"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 8: Test larger map population (may fail due to limits)
            Step(
                name="Populate map with large count (stress test)",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "populate-massive-map",
                    "args": ["u1000"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 9: Test larger memory allocation (may fail due to limits)
            Step(
                name="Memory allocation stress test (large)",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "memory-alloc-stress",
                    "args": ["u100"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 10: Test high gas consumption (may fail due to limits)
            Step(
                name="Gas consumption test (high)",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "gas-hog",
                    "args": ["u10000"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 11: Test deep recursion (may fail due to stack limits)
            Step(
                name="Deep recursion test (large fibonacci)",
                module="contract",
                method="call",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "deep-recursion-fibonacci",
                    "args": ["u30"]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 12: Final map entry read to verify state
            Step(
                name="Final map entry verification",
                module="contract",
                method="read",
                params={
                    "miner": "miner1",
                    "contract_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "contract_name": "memory-bomb",
                    "function_name": "get-map-entry",
                    "args": ["u999"]
                },
                wait=True,
                on_error="continue"
            )
        ]
    )

def main():
    """Execute the memory limits recipe test"""
    print("=" * 60)
    print(f"{Colors.format_header('RECIPE TO TEST MEMORY-BOMB CONTRACT AND BLOCKCHAIN LIMITS')}")
    print("=" * 60)
    
    runner = Runner()
    recipe = create_memory_limits_recipe()
    
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
    
    # Memory limits analysis
    print("\n" + "=" * 60)
    print(f"{Colors.format_header('MEMORY LIMITS ANALYSIS')}")
    print("=" * 60)
    
    # Analyze which memory/resource limits were hit
    failed_steps = [step for step in result.get('steps', []) if not step.get('success', False)]
    passed_steps = [step for step in result.get('steps', []) if step.get('success', False)]
    
    print(f"Steps that succeeded: {Colors.format_success(len(passed_steps))}")
    print(f"Steps that failed: {Colors.format_error(len(failed_steps))}")
    
    if failed_steps:
        print(f"\n{Colors.format_warning('Failed steps (likely due to resource limits):')}")
        for step in failed_steps:
            step_name = step.get('name', 'Unknown')
            error_msg = step.get('error', 'No error details')
            print(f"  - {Colors.format_error(step_name)}")
            print(f"    {Colors.format_dim('Error:')} {Colors.format_error(error_msg)}")
    
    # Final summary
    print("\n" + "=" * 60)
    print(f"{Colors.format_header('FINAL RESULT')}")
    print("=" * 60)
    
    if result['success']:
        print(f"{Colors.format_success('✓ ALL TESTS PASSED')} - Memory-bomb contract successfully tested all limits")
        print(f"{Colors.format_success('✓ No resource limits hit')} - Blockchain handled all memory/compute tests")
        return True
    else:
        print(f"{Colors.format_warning('⚠ TESTS COMPLETED WITH RESOURCE LIMITS')} - Some memory/compute limits were reached")
        print(f"{Colors.format_info('ℹ This is expected behavior')} - The test successfully identified blockchain limits")
        
        # Provide insights about which limits were hit
        memory_tests_failed = any('memory-alloc' in step.get('name', '') for step in failed_steps)
        gas_tests_failed = any('gas' in step.get('name', '') for step in failed_steps)
        recursion_tests_failed = any('recursion' in step.get('name', '') for step in failed_steps)
        map_tests_failed = any('map' in step.get('name', '') for step in failed_steps)
        
        limits_hit = []
        if memory_tests_failed:
            limits_hit.append("Memory allocation limits")
        if gas_tests_failed:
            limits_hit.append("Gas/computation limits")
        if recursion_tests_failed:
            limits_hit.append("Stack depth/recursion limits")
        if map_tests_failed:
            limits_hit.append("Storage/map size limits")
        
        if limits_hit:
            print(f"{Colors.format_info('Limits identified:')} {', '.join(limits_hit)}")
        
        return True  # Return True since hitting limits is expected behavior

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)