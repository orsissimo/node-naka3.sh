#!/usr/bin/env python3
"""
Fetch Transactions Example

This script demonstrates:
1. Fetching transaction list for a specific principal address
2. Filtering transactions by time range and/or block height
3. Optionally processing each transaction through TransactionHandler (deep dive)
4. Saving all data to /tmp directory

IMPORTANT NOTE:
The Hiro API filters transactions by 'burn_block_time', NOT 'block_time'.
The burn_block_time can be several minutes EARLIER than the block_time.
This means a transaction with block_time=17:43:05 might have burn_block_time=17:37:56,
so it will be included when filtering with end_time >= 17:37:56.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.logger import logger
from utils.base import PROJECT_ROOT
from utils.stacks.hiro_api import HiroAPI
from utils.stacks.hiro_json_handler import PrincipalHandler, RangeFilter
from utils.templates.recipe_blank import RecipeTemplate


class Recipe(RecipeTemplate):
    """Recipe for fetching transactions for a specific principal within a time range."""

    def _run_recipe(self) -> bool:
        logger.header("FETCH TRANSACTIONS FROM MAINNET")

        # Configuration
        logger.header("Step 1: Configure parameters")
        TARGET_ADDRESS = "SPGFXHEJ7ADB0FJEMJDF6YBKX5KGYJG0YYB5VCZB"

        ITALY_TZ = timezone(timedelta(hours=1))  # UTC+1
        START_DATE = datetime(2025, 10, 5, 18, 0, 0, tzinfo=ITALY_TZ)
        END_DATE = datetime(2025, 10, 6, 18, 43, 0, tzinfo=ITALY_TZ)

        # Convert to Unix timestamps
        start_timestamp = int(START_DATE.timestamp())
        end_timestamp = int(END_DATE.timestamp())

        # Create filter range (can use timestamp OR block_height OR burn_block_height)
        range_filter = RangeFilter(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            # Optionally, also filter by Stacks block height:
            # start_block_height=4005000,
            # end_block_height=4010000,
            # Or filter by Bitcoin burn block height:
            # start_burn_block_height=917000,
            # end_burn_block_height=918000,
        )

        logger.info(f"Target address: {TARGET_ADDRESS}")
        logger.info(f"Start time: {START_DATE.isoformat()} ({start_timestamp})")
        logger.info(f"End time: {END_DATE.isoformat()} ({end_timestamp})")
        if range_filter.start_block_height or range_filter.end_block_height:
            logger.info(
                f"Stacks block height range: {range_filter.start_block_height} - "
                f"{range_filter.end_block_height}"
            )
        if range_filter.start_burn_block_height or range_filter.end_block_height:
            logger.info(
                f"Bitcoin burn block height range: {range_filter.start_burn_block_height} - "
                f"{range_filter.end_burn_block_height}"
            )

        # Create PrincipalHandler
        logger.header("Step 2: Initialize PrincipalHandler")
        api = HiroAPI.mainnet()
        handler = PrincipalHandler(
            principal=TARGET_ADDRESS, api=api, range_filter=range_filter
        )

        # Fetch and filter transactions
        logger.header("Step 3: Fetch and filter transactions")
        transactions = handler.fetch_transaction_list()

        if not transactions:
            logger.warning("No transactions found matching the criteria")
            return True

        logger.success(f"Found {len(transactions)} transaction(s)")

        # Display basic transaction info
        logger.header("Step 4: Display transactions")
        for idx, tx in enumerate(transactions, 1):
            logger.info(f"\n--- Transaction {idx} ---")
            logger.info(f"TX ID: {tx.tx_id}")
            logger.info(f"Type: {tx.tx_type}")
            logger.info(f"Status: {tx.tx_status}")
            logger.info(f"Sender: {tx.sender_address}")

            if hasattr(tx, "block_height") and tx.block_height is not None:
                logger.info(f"Stacks block height: {tx.block_height}")

            if hasattr(tx, "burn_block_height") and tx.burn_block_height is not None:
                logger.info(f"Bitcoin burn block height: {tx.burn_block_height}")

            if hasattr(tx, "burn_block_time") and tx.burn_block_time is not None:
                burn_time = datetime.fromtimestamp(tx.burn_block_time, tz=ITALY_TZ)
                logger.info(
                    f"Burn block time: {burn_time.isoformat()} ({tx.burn_block_time})"
                )

            if hasattr(tx, "block_time") and tx.block_time is not None:
                block_time = datetime.fromtimestamp(tx.block_time, tz=ITALY_TZ)
                logger.info(f"Block time: {block_time.isoformat()} ({tx.block_time})")

            if hasattr(tx, "fee_rate") and tx.fee_rate is not None:
                logger.info(f"Fee: {tx.fee_rate} µSTX")

        # Optional: Deep dive - process each transaction through TransactionHandler
        logger.header("Step 5: Process transactions (deep dive)")
        tmp_dir = os.path.join(PROJECT_ROOT, "tmp")

        # Ask user if they want to process all transactions
        logger.info(
            "This will fetch detailed data for each transaction "
            "(contract code, events, metadata) and save individual JSON files."
        )

        # For this example, we'll process them automatically
        # In production, you might want to prompt the user
        process_deep = True

        if process_deep:
            results = handler.process_all_transactions(tmp_dir)
            logger.success(
                f"Processed {len(results)} transaction(s), saved to {tmp_dir}/"
            )

            # Display what was saved
            for tx_id, metadata in results:
                logger.info(f"  {tx_id[:20]}... → {type(metadata).__name__}")
        else:
            logger.info("Skipping deep dive processing")

        logger.header("FETCH COMPLETE")
        logger.success(
            f"Successfully fetched and filtered {handler.get_transaction_count()} transaction(s)"
        )

        return True


if __name__ == "__main__":
    recipe = Recipe()
    success = recipe.execute()
    sys.exit(0 if success else 1)
