import json
from .base import StacksTestBase, Colors
from .transaction import Transaction

class Forensics(StacksTestBase):
    """Utilities for diagnostic analysis, designed to be used as recipe steps."""

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
            verification_result = tx_utility.verify_transaction_direct(
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
            verification_result: The result dictionary from verify_transaction_direct
            
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
            verification_result: The result dictionary from verify_transaction_direct
            
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