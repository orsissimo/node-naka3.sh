#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors, StacksTestBase
from utils.transaction import Transaction

# The constant from the Stacks node source code
MAXIMUM_MEMPOOL_TX_CHAINING = 25

class ChainingTester:
    """A custom test module to handle the dynamic logic of this recipe."""
    def __init__(self):
        self.base = StacksTestBase()
        self.transaction = Transaction()

    def trigger_origin_error(self) -> bool:
        """Fetches current nonce, calculates a bad nonce, and expects failure."""
        print(f"\n{Colors.format_subheader('--- Testing Origin TooMuchChaining ---')}")
        try:
            current_nonce = self.base.get_nonce("miner1")
            bad_nonce = current_nonce + MAXIMUM_MEMPOOL_TX_CHAINING + 2
            print(f"Current nonce is {current_nonce}, attempting to submit with nonce {bad_nonce}")
            
            self.transaction.transfer(
                from_miner="miner1",
                to_address="ST3KCNDSWZSFZCC6BE4VA9AXWXC9KEB16FBTRK36T",
                amount=100,
                nonce=bad_nonce
            )
            # If the above line does NOT raise an exception, the test has failed.
            print(f"{Colors.format_error('✗ TEST FAILED')}: Transaction was unexpectedly accepted.")
            return False
        except Exception as e:
            error_str = str(e)
            if "TooMuchChaining" in error_str:
                print(f"{Colors.format_success('✓ TEST PASSED')}: Correctly received TooMuchChaining error.")
                return True
            else:
                print(f"{Colors.format_error('✗ TEST FAILED')}: Transaction failed, but for the wrong reason.")
                print(f"  Error: {error_str}")
                return False

def create_chaining_limit_recipe():
    """Defines the steps to run our custom ChainingTester module."""
    return Recipe(
        name="Mempool Chaining Limit Test",
        description="Intentionally trigger 'TooMuchChaining' errors for origin and sponsor.",
        setup=True,
        cleanup=True,
        steps=[
            Step(
                name="Trigger TooMuchChaining for Originator",
                module="chaining_tester", # Our custom module
                method="trigger_origin_error",
                params={},
                wait=False,
                on_error="stop"
            ),
        ]
    )

def main():
    """Main execution block."""
    runner = Runner()
    
    # IMPORTANT: Register our custom tester class as a module the runner can use.
    runner.modules['chaining_tester'] = ChainingTester()
    
    recipe = create_chaining_limit_recipe()
    result = runner.run(recipe)

    # The logic inside ChainingTester now handles pass/fail, so we can use standard reporting.
    print("\n" + "=" * 60)
    print(f"{Colors.format_header('RECIPE EXECUTION RESULTS')}")
    print("=" * 60)
    print(f"Recipe: {Colors.format_info(result['name'])}")
    print(f"Overall Success: {Colors.format_success('✓ PASSED') if result['success'] else Colors.format_error('✗ FAILED')}")
    
    sys.exit(0 if result['success'] else 1)

if __name__ == "__main__":
    main()