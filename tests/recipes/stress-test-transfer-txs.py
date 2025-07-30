#!/usr/bin/env python3
import sys
import os
from typing import Optional
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.recipes import Runner, Recipe, Step
from utils.base import Colors, StacksTestBase
from utils.transaction import Transaction

class StressTestForensics(StacksTestBase):
    """Forensics methods specific to the stress test recipe."""
    
    def verify_batch_limit_test(self, context: dict) -> bool:
        """
        Verifies the results of a batch limit-finding run stored in the context.
        This method implements the precise success criteria for the test and is
        designed to be called as a recipe step.
        """
        print("\n" + "="*80)
        print(f"{Colors.format_header('VERIFICATION & DIAGNOSTICS')}")
        print("="*80)
        
        batch_report = context.get('batch_report')
        if not batch_report:
            raise RuntimeError("Test framework error: Batch report not found in context for verification.")

        # Condition 1: Verify that the 'TooMuchChaining' limit was found.
        if batch_report['status'] != 'LimitFound':
            raise RuntimeError(f"Test failed: The script did not trigger the 'TooMuchChaining' limit. Final status was: {batch_report['status']}")
        
        print(f"{Colors.format_success('✓ Condition 1 Met')}: Successfully triggered the 'TooMuchChaining' limit at nonce {batch_report['limit_nonce']}.")
        
        # Condition 2: Verify each successfully submitted transaction one-by-one.
        print(f"\n{Colors.format_subheader('Verifying all submitted transactions...')}")
        tx_utility = Transaction()
        all_verified_successfully = True
        
        for tx_info in batch_report['successful_submissions']:
            nonce_str = f"  - Nonce {tx_info['nonce']:<3}"
            # This call now prints the full JSON details you requested.
            verification_result = tx_utility.verify_transaction_no_wait(
                miner=batch_report['from_miner'],
                txid=tx_info['txid']
            )
            
            # Enhanced verification logic to handle multiple success indicators
            is_verified = self._is_transaction_verified(verification_result)
            
            if is_verified:
                print(f"{nonce_str}: {Colors.format_success('✓ Verification PASSED')}")
            else:
                all_verified_successfully = False
                error_info = self._get_verification_error_info(verification_result)
                print(f"{nonce_str}: {Colors.format_error('✗ Verification FAILED')} ({error_info})")

        if not all_verified_successfully:
            raise RuntimeError("Test failed: Not all submitted transactions were successfully confirmed on-chain.")
            
        print(f"\n{Colors.format_success('✓ Condition 2 Met')}: All {len(batch_report['successful_submissions'])} submitted transactions were successfully verified on-chain.")
        
        print(f"\n{Colors.format_success('✓ ALL CONDITIONS MET - TEST PASSED')}")
        return True # Return True to the runner, indicating this step's success.

    def _is_transaction_verified(self, verification_result: dict) -> bool:
        """
        Determines if a transaction is verified based on multiple success indicators.
        
        Args:
            verification_result: The result dictionary from verify_transaction_no_wait
            
        Returns:
            bool: True if the transaction is verified, False otherwise
        """
        # Check the primary success flag
        if not verification_result.get('success', False):
            return False
        
        # Get transaction data
        tx_data = verification_result.get('transaction_data', {})
        tx_status = tx_data.get('tx_status', 'unknown')
        
        # Check for standard success status
        if tx_status == 'success':
            return True
        
        # Check for "(ok true)" result pattern
        result = tx_data.get('result', '')
        if result == '(ok true)':
            return True
        
        # Could add more success patterns here as needed
        # For example: result.startswith('(ok ') for other ok patterns
        
        return False

    def _get_verification_error_info(self, verification_result: dict) -> str:
        """
        Extracts error information from a failed verification result.
        
        Args:
            verification_result: The result dictionary from verify_transaction_no_wait
            
        Returns:
            str: A descriptive error message
        """
        # Check for explicit error in verification_result
        if 'error' in verification_result:
            return verification_result['error']
        
        # Check transaction status
        tx_data = verification_result.get('transaction_data', {})
        tx_status = tx_data.get('tx_status', 'unknown')
        
        if tx_status != 'success':
            return f'Transaction status: {tx_status}'
        
        # Check result field for error patterns
        result = tx_data.get('result', '')
        if result and result != '(ok true)':
            return f'Result: {result}'
        
        return 'Unknown verification failure'

