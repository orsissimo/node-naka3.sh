#!/usr/bin/env python3

import os
import sys
import time

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.config import Miner, AccountManager
from utils.miners import MinerManager
from utils.logger import logger
from utils.stacks_core_api import StacksCoreAPIWrapper


def check_miner_connectivity(miner: Miner) -> dict:
    """Check if miner API is responsive"""
    result = {"miner": miner, "connected": False, "error": None}

    try:
        account = AccountManager.get(miner)
        api = StacksCoreAPIWrapper(base_url=account.api_url)

        # Try to get account info
        account_info = api.get_account_info(account.address)
        nonce = account_info.nonce

        # Try to get node info
        info = api.get_info()
        height = info.get("stacks_tip_height", 0)

        result["connected"] = True
        result["nonce"] = nonce
        result["height"] = height
        result["address"] = account.address

    except Exception as e:
        result["error"] = str(e)

    return result


def print_connectivity_status(miners: list):
    """Print connectivity status for all miners"""
    logger.header("Miner Connectivity Status")

    for miner in miners:
        status = check_miner_connectivity(miner)
        if status["connected"]:
            logger.success(
                f"{miner.value}: CONNECTED - Height: {status['height']}, Nonce: {status['nonce']}"
            )
        else:
            logger.error(f"{miner.value}: DISCONNECTED - Error: {status['error']}")


def main():
    """Execute the miner stop/resume test"""
    logger.dim("=" * 80)
    logger.header("MINER STOP/RESUME TEST")
    logger.dim("=" * 80)

    # Raw minimal setup
    miner_manager = MinerManager()
    miners = [Miner.MINER1, Miner.MINER2, Miner.MINER3]

    try:
        # Start all miners
        logger.stacks("Starting all miners...")
        if not miner_manager.snapshot_restore_auto():
            raise RuntimeError("Failed to start miners")

        # Initial connectivity check
        logger.header("Step 1: Initial connectivity check")
        print_connectivity_status(miners)

        # Stop miner2
        logger.header("Step 2: Stopping miner2")
        miner_manager.stop_miner(Miner.MINER2)
        time.sleep(5)  # Give time for miner to stop

        logger.header("Connectivity after stopping miner2:")
        print_connectivity_status(miners)

        # Verify miner1 and miner3 still work
        logger.header("Step 3: Testing remaining miners")
        for miner in [Miner.MINER1, Miner.MINER3]:
            try:
                account = AccountManager.get(miner)
                api = StacksCoreAPIWrapper(base_url=account.api_url)
                account_info = api.get_account_info(account.address)
                balance = account_info.balance
                nonce = account_info.nonce
                logger.standard(
                    f"{miner.value}", f"Balance: {balance:,} µSTX, Nonce: {nonce}"
                )
            except Exception as e:
                logger.error(f"{miner.value}: ERROR - {e}")

        # Stop miner3
        logger.header("Step 4: Stopping miner3")
        miner_manager.stop_miner(Miner.MINER3)
        time.sleep(5)  # Give time for miner to stop

        logger.header("Connectivity after stopping miner3:")
        print_connectivity_status(miners)

        # Resume miner2
        logger.header("Step 5: Resuming miner2")
        miner_manager.resume_miner(Miner.MINER2)
        time.sleep(10)  # Give time for miner to start

        logger.header("Connectivity after resuming miner2:")
        print_connectivity_status(miners)

        # Resume miner3
        logger.header("Step 6: Resuming miner3")
        miner_manager.resume_miner(Miner.MINER3)
        time.sleep(10)  # Give time for miner to start

        logger.header("Connectivity after resuming miner3:")
        print_connectivity_status(miners)

        # Final connectivity check
        logger.header("Step 7: Final connectivity check")
        print_connectivity_status(miners)

        # Count working miners
        working_miners = 0
        for miner in miners:
            status = check_miner_connectivity(miner)
            if status["connected"]:
                working_miners += 1

        # Test summary
        logger.dim("=" * 80)
        logger.header("TEST SUMMARY")
        logger.dim("=" * 80)

        logger.standard("Working miners", f"{working_miners}/3")

        if working_miners == 3:
            logger.success("✓ All miners working - stop/resume test PASSED")
            return True
        else:
            logger.error("✗ Some miners not working - stop/resume test FAILED")
            return False

    except Exception as e:
        logger.error(f"TEST FAILED: {str(e)}")
        return False

    finally:
        # Cleanup
        logger.header("Cleaning up...")
        miner_manager.stop()
        miner_manager.cleanup()


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)
