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
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.logger import logger
from utils.stacks.config import account_manager
from utils.types.stacks.infrastructure import Miner
from utils.stacks.stacks_chain import StacksChain
from utils.types.tokens import StacksToken
from utils.hiro.hiro_utils import (
    fetch_contract_data,
    replicate_contract_call_events,
    call_read_only_functions,
)
from utils.hiro.hiro_manager import (
    extract_contract_metadata,
    extract_contract_events,
)
from utils.templates.recipe import RecipeTemplate


# Target transaction for this example - a contract deployment
TARGET_TX_ID = "0x8acc030ea9ba31fbcb1821fcdb671c542e90ec9dfe87c67979e6bac3f47c891b"


class ContractReplicationRecipe(RecipeTemplate):
    """Recipe for replicating a contract from mainnet."""

    def _run_recipe(self) -> bool:
        # Start miners
        if not self.miners.snapshot_restore_auto():
            logger.error("Failed to start miners")
            return False

        # First fetch the data
        data_file = fetch_contract_data(TARGET_TX_ID)

        if data_file:
            logger.header("REPLICATING CONTRACT FROM MAINNET DATA")

            # Load the data
            logger.header("Step 1: Load mainnet data")
            with open(data_file, "r") as f:
                data = json.load(f)

            # Extract contract metadata using utility function
            contract_metadata = extract_contract_metadata(data)

            logger.info(f"Contract name: {contract_metadata.contract_name}")
            logger.info(f"Source code: {len(contract_metadata.source_code)} chars")
            logger.success("Data loaded")

            # Extract contract call events using utility function (filters and parses automatically)
            contract_call_events = extract_contract_events(data)

            logger.info(f"Events to replicate: {len(contract_call_events)}")

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
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".clar", delete=False
            ) as f:
                f.write(contract_metadata.source_code)
                contract_file = f.name

            try:
                deployment_fee = StacksToken.from_microstx(50_000)
                result = chain.deploy_and_confirm(
                    deployer_account=deployer_account,
                    contract_name=contract_metadata.contract_name,
                    contract_file=contract_file,
                    fee=deployment_fee,
                    timeout=120,
                )

                if not result.confirmed:
                    logger.error(f"Contract deployment failed: {result.txid}")
                    return False

                logger.success(f"Contract deployed: {result.txid}")
                local_contract_id = (
                    f"{deployer_account.address}.{contract_metadata.contract_name}"
                )
                logger.success(f"Local contract ID: {local_contract_id}")
            finally:
                os.unlink(contract_file)

            logger.info(f"Available public functions: {contract_metadata.abi_functions.public_names}")

            # Replicate events (contract calls)
            logger.header("Step 4: Replicate contract calls from events")

            replication_results = replicate_contract_call_events(
                contract_call_events=contract_call_events,
                contract_metadata=contract_metadata,
                chain=chain,
                caller_account=caller_account,
                deployer_address=deployer_account.address,
                fee=StacksToken.from_microstx(10_000),
                timeout=120,
            )

            # Call all read-only functions
            logger.header("Step 5: Call all read-only functions")

            read_only_results = call_read_only_functions(
                contract_metadata=contract_metadata,
                chain=chain,
                caller_address=caller_account.address,
                deployer_address=deployer_account.address,
            )

            logger.header("REPLICATION COMPLETE")
            logger.success(f"Contract deployed: {local_contract_id}")

            # Count successful replications
            successful_replications = sum(1 for r in replication_results if r.confirmed)
            logger.success(
                f"Events replicated: {successful_replications}/{len(replication_results)}"
            )

            # Count successful read-only calls
            successful_reads = sum(1 for r in read_only_results if r.success)
            logger.success(
                f"Read-only functions called: {successful_reads}/{len(read_only_results)}"
            )
        return False


if __name__ == "__main__":
    recipe = ContractReplicationRecipe()
    success = recipe.execute()
    sys.exit(0 if success else 1)
