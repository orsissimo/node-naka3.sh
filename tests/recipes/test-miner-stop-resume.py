#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors

def create_miner_stop_resume_recipe():
    return Recipe(
        name="Miner Mempool Stop/Resume Test",
        description="Submit unprocessed transactions to specific miner, stop it, test mempool behavior",
        setup=True,  # Use recipe's built-in node management
        cleanup=True,  # Use recipe's built-in node management
        steps=[
            # Step 1: Submit transaction to miner2's mempool WITHOUT waiting for confirmation
            Step(
                name="Submit unprocessed tx to miner2's mempool",
                module="transaction", 
                method="submit_no_wait",
                params={
                    "target_miner": "miner2",  # Submit to miner2's specific endpoint
                    "from_miner": "miner2",    # Transaction from miner2 account
                    "to_address": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",  # miner1 address
                    "amount": 500000,  # 0.5 STX in µSTX
                    "memo": "Unprocessed tx in miner2 mempool"
                },
                wait=False,  # Don't wait for confirmation - keep in mempool
                on_error="stop"
            ),
            # Step 2: Submit second transaction to miner2's mempool with nonce 1
            Step(
                name="Submit second unprocessed tx to miner2's mempool", 
                module="transaction",
                method="submit_no_wait",
                params={
                    "target_miner": "miner2",  # Submit to miner2's specific endpoint
                    "from_miner": "miner2",    # Transaction from miner2 account
                    "to_address": "ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0",  # miner3 address
                    "amount": 300000,  # 0.3 STX in µSTX
                    "memo": "Second unprocessed tx in miner2 mempool",
                    "nonce": 1  # Use nonce 1 for second transaction
                },
                wait=False,  # Don't wait for confirmation - keep in mempool
                on_error="stop"
            ),
            # Step 3: Stop miner2 while transactions are in mempool
            Step(
                name="Stop miner2 with unprocessed transactions",
                module="node",
                method="stop_miner", 
                params={
                    "miner_id": 2
                },
                wait=True,
                on_error="stop"
            ),
            # Step 4: Try to verify the previous txs (using verify_transaction_no_wait from base.py)
            Step(
                name="Verify transactions while miner2 is stopped",
                module="transaction",
                method="verify_previous_transactions",
                params={
                    "query_miner": "miner1",  # Query from active miner1
                    "check_stopped_miner": True
                },
                wait=True,
                on_error="continue"  # Continue even if verification fails
            ),
            # Step 5: Resume miner2
            Step(
                name="Resume miner2",
                module="node",
                method="resume_miner",
                params={
                    "miner_id": 2
                },
                wait=True,
                on_error="stop"
            ),
            # Step 6: Try to verify the previous txs again (using verify_transaction_no_wait from base.py)
            Step(
                name="Verify transactions after miner2 resumed",
                module="transaction",
                method="verify_previous_transactions",
                params={
                    "query_miner": "miner2",  # Query from resumed miner2
                    "check_resumed_miner": True
                },
                wait=True,
                on_error="continue"  # Continue even if verification fails
            )
        ]
    )

