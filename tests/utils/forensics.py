import json
from .base import StacksTestBase, Colors
from .transaction import Transaction

class Forensics(StacksTestBase):
    """Utilities for diagnostic analysis, designed to be used as recipe steps."""

    def verify_batch_limit_test(self, context: dict):
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
            # We call verify_transaction_direct which includes the detailed logging you wanted.
            verification_result = tx_utility.verify_transaction_direct(
                miner=batch_report['from_miner'],
                txid=tx_info['txid']
            )
            
            tx_data = verification_result.get('transaction_data', {})
            tx_status = tx_data.get('tx_status', 'unknown')
            
            if verification_result['success'] and tx_status == 'success':
                # The detailed log is already printed by verify_transaction_direct
                print(f"{nonce_str}: {Colors.format_success('✓ Verification PASSED')}")
            else:
                all_verified_successfully = False
                error_info = verification_result.get('error', f'Final status was: {tx_status}')
                print(f"{nonce_str}: {Colors.format_error('✗ Verification FAILED')} ({error_info})")

        if not all_verified_successfully:
            raise RuntimeError("Test failed: Not all submitted transactions were successfully confirmed on-chain.")
            
        print(f"\n{Colors.format_success('✓ Condition 2 Met')}: All {len(batch_report['successful_submissions'])} submitted transactions were successfully verified.")
        
        print(f"\n{Colors.format_success('✓ ALL CONDITIONS MET - TEST PASSED')}")
        return True # Return True to the runner, indicating the step was successful.