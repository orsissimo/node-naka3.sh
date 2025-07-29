#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors
from utils.forensics import Forensics
from utils.transaction import Transaction

def generate_transfers(count: int) -> list:
    """Helper to generate a list of transfers for the recipe."""
    transfers = []
    addresses = ["ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM"]
    for i in range(count):
        transfers.append({"to": addresses[0], "amount": 100 + i, "memo": f"StressTx{i+1}"})
    return transfers

def create_stress_recipe(context: dict):
    """
    Creates a two-step recipe:
    1. Run the batch until the limit is found, storing the result in the context.
    2. Verify the result from the context using the forensics module.
    """
    return Recipe(
        name="Find Mempool Chaining Limit and Verify",
        description="A two-step recipe to find the mempool limit and then run diagnostics.",
        setup=True,
        cleanup=True,
        steps=[
            Step(
                name="Submit until limit is found",
                module="transaction",
                method="batch",
                params={
                    "from_miner": "miner1",
                    "transfers": generate_transfers(50),
                    "context": context  # Pass the shared context dictionary
                },
                wait=False, # Let the method handle its own waiting
                on_error="stop"
            ),
            Step(
                name="Verify Batch and Diagnose Result",
                module="forensics",
                method="verify_batch_limit_test",
                params={
                    "context": context # Pass the same context dictionary
                },
                wait=False,
                on_error="stop"
            )
        ]
    )

def main():
    # A shared context dictionary to pass data between steps
    test_context = {}

    runner = Runner()
    # IMPORTANT: Register all modules that will be called by steps.
    runner.modules['transaction'] = Transaction()
    runner.modules['forensics'] = Forensics()
    
    recipe = create_stress_recipe(test_context)
    result = runner.run(recipe)
    
    # The pass/fail logic is now entirely handled by the recipe steps.
    # The main function just reports the final outcome from the runner.
    print("\n" + "="*60)
    print(f"{Colors.format_header('FINAL RECIPE RESULT')}")
    print("="*60)
    
    if result['success']:
        print(f"{Colors.format_success('✓ RECIPE PASSED')}: The system behaved as expected under stress.")
        sys.exit(0)
    else:
        print(f"{Colors.format_error('✗ RECIPE FAILED')}: The system did not behave as expected.")
        # The detailed error will have already been printed by the failing step.
        sys.exit(1)

if __name__ == "__main__":
    main()