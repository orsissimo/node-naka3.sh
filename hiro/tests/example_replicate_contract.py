#!/usr/bin/env python3
"""
Contract Call Replication Example

This script demonstrates:
1. Fetching a contract deployment transaction from mainnet
2. Extracting contract information and events
3. Replicating the deployment locally
4. Replicating all contract calls (events) in chronological order
5. Calling all read-only functions
"""

import os
import sys
import json
import tempfile

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from utils.logger import logger
from utils.config import account_manager
from utils.types.infrastructure import Miner
from utils.stacks_chain import StacksChain
from utils.types.tokens import StacksToken
from hiro.hiro_api import StacksMainnetAPI
from hiro.utils.formatter import ResponseCollection
from utils.templates.recipe import RecipeTemplate


def fetch_contract_call_data():
    """Fetch contract call transaction and related data from mainnet."""

    # Target transaction - a contract deployment
    TARGET_TX_ID = "0x8acc030ea9ba31fbcb1821fcdb671c542e90ec9dfe87c67979e6bac3f47c891b"

    api = StacksMainnetAPI()
    collection = ResponseCollection(TARGET_TX_ID)

    logger.header("FETCHING CONTRACT CALL DATA FROM MAINNET")

    # Step 1: Get transaction details
    logger.header("Step 1: Fetch transaction details")
    logger.info(f"Transaction ID: {TARGET_TX_ID}")

    contract_id = None

    try:
        tx = api.get_transaction_by_id(TARGET_TX_ID)
        collection.add_endpoint(
            method_name="get_transaction_by_id",
            endpoint=f"/extended/v1/tx/{TARGET_TX_ID}",
            response=tx
        )
        logger.success(f"Transaction fetched: {tx.tx_type}")
        logger.info(f"Status: {tx.tx_status}")

        # Extract contract ID for subsequent calls
        if tx.contract_call:
            contract_id = tx.contract_call.contract_id
            logger.info(f"Contract call detected")
            logger.info(f"Contract ID: {contract_id}")
            logger.info(f"Function: {tx.contract_call.function_name}")
        elif tx.smart_contract:
            contract_id = tx.smart_contract.contract_id
            logger.info(f"Contract deployment detected")
            logger.info(f"Contract ID: {contract_id}")
        else:
            logger.warning(f"No contract information found in transaction")
            contract_id = None

    except Exception as e:
        logger.error(f"Failed to fetch transaction: {e}")
        collection.add_endpoint(
            method_name="get_transaction_by_id",
            endpoint=f"/extended/v1/tx/{TARGET_TX_ID}",
            error=str(e)
        )
        return None

    # Step 2: Get raw transaction
    logger.header("Step 2: Fetch raw transaction")

    try:
        raw_tx = api.get_raw_transaction_by_id(TARGET_TX_ID)
        collection.add_endpoint(
            method_name="get_raw_transaction_by_id",
            endpoint=f"/extended/v1/tx/{TARGET_TX_ID}/raw",
            response=raw_tx
        )
        logger.success(f"Raw transaction fetched: {len(raw_tx)} chars")
    except Exception as e:
        logger.error(f"Failed to fetch raw transaction: {e}")
        collection.add_endpoint(
            method_name="get_raw_transaction_by_id",
            endpoint=f"/extended/v1/tx/{TARGET_TX_ID}/raw",
            error=str(e)
        )

    # Step 3: Get contract details
    if contract_id:
        logger.header("Step 3: Fetch contract details")

        try:
            contract = api.get_contract_by_id(contract_id)
            collection.add_endpoint(
                method_name="get_contract_by_id",
                endpoint=f"/extended/v1/contract/{contract_id}",
                response=contract
            )
            logger.success(f"Contract fetched: {contract.contract_id}")
            logger.info(f"Source code length: {len(contract.source_code)} chars")
        except Exception as e:
            logger.error(f"Failed to fetch contract: {e}")
            collection.add_endpoint(
                method_name="get_contract_by_id",
                endpoint=f"/extended/v1/contract/{contract_id}",
                error=str(e)
            )

        # Step 4: Get contract events
        logger.header("Step 4: Fetch contract events")

        try:
            events = api.get_contract_events_by_id(contract_id, limit=10)
            collection.add_endpoint(
                method_name="get_contract_events_by_id",
                endpoint=f"/extended/v1/contract/{contract_id}/events",
                response=events
            )
            logger.success(f"Contract events fetched: {len(events.results)} events")
        except Exception as e:
            logger.error(f"Failed to fetch contract events: {e}")
            collection.add_endpoint(
                method_name="get_contract_events_by_id",
                endpoint=f"/extended/v1/contract/{contract_id}/events",
                error=str(e)
            )

    # Save to output file
    output_file = "contract_call_mainnet_data.json"
    collection.save(output_file)

    logger.header("DATA COLLECTION COMPLETE")
    logger.success(f"All data saved to: {output_file}")
    logger.info(f"Endpoints called: {len(collection)}")

    return output_file


