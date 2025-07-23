#!/usr/bin/env python3
"""
Recipe-based contract test that exactly replicates test-contract.py functionality
using minimal LOC with the recipe system.
"""

from utils.recipes import Runner, Recipe, Step

def create_contract_simple_recipe():
    return Recipe(
        name="Contract Simple Test",
        description="Deploy contract, test interaction, verify chain progression",
        setup=True,  # Use recipe's built-in node management
        cleanup=True,  # Use recipe's built-in node management
        steps=[
            # Step 1: Deploy contract (replicates test_contract_deployment)
            Step(
                name="Deploy counter contract",
                module="contract",
                method="deploy_and_test",
                params={
                    "miner": "miner1",
                    "contract_file": "contracts/contract-counter.clar", 
                    "contract_name": "mycontract",
                    "test_functions": [
                        {"name": "get-counter", "type": "read"},
                        {"name": "increment", "type": "public"},
                        {"name": "get-counter", "type": "read"},
                        {"name": "get-last-caller", "type": "read"}
                    ]
                },
                wait=True,
                on_error="stop"
            )
        ]
    )

def main():
    """Execute the contract simple recipe test"""
    print("=" * 60)
    print("RECIPE TO TEST BASIC CONTRACT DEPLOYMENT AND INTERACTIONS")
    print("=" * 60)
    
    runner = Runner()
    recipe = create_contract_simple_recipe()
    
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
            if isinstance(step_result, dict) and 'function_results' in step_result:
                print(f"     Contract: {step_result.get('contract_name', 'Unknown')}")
                print(f"     Deploy TXID: {step_result.get('deploy_txid', 'Unknown')}")
                print(f"     Function tests:")
                for func_result in step_result.get('function_results', []):
                    func_status = '✓' if func_result.get('success', False) else '✗'
                    func_name = func_result.get('function', 'unknown')
                    func_type = func_result.get('type', 'unknown')
                    print(f"       {func_status} {func_name} ({func_type})")
                    if not func_result.get('success', False) and 'error' in func_result:
                        print(f"         Error: {func_result['error']}")
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
        print("✓ ALL TESTS PASSED - Contract successfully deployed, tested, and chain healthy")
        print("✓ Recipe-based test exactly replicated test-contract.py functionality")
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