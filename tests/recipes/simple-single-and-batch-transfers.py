#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors

def create_single_and_batch_transfers_recipe():
    return Recipe(
        name="Single and Batch Transfers Test",
        description="Test single STX transfer followed by multiple batch transfers",
        setup=True,  # Use recipe's built-in node management
        cleanup=True,  # Use recipe's built-in node management
        steps=[
            # Step 1: Single STX transfer
            Step(
                name="Single STX transfer",
                module="transaction",
                method="transfer",
                params={
                    "from_miner": "miner1",
                    "to_address": "ST3KCNDSWZSFZCC6BE4VA9AXWXC9KEB16FBTRK36T",
                    "amount": 1000,
                    "memo": "SingleTransfer"
                },
                wait=True,
                on_error="stop"
            ),
            # Step 2: True batch transfer (10 transactions submitted rapidly for same block)
            Step(
                name="True batch transfer",
                module="transaction",
                method="batch",
                params={
                    "from_miner": "miner1",
                    "transfers": [
                        {"to": "ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y", "amount": 500, "memo": "BatchTx1"},
                        {"to": "ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM", "amount": 750, "memo": "BatchTx2"},
                        {"to": "ST3KCNDSWZSFZCC6BE4VA9AXWXC9KEB16FBTRK36T", "amount": 300, "memo": "BatchTx3"},
                        {"to": "ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM", "amount": 400, "memo": "BatchTx4"},
                        {"to": "ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y", "amount": 200, "memo": "BatchTx5"},
                        {"to": "ST3KCNDSWZSFZCC6BE4VA9AXWXC9KEB16FBTRK36T", "amount": 600, "memo": "BatchTx6"},
                        {"to": "ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM", "amount": 100, "memo": "BatchTx7"},
                        {"to": "ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y", "amount": 350, "memo": "BatchTx8"},
                        {"to": "ST3KCNDSWZSFZCC6BE4VA9AXWXC9KEB16FBTRK36T", "amount": 150, "memo": "BatchTx9"},
                        {"to": "ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM", "amount": 250, "memo": "BatchTx10"}
                    ]
                },
                wait=True,
                on_error="continue"
            ),
            # Step 3: Final transfer from miner2 (wait for this one to confirm all)
            Step(
                name="Reverse transfer",
                module="transaction", 
                method="transfer",
                params={
                    "from_miner": "miner2",
                    "to_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                    "amount": 250,
                    "memo": "ReverseTransfer" 
                },
                wait=True,
                on_error="continue"
            )
        ]
    )

def main():
    """Execute the single and batch transfers recipe test"""
    print("=" * 60)
    print(f"{Colors.format_header('RECIPE TO TEST SINGLE AND BATCH STX TRANSFERS')}")
    print("=" * 60)
    
    runner = Runner()
    recipe = create_single_and_batch_transfers_recipe()
    
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
            # Show transaction ID for transfers
            if isinstance(step_result, str) and len(step_result) == 64:  # Looks like a txid
                print(f"     Transaction ID: {Colors.format_dim(step_result)}")
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
        print(f"{Colors.format_success('✓ ALL TESTS PASSED')} - Single and batch transfers completed successfully")
        print(f"{Colors.format_success('✓ Recipe-based test')} demonstrating multiple transfer scenarios")
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