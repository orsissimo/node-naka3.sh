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

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.logger import logger
from utils.base import account_manager, PROJECT_ROOT
from utils.types.stacks.infrastructure import Miner
from utils.stacks.stacks_chain import StacksChain
from utils.types.tokens import StacksToken
from utils.hiro.replicators import ContractReplicator
from utils.hiro.json_handler import TransactionHandler
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

        logger.header("REPLICATING CONTRACT FROM MAINNET DATA")

        # Step 1: Fetch and extract transaction data
        logger.header("Step 1: Fetch mainnet data")
        handler = TransactionHandler(TARGET_TX_ID)
        tmp_dir = os.path.join(PROJECT_ROOT, "tmp")
        metadata, data_file = handler.fetch_extract_and_save(tmp_dir)

        if metadata is None:
            logger.error("Failed to fetch transaction metadata")
            return False

        # Ensure this is a contract deployment
        from utils.types.hiro.infrastructure import ContractMetadata
        if not isinstance(metadata, ContractMetadata):
            logger.error(f"Expected contract deployment, got {type(metadata).__name__}")
            return False

        contract_metadata = metadata

        logger.info(f"Contract name: {contract_metadata.contract_name}")
        logger.info(f"Source code: {len(contract_metadata.source_code)} chars")
        logger.info(
            f"Events to replicate: {len(contract_metadata.contract_events)}"
        )
        logger.success(f"Data loaded and saved to: {data_file}")

        # Setup local environment
        logger.header("Step 2: Setup local environment")
        deployer_account = account_manager.get(Miner.MINER1)
        caller_account = account_manager.get(Miner.MINER2)
        chain = StacksChain(deployer_account.api_url)

        logger.info(f"Mainnet deployer: {deployer_account.address}")
        logger.info(f"Local deployer: {caller_account.address}")

        # Deploy contract
        logger.header("Step 3: Deploy contract")

        deployment_fee = StacksToken.from_microstx(50_000)
        result = chain.deploy_and_confirm(
            deployer_account=deployer_account,
            contract_name=contract_metadata.contract_name,
            contract_source=contract_metadata.source_code,
            fee=deployment_fee,
            timeout=120,
        )

        if not result.confirmed:
            logger.error(f"Contract deployment failed: {result.txid}")
            return False

        logger.success(f"Contract deployed: {result.txid}")

        logger.info(
            f"Available public functions: {contract_metadata.abi_functions.public_names}"
        )
        logger.info(
            f"Available read-only functions: {contract_metadata.abi_functions.read_only_names}"
        )

        # Create replicator
        replicator = ContractReplicator(chain, contract_metadata)

        # Replicate events (contract calls)
        logger.header("Step 4: Replicate contract calls from events")

        replication_results = replicator.replicate_events(
            caller_account=caller_account,
            local_deployer_address=deployer_account.address,
            fee=StacksToken.from_microstx(10_000),
            timeout=120,
        )

        # Call all read-only functions
        logger.header("Step 5: Call all read-only functions")

        read_only_results = replicator.call_read_only_functions(
            caller_address=caller_account.address,
            local_deployer_address=deployer_account.address,
        )

        logger.header("REPLICATION COMPLETE")
        logger.success(f"Contract deployed: {result.txid}")

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