class StressTestTransaction(Transaction):
    """Enhanced Transaction class with stress test specific methods."""
    
    def _extract_expected_nonce(self, error_str: str) -> Optional[int]:
        """Extract expected nonce from TooMuchChaining error message."""
        import re
        # Look for pattern like "expected': 26" in the error
        match = re.search(r"'expected':\s*(\d+)", error_str)
        if match:
            return int(match.group(1))
        return None

    def resubmit_failed_in_same_block(self, context: dict) -> bool:
        """
        Re-submits transactions that failed due to TooMuchChaining in the SAME block,
        starting from the expected nonce. If block proceeds, restarts the whole test.
        """
        retry_info = context.get('retry_info')
        if not retry_info or not retry_info.get('retry_nonce'):
            print(f"{Colors.format_warning('⚠ No retry info available - skipping resubmission')}")
            return True
            
        from_miner = context['batch_report']['from_miner']
        retry_nonce = retry_info['retry_nonce']
        original_block_height = retry_info['block_height_when_failed']
        
        print(f"\n{Colors.format_header('=== RE-SUBMISSION IN SAME BLOCK ===')}")
        print(f"Block height when failed: {original_block_height}")
        print(f"Retrying failed nonce: {retry_nonce}")
        
        # Check if block has proceeded - if so, we must restart
        current_height = self.get_block_height(from_miner)
        if current_height != original_block_height:
            print(f"{Colors.format_error('✗ BLOCK PROCEEDED!')}")
            print(f"  Original: {original_block_height}, Current: {current_height}")
            print(f"{Colors.format_warning('⚠ Must restart test from beginning')}")
            raise RuntimeError("Block proceeded during mempool testing - test must be restarted")
        
        print(f"✓ Block height unchanged: {current_height}")
        
        # Prepare transaction starting from expected nonce
        account = self.get_account(from_miner)
        transfer = {"to": "ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM", "amount": 100, "memo": "RetryTx"}
        
        try:
            cmd = ["blockstack-cli", "--testnet", "token-transfer", account.private_key, "180", 
                    str(retry_nonce), transfer['to'], str(transfer['amount']), transfer['memo']]
            tx_binary = self.run_cli_command(cmd, binary_output=True)
            
            # Double-check block height hasn't proceeded during tx preparation
            height_after_prep = self.get_block_height(from_miner)
            if height_after_prep != original_block_height:
                print(f"{Colors.format_error('✗ BLOCK PROCEEDED DURING PREPARATION!')}")
                print(f"  Original: {original_block_height}, After prep: {height_after_prep}")
                raise RuntimeError("Block proceeded during transaction preparation - test must be restarted")
            
            response = self.api_call(account, "/v2/transactions", "POST", tx_binary)
            txid = self.handle_api_response(response)
            
            print(f"{Colors.format_success(f'✓ Re-submitted tx (nonce {retry_nonce}) in same block')}: {Colors.format_dim(txid)}")
            
            # Store retry result in context
            context['retry_result'] = {
                'success': True,
                'txid': txid,
                'nonce': retry_nonce,
                'block_height': original_block_height
            }
            
            return True
            
        except Exception as e:
            error_str = str(e)
            print(f"{Colors.format_error(f'✗ Re-submission failed')}: {error_str}")
            
            context['retry_result'] = {
                'success': False,
                'error': error_str,
                'nonce': retry_nonce,
                'block_height': original_block_height
            }
            
            # Don't raise - let forensics analyze the retry failure
            return True

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
    runner.modules['transaction'] = StressTestTransaction()
    runner.modules['forensics'] = StressTestForensics()
    
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