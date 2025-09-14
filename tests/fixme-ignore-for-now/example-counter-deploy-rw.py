#!/usr/bin/env python3

import os
import sys
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.config import AccountManager, Miner
from utils.miners import MinerManager
from utils.logger import Colors
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.stacks_core_api import StacksCoreAPIWrapper


def main():
    """Execute the contract deployment and interaction test"""
    print(f"{Colors.format_dim('=' * 60)}")
    print(
        f"{Colors.format_header('CONTRACT COUNTER DEPLOYMENT AND INTERACTIONS TEST')}"
    )
    print(f"{Colors.format_dim('=' * 60)}")

    # Raw minimal setup
    miners = MinerManager()
    account = AccountManager.get(Miner.MINER1)
    api = StacksCoreAPIWrapper(base_url=account.api_url)
    cli = BlockstackCLIWrapper()

    try:
        # Start miners
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not miners.snapshot_restore_auto():
            raise RuntimeError("Failed to start miners")

        # Step 1: Deploy counter contract
        print(f"\n{Colors.format_header('Step 1: Deploy counter contract')}")
        print(f"{Colors.format_info('Contract')}: {Colors.format_dim('mycontract')}")
        print(
            f"{Colors.format_info('File')}: {Colors.format_dim('contracts/contract-counter.clar')}"
        )

        account_info = api.get_account_info(account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)

        tx_hex = cli.generate_contract_deploy_tx_hex(
            account.private_key,
            5000,
            initial_nonce,
            "mycontract",
            os.path.join(
                os.path.dirname(__file__), "..", "contracts/contract-counter.clar"
            ),
        )
        deploy_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        print(
            f"{Colors.format_success('Contract deployed')}: {Colors.format_info(deploy_txid)}"
        )

        if not wait_for_tx_confirmation(
            api, account.address, initial_nonce, initial_height, timeout=120
        ):
            raise RuntimeError("Contract deployment confirmation timeout")
        logger.success("Contract mycontract deployment confirmed!")

        # Step 2: Read initial counter value
        logger.header("Step 2: Read initial counter")
        initial_counter = api.call_read_only_function(
            account.address, "mycontract", "get-counter", account.address, []
        )
        logger.success("Read-only call successful")
        logger.standard("Response", json.dumps(initial_counter, indent=2))

        # Step 3: Read initial last caller
        logger.header("Step 3: Read initial last caller")
        initial_caller = api.call_read_only_function(
            account.address, "mycontract", "get-last-caller", account.address, []
        )
        logger.success("Read-only call successful")
        logger.standard("Response", json.dumps(initial_caller, indent=2))

        # Step 4: Increment counter
        logger.header("Step 4: Increment counter")
        account_info = api.get_account_info(account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)

        tx_hex = cli.generate_contract_call_tx_hex(
            account.private_key,
            5000,
            initial_nonce,
            account.address,
            "mycontract",
            "increment",
            [],
        )
        increment_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        logger.success(f"Contract call submitted: {increment_txid}")

        if not wait_for_tx_confirmation(
            api, account.address, initial_nonce, initial_height, timeout=120
        ):
            raise RuntimeError("Contract call confirmation timeout")
        logger.success("increment call confirmed!")

        # Step 5: Read counter after increment
        logger.header("Step 5: Read counter after increment")
        after_increment_counter = api.call_read_only_function(
            account.address, "mycontract", "get-counter", account.address, []
        )
        logger.success("Read-only call successful")
        logger.standard("Response", json.dumps(after_increment_counter, indent=2))

        # Step 6: Read last caller after increment
        logger.header("Step 6: Read last caller after increment")
        after_increment_caller = api.call_read_only_function(
            account.address, "mycontract", "get-last-caller", account.address, []
        )
        logger.success("Read-only call successful")
        logger.standard("Response", json.dumps(after_increment_caller, indent=2))

        # Step 7: Reset counter
        logger.header("Step 7: Reset counter")
        account_info = api.get_account_info(account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)

        tx_hex = cli.generate_contract_call_tx_hex(
            account.private_key,
            5000,
            initial_nonce,
            account.address,
            "mycontract",
            "reset",
            [],
        )
        reset_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
        logger.success(f"Contract call submitted: {reset_txid}")

        if not wait_for_tx_confirmation(
            api, account.address, initial_nonce, initial_height, timeout=120
        ):
            raise RuntimeError("Contract call confirmation timeout")
        logger.success("reset call confirmed!")

        # Step 8: Read counter after reset
        logger.header("Step 8: Read counter after reset")
        after_reset_counter = api.call_read_only_function(
            account.address, "mycontract", "get-counter", account.address, []
        )
        logger.success("Read-only call successful")
        logger.standard("Response", json.dumps(after_reset_counter, indent=2))

        # Step 9: Read last caller after reset
        logger.header("Step 9: Read last caller after reset")
        after_reset_caller = api.call_read_only_function(
            account.address, "mycontract", "get-last-caller", account.address, []
        )
        logger.success("Read-only call successful")
        logger.standard("Response", json.dumps(after_reset_caller, indent=2))

        # Final summary
        logger.dim("=" * 60)
        logger.header("FINAL RESULT")
        logger.dim("=" * 60)

        logger.standard("Deploy TXID", deploy_txid)
        logger.standard("Increment TXID", increment_txid)
        logger.standard("Reset TXID", reset_txid)

        return True

    except Exception as e:
        logger.error(f"TEST FAILED: {str(e)}")
        return False

    finally:
        # Cleanup
        logger.header("Cleaning up...")
        miners.stop()
        miners.cleanup()


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)
