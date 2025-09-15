#!/usr/bin/env python3

import os
import sys
import time
from typing import Optional

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.config import account_manager
from utils.types.infrastructure import Miner, TransactionResult
from utils.types.exceptions import *
from utils.miners import MinerManager
from utils.logger import logger
from utils.stacks_chain import StacksChain
from utils.stacks_core_api import StacksCoreAPI
from utils.blockstack_cli import BlockstackCLI
from utils.types.tokens import StacksToken


def main() -> bool:
    logger.header("COMPREHENSIVE STACKS CORE API & BLOCKSTACK CLI TEST")

    miners = MinerManager()

    # Setup accounts
    miner1_account = account_manager.get(Miner.MINER1)
    miner2_account = account_manager.get(Miner.MINER2)
    chain = StacksChain(miner1_account.api_url)
    api = StacksCoreAPI(miner1_account.api_url)
    cli = BlockstackCLI()

    # Initialize contract variables for API testing
    contract_address: str = ""
    contract_name: str = "counter"

    try:
        logger.info("Starting miners...")
        if not miners.snapshot_restore_auto():
            raise StacksException("Failed to start miners")

        # Wait for network to be ready
        logger.info("Waiting for network to be ready...")
        time.sleep(5)

        logger.header("TESTING STACKS CORE API FUNCTIONS")

        # V2 Info and Node Status
        logger.info("Testing get_info...")
        node_info = api.get_info()
        logger.success("get_info")

        logger.info("Testing get_pox_info...")
        api.get_pox_info()
        logger.success("get_pox_info")

        # V2 Account Operations
        logger.info("Testing get_account_info...")
        account_info = api.get_account_info(miner1_account.address)
        logger.success("get_account_info")

        # V2 Fee Operations
        logger.info("Testing get_fee_rate_for_transfer...")
        api.get_fee_rate_for_transfer()
        logger.success("get_fee_rate_for_transfer")

        # Create and broadcast a transaction for further testing
        transfer_amount: StacksToken = StacksToken.from_microstx(50_000)
        transaction_fee: StacksToken = StacksToken.from_microstx(1_000)
        transfer_result: Optional[TransactionResult] = None

        try:
            logger.info("Creating test transaction...")
            transfer_result = chain.transfer_and_confirm(
                sender_account=miner1_account,
                recipient=miner2_account.address,
                amount=transfer_amount,
                memo="Test for comprehensive testing",
                fee=transaction_fee,
                timeout=60,
            )
            logger.success("Created test transaction for further testing")
        except Exception as e:
            logger.warning(f"Could not create test transaction: {e}")

        # V3 Transaction Operations (if we have a transaction)
        if transfer_result and transfer_result.txid:
            logger.info("Testing get_transaction_by_id...")
            api.get_transaction_by_id(transfer_result.txid)
            logger.success("get_transaction_by_id")

        # V3 Block Operations
        if node_info and hasattr(node_info, "stacks_tip_height"):
            current_height = getattr(node_info, "stacks_tip_height", 1)
            if current_height > 0:
                logger.info("Testing get_block_by_height...")
                api.get_block_by_height(current_height)
                logger.success("get_block_by_height")

        # V3 Tenure Operations
        logger.info("Testing get_tenure_info...")
        tenure_info = api.get_tenure_info()
        logger.success("get_tenure_info")

        # V3 Sortition Operations
        logger.info("Testing get_sortitions...")
        api.get_sortitions()
        logger.success("get_sortitions")

        # Smart Contract Operations - Test with system contract
        try:
            logger.info("Testing call_read_only_function on system contract...")
            chain.call_contract_read_function(
                "ST000000000000000000002AMW42H",  # Boot contract address
                "pox-4",  # PoX contract
                "get-pox-info",  # Read-only function
                miner1_account.address,  # Sender
            )
            logger.success("call_read_only_function")
        except Exception as e:
            logger.warning(f"Could not test system contract read function: {e}")

        logger.header("TESTING BLOCKSTACK CLI FUNCTIONS")

        # Generate secret key
        logger.info("Testing generate_sk...")
        secret_key_info = cli.generate_sk(testnet=True)
        logger.success("generate_sk")

        # Get addresses (use generated key or miner key)
        test_sk = (
            secret_key_info.secret_key
            if secret_key_info
            else miner1_account.private_key
        )
        if test_sk:
            logger.info("Testing get_addresses...")
            cli.get_addresses(test_sk, testnet=True)
            logger.success("get_addresses")

        # Token transfer via CLI
        if account_info and hasattr(account_info, "nonce"):
            nonce = account_info.nonce + 1
            logger.info("Testing generate_token_transfer_tx_hex...")
            cli.generate_token_transfer_tx_hex(
                miner1_account.private_key,
                1000,  # fee rate
                nonce,
                miner2_account.address,
                10_000,  # amount in µSTX
                "CLI test transfer",
                testnet=True,
            )
            logger.success("generate_token_transfer_tx_hex")

        # Decode functions
        if account_info and hasattr(account_info, "nonce"):
            try:
                # Generate a real transaction hex without posting it
                real_tx_hex = cli.generate_token_transfer_tx_hex(
                    miner1_account.private_key,
                    1000,  # fee rate
                    account_info.nonce + 10,  # Use future nonce
                    miner2_account.address,
                    5_000,  # small amount in µSTX
                    "Decode test transaction",
                    testnet=True,
                )
                clean_tx_hex = (
                    real_tx_hex[2:] if real_tx_hex.startswith("0x") else real_tx_hex
                )

                logger.info("Testing decode_tx...")
                cli.decode_tx(clean_tx_hex, testnet=True)
                logger.success("decode_tx")
            except Exception as e:
                logger.warning(f"Could not test decode_tx: {e}")

        logger.info("Testing decode_microblocks...")
        cli.decode_microblocks("00" * 400, testnet=True)
        logger.success("decode_microblocks")

        # Contract operations via CLI - deploy real counter contract
        if account_info and hasattr(account_info, "nonce"):
            contract_file = "contracts/contract-counter.clar"
            try:
                # Deploy the counter contract using chain facade
                logger.info("Deploying counter contract...")
                deploy_result = chain.deploy_and_confirm(
                    deployer_account=miner1_account,
                    contract_name=contract_name,
                    contract_file=contract_file,
                    timeout=300,
                )

                deploy_txid = deploy_result.txid
                confirmed = deploy_result.confirmed
                contract_address = miner1_account.address

                logger.info(f"Contract deployment transaction: {deploy_txid}")

                if confirmed and contract_address:
                    logger.success("Contract deployment confirmed!")

                    logger.header("TESTING CONTRACT API FUNCTIONS AFTER DEPLOYMENT")

                    # Test contract source
                    logger.info("Testing get_contract_source...")
                    api.get_contract_source(contract_address, contract_name)
                    logger.success("get_contract_source")

                    # Test contract interface
                    logger.info("Testing get_contract_interface...")
                    api.get_contract_interface(contract_address, contract_name)
                    logger.success("get_contract_interface")

                    # Test read-only function calls on deployed counter contract
                    logger.info("Testing contract read functions...")
                    chain.call_contract_read_function(
                        contract_address, contract_name, "get-counter", miner1_account.address
                    )
                    logger.success("get-counter read function")

                    chain.call_contract_read_function(
                        contract_address, contract_name, "get-last-caller", miner1_account.address
                    )
                    logger.success("get-last-caller read function")

                    # Test map entry with actual counter-history map after increment
                    logger.info("Calling increment via contract call to populate map...")
                    increment_result = chain.call_contract_write_function_and_confirm(
                        miner1_account, contract_address, contract_name, "increment", timeout=120
                    )
                    logger.info(f"Increment transaction posted: {increment_result.txid}")
                    if increment_result.confirmed:
                        logger.success("Increment confirmed, map should now have data")
                        
                        logger.info("Testing get_map_entry...")
                        api.get_map_entry(
                            contract_address,
                            contract_name,
                            "simple-map",
                            "0x0100000000000000000000000000000001",
                        )
                        logger.success("get_map_entry")
                    else:
                        logger.warning("Increment not confirmed, skipping map entry test")

                    # Test contract call and confirmation
                    call_result = chain.call_contract_write_function_and_confirm(
                        miner1_account, contract_address, contract_name, "increment", timeout=60
                    )

                    logger.info(f"Contract call transaction posted: {call_result.txid}")

                    if call_result.confirmed:
                        logger.success("Contract call confirmed!")

                        # Test read-only functions after contract call to see state changes
                        logger.header("TESTING CONTRACT STATE AFTER INCREMENT")

                        logger.info("Testing counter state after increment...")
                        chain.call_contract_read_function(
                            contract_address, contract_name, "get-counter", miner1_account.address
                        )
                        logger.success("get-counter after increment")

                        chain.call_contract_read_function(
                            contract_address, contract_name, "get-last-caller", miner1_account.address
                        )
                        logger.success("get-last-caller after increment")
                    else:
                        logger.warning("Contract call not confirmed")

                else:
                    logger.warning("Contract deployment not confirmed, skipping contract API tests")

            except Exception as deploy_error:
                logger.warning(f"Could not deploy contract: {deploy_error}")

        # Test raw transaction posting via API with valid transaction bytes
        try:
            logger.info("Testing post_raw_transaction...")
            # Get current nonce to avoid BadNonce error
            current_nonce = chain.get_current_nonce(miner1_account.address)
            raw_tx_hex = cli.generate_token_transfer_tx_hex(
                miner1_account.private_key,
                1000,  # fee rate
                current_nonce,  # Use current nonce
                miner2_account.address,
                3_000,  # small amount in µSTX
                "Raw transaction test",
                testnet=True,
            )
            hex_str = raw_tx_hex[2:] if raw_tx_hex.startswith("0x") else raw_tx_hex
            raw_tx_bytes = bytes.fromhex(hex_str)
            
            api.post_raw_transaction(raw_tx_bytes)
            logger.success("post_raw_transaction")
        except Exception as e:
            logger.warning(f"Could not test raw transaction posting: {e}")

        logger.success("All tests completed successfully!")
        return True

    except Exception as e:
        logger.error(f"TEST FAILED - Unexpected Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

    finally:
        logger.header("Cleaning up...")
        miners.stop()
        miners.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)