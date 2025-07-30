#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors
from utils.forensics import Forensics
from utils.contract import Contract

def generate_contract_files(count: int) -> list:
    """Helper to generate a list of contract files from existing contracts for the recipe."""
    # Use existing contract files from the contracts directory (up to 1000kb max)
    base_contract_files = [
        "contracts/contract-8kb.clar",
        "contracts/contract-16kb.clar", 
        "contracts/contract-24kb.clar",
        "contracts/contract-40kb.clar",
        "contracts/contract-60kb.clar",
        "contracts/contract-80kb.clar",
        "contracts/contract-100kb.clar",
        "contracts/contract-120kb.clar",
        "contracts/contract-160kb.clar",
        "contracts/contract-200kb.clar",
        "contracts/contract-240kb.clar",
        "contracts/contract-300kb.clar",
        "contracts/contract-400kb.clar",
        "contracts/contract-500kb.clar",
        "contracts/contract-600kb.clar",
        "contracts/contract-700kb.clar",
        "contracts/contract-800kb.clar",
        "contracts/contract-900kb.clar",
        "contracts/contract-1000kb.clar"
    ]
    
    # Cycle through contracts if count > available files
    contract_files = []
    for i in range(count):
        contract_files.append(base_contract_files[i % len(base_contract_files)])
    
    return contract_files

def create_stress_recipe(context: dict):
    """
    Creates a two-step recipe implementing idea.txt suggestions:
    1. Run the batch contract deployment until the limit is found, storing the result in the context.
    2. Verify the result from the context using the forensics module.
    """
    return Recipe(
        name="Find Mempool Chaining Limit for Contract Deployments and Verify",
        description="Enhanced two-step recipe with block height awareness and immediate re-submission of failed contract deployments.",
        setup=True,
        cleanup=True,
        steps=[
            Step(
                name="Deploy contracts until limit is found",
                module="contract",
                method="batch_deploy",
                params={
                    "from_miner": "miner1",
                    "contracts": generate_contract_files(100),
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
    runner.modules['contract'] = Contract()
    runner.modules['forensics'] = Forensics()
    
    recipe = create_stress_recipe(test_context)
    result = runner.run(recipe)
    
    # The pass/fail logic is now entirely handled by the recipe steps.
    # The main function just reports the final outcome from the runner.
    print("\n" + "="*60)
    print(f"{Colors.format_header('FINAL RECIPE RESULT')}")
    print("="*60)
    
    if result['success']:
        print(f"{Colors.format_success('✓ RECIPE PASSED')}: The system behaved as expected under contract deployment stress.")
        sys.exit(0)
    else:
        print(f"{Colors.format_error('✗ RECIPE FAILED')}: The system did not behave as expected.")
        # The detailed error will have already been printed by the failing step.
        sys.exit(1)

if __name__ == "__main__":
    main()