def replicate_contract_deployment(data_file: str):
    """
    Replicate contract deployment and all events from mainnet data.

    Args:
        data_file: Path to the JSON file with mainnet data
    """
    logger.header("REPLICATING CONTRACT FROM MAINNET DATA")

    # Load the data
    logger.header("Step 1: Load mainnet data")
    with open(data_file, 'r') as f:
        data = json.load(f)

    # Extract contract info
    contract_response = data["endpoints"]["get_contract_by_id"]["response"]
    contract_id_parts = contract_response["contract_id"].split(".")
    contract_name = contract_id_parts[1]
    contract_source = contract_response["source_code"]
    contract_abi = json.loads(contract_response["abi"])

    logger.info(f"Contract name: {contract_name}")
    logger.info(f"Source code: {len(contract_source)} chars")
    logger.success("Data loaded")

    # Extract events
    events_response = data["endpoints"]["get_contract_events_by_id"]["response"]
    events = events_response["results"]

    # Reverse to get chronological order (API returns newest first)
    events = list(reversed(events))

    logger.info(f"Events to replicate: {len(events)}")

    # Setup local environment
    logger.header("Step 2: Setup local environment")
    deployer_account = account_manager.get(Miner.MINER1)
    caller_account = account_manager.get(Miner.MINER2)
    chain = StacksChain(deployer_account.api_url)

    logger.info(f"Deployer: {deployer_account.address}")
    logger.info(f"Caller: {caller_account.address}")

    # Deploy contract
    logger.header("Step 3: Deploy contract")

    # Write contract source to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.clar', delete=False) as f:
        f.write(contract_source)
        contract_file = f.name

    try:
        deployment_fee = StacksToken.from_microstx(50_000)
        result = chain.deploy_and_confirm(
            deployer_account=deployer_account,
            contract_name=contract_name,
            contract_file=contract_file,
            fee=deployment_fee,
            timeout=120,
        )

        if not result.confirmed:
            logger.error(f"Contract deployment failed: {result.txid}")
            return False

        logger.success(f"Contract deployed: {result.txid}")
        local_contract_id = f"{deployer_account.address}.{contract_name}"
        logger.success(f"Local contract ID: {local_contract_id}")
    finally:
        os.unlink(contract_file)

    # Replicate events (contract calls)
    logger.header("Step 4: Replicate contract calls from events")

    for i, event in enumerate(events):
        if event["event_type"] == "smart_contract_log":
            contract_log = event["contract_log"]
            value_repr = contract_log["value"]["repr"]

            logger.info(f"Event {i+1}: {value_repr}")

            # Parse the event to determine function called
            # Events show: (tuple (caller '...') (event "incremented") (new-value u1))
            if '"incremented"' in value_repr:
                function_name = "increment"
                logger.info(f"Calling function: {function_name}")

                call_result = chain.call_contract_write_function_and_confirm(
                    caller_account=caller_account,
                    contract_address=deployer_account.address,
                    contract_name=contract_name,
                    function_name=function_name,
                    function_args=[],
                    fee=StacksToken.from_microstx(10_000),
                    timeout=120,
                )

                if call_result.confirmed:
                    logger.success(f"{function_name} confirmed: {call_result.txid}")
                else:
                    logger.error(f"{function_name} failed")

            elif '"reset"' in value_repr:
                function_name = "reset"
                logger.info(f"Calling function: {function_name}")

                call_result = chain.call_contract_write_function_and_confirm(
                    caller_account=caller_account,
                    contract_address=deployer_account.address,
                    contract_name=contract_name,
                    function_name=function_name,
                    function_args=[],
                    fee=StacksToken.from_microstx(10_000),
                    timeout=120,
                )

                if call_result.confirmed:
                    logger.success(f"{function_name} confirmed: {call_result.txid}")
                else:
                    logger.error(f"{function_name} failed")

    # Call all read-only functions
    logger.header("Step 5: Call all read-only functions")

    # Extract read-only functions from ABI
    read_only_functions = [
        func for func in contract_abi["functions"]
        if func["access"] == "read_only"
    ]

    logger.info(f"Found {len(read_only_functions)} read-only functions")

    for func in read_only_functions:
        function_name = func["name"]
        logger.info(f"Calling read-only: {function_name}")

        read_result = chain.call_contract_read_function(
            contract_address=deployer_account.address,
            contract_name=contract_name,
            function_name=function_name,
            sender=caller_account.address,
            function_args=[],
        )

        if read_result.okay:
            logger.success(f"{function_name}: {read_result.result}")
        else:
            logger.error(f"{function_name} failed: {read_result.cause}")

    logger.header("REPLICATION COMPLETE")
    logger.success(f"Contract deployed: {local_contract_id}")
    logger.success(f"Events replicated: {len(events)}")
    logger.success(f"Read-only functions called: {len(read_only_functions)}")

    return True


class ContractReplicationRecipe(RecipeTemplate):
    """Recipe for replicating a contract from mainnet."""

    def _run_recipe(self) -> bool:
        # Start miners
        if not self.miners.snapshot_restore_auto():
            logger.error("Failed to start miners")
            return False

        # First fetch the data
        data_file = fetch_contract_call_data()

        # Then replicate it locally
        if data_file:
            return replicate_contract_deployment(data_file)
        return False


if __name__ == "__main__":
    recipe = ContractReplicationRecipe()
    success = recipe.execute()
    sys.exit(0 if success else 1)
