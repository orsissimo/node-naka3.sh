#!/usr/bin/env python3
"""
Contract Operations Example

This script demonstrates:
1. Fetching a contract deployment transaction from mainnet
2. Extracting contract information and events
3. Deploying the contract locally
4. Calling contract functions based on events
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
from utils.stacks.stacks_contract_macros import ContractMacros
from utils.stacks.hiro_json_handler import TransactionHandler
from utils.templates.recipe_naka3 import RecipeTemplate


class Recipe(RecipeTemplate):
    """Recipe for demonstrating contract operations from mainnet data."""

    def _run_recipe(self) -> bool:
        # Start miners
        if not self.miners.snapshot_restore_auto():
            logger.error("Failed to start miners")
            return False

        logger.header("CONTRACT OPERATIONS FROM MAINNET DATA")

        # Fetch and extract transaction data
        logger.header("Step 1: Fetch mainnet data")
        TARGET_TX_ID = "0x8acc030ea9ba31fbcb1821fcdb671c542e90ec9dfe87c67979e6bac3f47c891b"

        from utils.stacks.hiro_api import HiroAPI
        handler = TransactionHandler(TARGET_TX_ID, api=HiroAPI.mainnet())
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
        if contract_metadata.contract_events is not None:
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

        # Create contract macros helper
        macros = ContractMacros(chain, contract_metadata)

        # Call events (contract calls)
        logger.header("Step 4: Call contract functions from events")

        event_results = macros.call_events(
            caller_account=caller_account,
            local_deployer_address=deployer_account.address,
            fee=StacksToken.from_microstx(10_000),
            timeout=120,
        )

        # Call all read-only functions
        logger.header("Step 5: Call all read-only functions")

        read_only_results = macros.call_read_only_functions(
            caller_address=caller_account.address,
            local_deployer_address=deployer_account.address,
        )

        logger.header("OPERATION COMPLETE")
        logger.success(f"Contract deployed: {result.txid}")

        # Count successful event calls
        successful_events = sum(1 for r in event_results if r.confirmed)
        logger.success(
            f"Events called: {successful_events}/{len(event_results)}"
        )

        # Count successful read-only calls
        successful_reads = sum(1 for r in read_only_results if r.success)
        logger.success(
            f"Read-only functions called: {successful_reads}/{len(read_only_results)}"
        )

        return False


if __name__ == "__main__":
    recipe = Recipe()
    success = recipe.execute()
    sys.exit(0 if success else 1)

# TODO: Definire un punto di ingresso unico per le ricette - investigare e creare un runner: ./runner.py --recipe example_contract_replicate "+params"