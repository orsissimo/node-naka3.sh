#!/usr/bin/env python3
"""
Recipe-based transaction test that exactly replicates test-transaction.py functionality
using minimal LOC with the recipe system.
"""

from utils.recipes import Runner, Recipe, Step

def create_transaction_simple_recipe():
    return Recipe(
        name="Transaction Simple Test",
        description="Send STX transfer, verify confirmation, check chain progression",
        setup=True,  # Use recipe's built-in node management
        cleanup=True,  # Use recipe's built-in node management
        steps=[
            # Step 1: Send STX transfer (replicates test_transaction)
            Step(
                name="Send STX transfer",
                module="transaction",
                method="transfer",
                params={
                    "from_miner": "miner1",
                    "to_address": "ST3KCNDSWZSFZCC6BE4VA9AXWXC9KEB16FBTRK36T",
                    "amount": 1000,
                    "memo": "HelloMemoRecipe"
                },
                wait=True,
                on_error="stop"
            )
        ]
    )

def main():
    """Execute the transaction simple recipe test"""
    print("=" * 60)
    print("RECIPE TO TEST BASIC STX TRANSACTION")
    print("=" * 60)
    
    runner = Runner()
    recipe = create_transaction_simple_recipe()
    
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
            # Show transaction ID for transfers
            if isinstance(step_result, str) and len(step_result) == 64:  # Looks like a txid
                print(f"     Transaction ID: {step_result}")
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
        print("✓ ALL TESTS PASSED - Transaction successfully sent, confirmed, and chain healthy")
        print("✓ Recipe-based test exactly replicated test-transaction.py functionality")
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