def main():
    """Execute the miner mempool stop/resume recipe test"""
    print("=" * 80)
    print(f"{Colors.format_header('RECIPE TO TEST MINER MEMPOOL BEHAVIOR ON STOP/RESUME')}")
    print("=" * 80)
    print(f"{Colors.format_dim('This test will:')}")
    print(f"{Colors.format_dim('1. Submit two unprocessed transactions to miner2 mempool')}")
    print(f"{Colors.format_dim('2. Stop miner2 with pending mempool transactions')}")
    print(f"{Colors.format_dim('3. Try to verify transactions while miner2 is stopped')}")
    print(f"{Colors.format_dim('4. Resume miner2')}")
    print(f"{Colors.format_dim('5. Try to verify transactions after miner2 is resumed')}")
    print("=" * 80)
    
    runner = Runner()
    recipe = create_miner_stop_resume_recipe()
    
    # Run the recipe with built-in node management
    result = runner.run(recipe)
    
    # Print results summary  
    print("\n" + "=" * 80)
    print(f"{Colors.format_header('RECIPE EXECUTION RESULTS')}")
    print("=" * 80)
    
    print(f"Recipe: {Colors.format_info(result['name'])}")
    print(f"Overall Success: {Colors.format_success('✓ PASSED') if result['success'] else Colors.format_error('✗ FAILED')}")
    duration_text = f"{result.get('duration', 0):.2f} seconds"
    print(f"Duration: {Colors.format_dim(duration_text)}")
    print(f"Setup Success: {Colors.format_success('✓') if result.get('setup_success', False) else Colors.format_error('✗')}")
    print(f"Cleanup Success: {Colors.format_success('✓') if result.get('cleanup_success', False) else Colors.format_error('✗')}")
    
    # Chain progression results
    if result.get('chain_progression_verified', False):
        print(f"Chain Progression: {Colors.format_success('✓ VERIFIED')}")
    else:
        print(f"Chain Progression: {Colors.format_error('✗ FAILED')}")
        if 'chain_verification_error' in result:
            print(f"  Error: {Colors.format_error(result['chain_verification_error'])}")
    
    steps_count = len(result.get('steps', []))
    print(f"\n{Colors.format_subheader(f'Step Results ({steps_count} steps)')}")
    
    expected_failure_step = "Verify miner2 API is down (should fail)"
    
    for i, step in enumerate(result.get('steps', []), 1):
        step_name = step.get('name', 'Unknown')
        step_success = step.get('success', False)
        
        # Special handling for the expected failure step
        if step_name == expected_failure_step:
            if not step_success:
                status = Colors.format_success('✓ FAILED AS EXPECTED')
                print(f"  {Colors.format_info(f'{i}.')} {Colors.format_dim(step_name)}: {status}")
                if 'error' in step:
                    print(f"     Expected Error: {Colors.format_success(step['error'])}")
            else:
                status = Colors.format_error('✗ UNEXPECTEDLY SUCCEEDED')
                print(f"  {Colors.format_info(f'{i}.')} {Colors.format_dim(step_name)}: {status}")
                print(f"     Warning: {Colors.format_warning('API connection should have failed but succeeded!')}")
        else:
            # Normal step handling
            status = Colors.format_success('✓ PASSED') if step_success else Colors.format_error('✗ FAILED')
            duration = step.get('duration', 0)
            retries = step.get('retries', 0)
            duration_retries_text = f"{duration:.2f}s, {retries} retries"
            print(f"  {Colors.format_info(f'{i}.')} {Colors.format_dim(step_name)}: {status} ({Colors.format_dim(duration_retries_text)})")
            
            if not step_success and 'error' in step:
                print(f"     Error: {Colors.format_error(step['error'])}")
            elif step_success and 'result' in step:
                step_result = step['result']
                if isinstance(step_result, str) and len(step_result) == 66:  # Likely a transaction ID
                    print(f"     TX ID: {Colors.format_dim(step_result)}")
                elif isinstance(step_result, dict):
                    # Handle structured results
                    if 'txid' in step_result:
                        print(f"     TX ID: {Colors.format_dim(step_result['txid'])}")
                    elif 'success' in step_result:
                        print(f"     Operation: {Colors.format_success('✓') if step_result['success'] else Colors.format_error('✗')}")
    
    # Final summary
    print("\n" + "=" * 80)
    print(f"{Colors.format_header('FINAL RESULT')}")
    print("=" * 80)
    
    # Check if the expected failure step actually failed
    expected_failure_occurred = False
    for step in result.get('steps', []):
        if step.get('name') == expected_failure_step and not step.get('success', True):
            expected_failure_occurred = True
            break
    
    if result['success'] and expected_failure_occurred:
        print(f"{Colors.format_success('✓ ALL TESTS PASSED')} - Miner mempool behavior working correctly")
        print(f"{Colors.format_success('✓ Expected failure')} occurred when trying to connect to stopped miner")
        print(f"{Colors.format_success('✓ Mempool recovery successful')} after miner resume")
        return True
    elif result['success'] and not expected_failure_occurred:
        print(f"{Colors.format_warning('⚠ PARTIAL SUCCESS')} - All steps passed but expected failure didn't occur")
        print(f"{Colors.format_warning('Warning:')} API connection to stopped miner should have failed")
        return False
    else:
        print(f"{Colors.format_error('✗ TESTS FAILED')} - Miner mempool stop/resume test encountered errors")
        failed_steps = [step for step in result.get('steps', []) if not step.get('success', False) and step.get('name') != expected_failure_step]
        if failed_steps:
            print(f"{Colors.format_warning('Unexpected failures:')}")
            for step in failed_steps:
                print(f"  - {Colors.format_error(step.get('name', 'Unknown'))}: {Colors.format_error(step.get('error', 'No error details'))}")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)