#!/usr/bin/env python3

import sys
import os
import time

# --- Setup Python Path ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.node_manager import NodeManager
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.stacks_core_api import StacksCoreAPIWrapper
from utils.colors import logger, Colors
from utils.config import ACCOUNTS

# --- Test Constants ---
CONTRACT_FILE = "contracts/contract-counter.clar"
CONTRACT_NAME = "mycontract"
DEPLOYER_ACCOUNT = ACCOUNTS["miner1"]
HIGH_FEE = 250000 

def wait_for_tx_confirmation(apis: dict[str, StacksCoreAPIWrapper], txid: str, timeout: int = 120) -> bool:
    """
    Polls all available miner APIs directly for a confirmed transaction status.
    This is the most robust method as it simply waits for the final desired state.
    """
    start_time = time.time()
    logger.info(f"Waiting for on-chain confirmation of tx: {Colors.format_grey(txid)}...")
    
    while time.time() - start_time < timeout:
        for miner_name, api in apis.items():
            try:
                tx_info = api.get_transaction_by_id(txid)
                # If we get a response (not a 404), the transaction is known to the node.
                if tx_info:
                    if tx_info.get('tx_status') == 'success':
                        logger.info(f"Transaction {Colors.format_grey(txid)} {Colors.format_success(f'confirmed on-chain by {miner_name}!')}")
                        return True
                    # If it failed for any reason, stop immediately.
                    elif tx_info.get('tx_status') != 'pending':
                        logger.error(f"Transaction {Colors.format_grey(txid)} {Colors.format_fail('failed')} on {miner_name} with status: {tx_info.get('tx_status')}")
                        logger.error(f"Reason: {tx_info.get('tx_result', {}).get('repr', 'N/A')}")
                        return False
            except Exception:
                # This will catch connection errors and cases where the API returns a 404
                # We simply ignore them and try the next miner or the next polling cycle.
                pass
        
        # Wait before the next round of polling
        time.sleep(3)

    logger.error(f"Timeout waiting for transaction {txid} to be confirmed on-chain.")
    return False

def main():
    """Main test function that runs all steps sequentially."""
    node = NodeManager()
    cli = BlockstackCLIWrapper()
    apis = node.apis
    primary_api = apis["miner1"]
    
    errors = []

    try:
        logger.info(f"{Colors.format_header('STEP 1: Starting Node Environment')}")
        if not node.start_node():
            raise RuntimeError("Failed to start the node environment. Aborting test.")

        logger.info(f"{Colors.format_header('STEP 2: Deploying Counter Contract')}")
        try:
            current_nonce = primary_api.get_account_info(DEPLOYER_ACCOUNT.address)['nonce']
            tx_hex = cli.publish_contract(
                publisher_sk=DEPLOYER_ACCOUNT.private_key, fee_rate=HIGH_FEE, nonce=current_nonce,
                contract_name=CONTRACT_NAME, file_name=CONTRACT_FILE, testnet=True
            )
            if not tx_hex: raise RuntimeError("CLI failed to generate a transaction hex.")
            txid = primary_api.post_raw_transaction(bytes.fromhex(tx_hex))
            if not txid: raise RuntimeError("API rejected the transaction broadcast.")
            
            if not wait_for_tx_confirmation(apis, txid):
                raise RuntimeError("Contract deployment transaction failed to confirm.")
            logger.info(f"{Colors.format_success('Contract deployed successfully.')}")
        except Exception as e:
            errors.append(f"FAIL: Contract Deployment - {e}")

        if not errors:
            logger.info(f"{Colors.format_header('STEP 3: Reading Initial State')}")
            try:
                response = primary_api.call_read_only_function(DEPLOYER_ACCOUNT.address, CONTRACT_NAME, 'get-counter', DEPLOYER_ACCOUNT.address, [])
                if response['result'] != 'u0':
                    errors.append(f"FAIL: Initial counter was not 0, got {response['result']}")
                
                response = primary_api.call_read_only_function(DEPLOYER_ACCOUNT.address, CONTRACT_NAME, 'get-last-caller', DEPLOYER_ACCOUNT.address, [])
                if response['result'] != 'none':
                    errors.append(f"FAIL: Initial last-caller was not none, got {response['result']}")
                
                logger.info(f"{Colors.format_success('Initial state verified.')}")
            except Exception as e:
                errors.append(f"FAIL: Reading initial state - {e}")
        
        if not errors:
            logger.info(f"{Colors.format_header('STEP 4: Calling increment()')}")
            try:
                current_nonce = primary_api.get_account_info(DEPLOYER_ACCOUNT.address)['nonce']
                tx_hex = cli.call_contract(
                    DEPLOYER_ACCOUNT.private_key, HIGH_FEE, current_nonce, DEPLOYER_ACCOUNT.address, 
                    CONTRACT_NAME, "increment", [], testnet=True
                )
                if not tx_hex: raise RuntimeError("CLI failed to generate a transaction hex for increment.")
                txid = primary_api.post_raw_transaction(bytes.fromhex(tx_hex))
                if not txid: raise RuntimeError("API rejected the increment transaction broadcast.")
                if not wait_for_tx_confirmation(apis, txid):
                    raise RuntimeError("Increment transaction failed to confirm.")
                logger.info(f"{Colors.format_success('increment() called successfully.')}")
            except Exception as e:
                errors.append(f"FAIL: Calling increment - {e}")

        if not errors:
            logger.info(f"{Colors.format_header('STEP 5: Reading State After Increment')}")
            try:
                response = primary_api.call_read_only_function(DEPLOYER_ACCOUNT.address, CONTRACT_NAME, 'get-counter', DEPLOYER_ACCOUNT.address, [])
                if response['result'] != 'u1':
                    errors.append(f"FAIL: Counter was not 1 after increment, got {response['result']}")
                
                response = primary_api.call_read_only_function(DEPLOYER_ACCOUNT.address, CONTRACT_NAME, 'get-last-caller', DEPLOYER_ACCOUNT.address, [])
                expected_caller = f"(some '{DEPLOYER_ACCOUNT.address}')"
                if response['result'] != expected_caller:
                     errors.append(f"FAIL: Last caller was not correct. Expected '{expected_caller}', got '{response['result']}'")
                
                logger.info(f"{Colors.format_success('State after increment verified.')}")
            except Exception as e:
                errors.append(f"FAIL: Reading state after increment - {e}")

    except Exception as e:
        logger.critical(f"A critical error occurred: {e}", exc_info=True)
        errors.append(f"CRITICAL: {e}")
    finally:
        logger.info(f"{Colors.format_header('FINAL STEP: Stopping Node Environment')}")
        node.stop_node()

    print("\n" + "="*60)
    logger.info(f"{Colors.format_header('TEST SUMMARY')}")
    print("="*60)
    if not errors:
        logger.info(f"{Colors.format_success('✓ ALL TESTS PASSED')}")
        sys.exit(0)
    else:
        logger.error(f"{Colors.format_fail(f'✗ TEST FAILED WITH {len(errors)} ERROR(S)')}")
        for i, err in enumerate(errors):
            logger.error(f"  {i+1}: {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()