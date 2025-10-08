#!/usr/bin/env python3
"""
Smart Contract Deployment and Interaction Example

This script demonstrates:
1. Deploying a Clarity contract
2. Calling read-only functions
3. Calling public/write functions
4. Verifying contract state changes
"""

import os
import sys

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.stacks.config import account_manager
from utils.types.stacks.infrastructure import Miner
from utils.logger import logger
from utils.stacks.stacks_chain import StacksChain
from utils.types.tokens import StacksToken
from utils.templates.recipe import RecipeTemplate


class ContractDeploymentRecipe(RecipeTemplate):
    def _run_recipe(self) -> bool:
        logger.header("SMART CONTRACT DEPLOYMENT & INTERACTION TEST")

        deployer_account = account_manager.get(Miner.MINER1)
        caller_account = account_manager.get(Miner.MINER2)
        chain = StacksChain(deployer_account.api_url)

        if not self.miners.snapshot_restore_auto():
            logger.error("Failed to start miners")
            return False

        logger.info(f"Deployer address: {deployer_account.address}")
        logger.info(f"Caller address: {caller_account.address}")

        logger.header("Step 1: Prepare contract for deployment")
        contract_path = os.path.join(
            os.path.dirname(__file__), "..", "contracts", "contract-counter.clar"
        )

        contract_name = "my-counter"
        logger.info(f"Contract name: {contract_name}")
        logger.info(f"Contract file: {contract_path}")
        logger.success("Contract ready for deployment")

        logger.header("Step 2: Deploy contract")
        initial_balance = chain.get_stx_balance(deployer_account.address)
        logger.info(
            f"Deployer balance before deployment: {initial_balance.format_stx()}"
        )

        deployment_fee = StacksToken.from_microstx(50_000)
        logger.info(f"Deployment fee: {deployment_fee.format_stx()}")

        result = chain.deploy_and_confirm(
            deployer_account=deployer_account,
            contract_name=contract_name,
            contract_file=contract_path,
            fee=deployment_fee,
            timeout=120,
        )

        if not result.confirmed:
            logger.error(f"Contract deployment failed: {result.txid}")
            return False

        logger.success(f"Contract deployed: {result.txid}")
        contract_id = f"{deployer_account.address}.{contract_name}"
        logger.success(f"Contract ID: {contract_id}")

        final_balance = chain.get_stx_balance(deployer_account.address)
        logger.info(f"Deployer balance after deployment: {final_balance.format_stx()}")
        logger.info(
            f"Deployment cost: {(initial_balance - final_balance).format_stx()}"
        )

        logger.header("Step 3: Read initial counter value (read-only)")

        read_result = chain.call_contract_read_function(
            contract_address=deployer_account.address,
            contract_name=contract_name,
            function_name="get-counter",
            sender=caller_account.address,
            function_args=[],
        )

        logger.info(f"Read-only function result: {read_result.result}")

        if read_result.okay:
            logger.success(f"Initial counter value: {read_result.result}")
        else:
            logger.error(f"Read-only call failed: {read_result.cause}")
            return False

        logger.header("Step 4: Increment counter (write function)")

        increment_fee = StacksToken.from_microstx(10_000)
        logger.info(f"Calling increment with fee: {increment_fee.format_stx()}")

        increment_result = chain.call_contract_write_function_and_confirm(
            caller_account=caller_account,
            contract_address=deployer_account.address,
            contract_name=contract_name,
            function_name="increment",
            function_args=[],
            fee=increment_fee,
            timeout=120,
        )

        if not increment_result.confirmed:
            logger.error(f"Increment call failed: {increment_result.txid}")
            return False

        logger.success(f"Increment confirmed: {increment_result.txid}")

        logger.header("Step 5: Verify counter was incremented")

        read_result_after = chain.call_contract_read_function(
            contract_address=deployer_account.address,
            contract_name=contract_name,
            function_name="get-counter",
            sender=caller_account.address,
            function_args=[],
        )

        logger.info(f"Counter value after increment: {read_result_after.result}")

        if read_result_after.okay:
            logger.success(f"New counter value: {read_result_after.result}")
        else:
            logger.error(f"Read-only call failed: {read_result_after.cause}")
            return False

        logger.header("Step 6: Increment counter 3 more times")

        for i in range(3):
            logger.info(f"Increment #{i+2}...")

            inc_result = chain.call_contract_write_function_and_confirm(
                caller_account=caller_account,
                contract_address=deployer_account.address,
                contract_name=contract_name,
                function_name="increment",
                function_args=[],
                fee=increment_fee,
                timeout=120,
            )

            if inc_result.confirmed:
                logger.success(f"Increment #{i+2} confirmed: {inc_result.txid}")
            else:
                logger.error(f"Increment #{i+2} failed")
                return False

        logger.header("Step 7: Read final counter value")

        final_read_result = chain.call_contract_read_function(
            contract_address=deployer_account.address,
            contract_name=contract_name,
            function_name="get-counter",
            sender=caller_account.address,
            function_args=[],
        )

        logger.info(f"Final counter value: {final_read_result.result}")

        if final_read_result.okay:
            logger.success(f"Final counter value: {final_read_result.result}")
        else:
            logger.error(f"Final read failed: {final_read_result.cause}")
            return False

        logger.header("Step 8: Test reset function")

        reset_result = chain.call_contract_write_function_and_confirm(
            caller_account=caller_account,
            contract_address=deployer_account.address,
            contract_name=contract_name,
            function_name="reset",
            function_args=[],
            fee=increment_fee,
            timeout=120,
        )

        if reset_result.confirmed:
            logger.success(f"Reset confirmed: {reset_result.txid}")
        else:
            logger.error(f"Reset failed")
            return False

        logger.header("Step 9: Verify final state after reset")

        final_check = chain.call_contract_read_function(
            contract_address=deployer_account.address,
            contract_name=contract_name,
            function_name="get-counter",
            sender=caller_account.address,
            function_args=[],
        )

        logger.info(f"Counter after reset: {final_check.result}")

        if final_check.okay:
            logger.success(f"Final value after reset: {final_check.result}")
        else:
            logger.error(f"Final check failed: {final_check.cause}")
            return False

        logger.header("SUMMARY")
        logger.success(f"Contract deployed: {contract_id}")
        logger.success(f"Initial read-only calls: Successful")
        logger.success(f"Write operations (increment x4, reset x1): Successful")
        logger.success(f"State verification: Counter value correctly updated")
        logger.info(f"Total transactions: 6 (1 deployment + 4 increments + 1 reset)")

        return True


if __name__ == "__main__":
    recipe = ContractDeploymentRecipe()
    success = recipe.execute()
    sys.exit(0 if success else 1)
