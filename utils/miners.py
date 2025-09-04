#!/usr/bin/env python3

import subprocess
import time
import os
from .logger import logger, Colors
from .stacks_core_api import StacksCoreAPI
from .config import (
    AccountManager,
    Miner,
    MiningMode,
    StacksException,
    StacksNetworkException,
    StacksTimeoutException,
    StacksAPIException,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYBOOK_DIR = os.path.join(PROJECT_ROOT, "naka3", "playbooks", "three-miners")


class MinerManager:
    def __init__(self):
        self._miner_process = None
        self._running = False
        self._apis = {
            name: StacksCoreAPI(base_url=account.api_url)
            for name, account in AccountManager.all().items()
        }
        self._validate_initialization()

    def _validate_initialization(self):
        """Validate that initialization completed successfully."""
        if not self._apis:
            raise ValueError("No miner APIs were initialized")
        if not isinstance(self._running, bool):
            raise TypeError("Running state must be boolean")

    @property
    def is_running(self) -> bool:
        """Check if miners are currently running (read-only)."""
        return self._running

    @property
    def api_count(self) -> int:
        """Get number of managed APIs (read-only)."""
        return len(self._apis)

    def wait_for_miners_ready(self, timeout: int = 45) -> bool:
        """Waits for all managed miner APIs to become responsive with adaptive polling."""
        logger.info("Verifying all miner endpoints are ready...", Colors.ORANGE)
        time.sleep(10)

        start_time = time.time()
        miners_to_check = list(self._apis.keys())
        sleep_interval = 1  # Start with 1 second

        while time.time() - start_time < timeout:
            ready_miners = []
            progress_made = False

            for miner_name, api in self._apis.items():
                try:
                    if api.get_info():
                        ready_miners.append(miner_name)
                        if miner_name not in getattr(self, "_ready_miners", set()):
                            progress_made = True
                except (
                    StacksNetworkException,
                    StacksTimeoutException,
                    StacksAPIException,
                ) as e:
                    # Log transient API failures as warnings during readiness check
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time > 5:  # Only warn if we have time left to retry
                        logger.warning(f"Miner {miner_name} not ready yet (will retry): {type(e).__name__}")
                    # Continue checking other miners

            # Track ready miners to detect progress
            if not hasattr(self, "_ready_miners"):
                self._ready_miners = set()

            if ready_miners:
                new_ready = set(ready_miners) - self._ready_miners
                if new_ready:
                    progress_made = True
                    for miner in new_ready:
                        logger.info(f"Miner {miner} is now ready", Colors.ORANGE)
                self._ready_miners.update(ready_miners)

            if len(ready_miners) == len(miners_to_check):
                logger.info(
                    f"All {len(miners_to_check)} miners are ready.", Colors.ORANGE
                )
                return True

            # Adaptive polling: faster when making progress, slower when not
            if progress_made:
                sleep_interval = 1  # Reset to fast polling
            else:
                sleep_interval = min(sleep_interval * 1.2, 4)  # Gradual backoff, max 4s

            logger.debug(
                f"Miners ready: {len(ready_miners)}/{len(miners_to_check)}. Waiting {sleep_interval:.1f}s..."
            )
            time.sleep(sleep_interval)

        logger.error(
            f"Timeout: Only {len(ready_miners)}/{len(miners_to_check)} miners became ready."
        )
        raise StacksTimeoutException(
            f"Timeout: Only {len(ready_miners)}/{len(miners_to_check)} miners became ready"
        )

    def start(self, mode: MiningMode) -> bool:
        """Start miners from scratch in specified mode.

        Args:
            mode: Mining mode - MiningMode.AUTO or MiningMode.MANUAL (required)
        """
        if not isinstance(mode, MiningMode):
            raise ValueError(
                f"Invalid mode '{mode}'. Use MiningMode.AUTO or MiningMode.MANUAL"
            )

        logger.info(
            f"Starting three miners from scratch in {mode.value} mode...", Colors.ORANGE
        )
        try:
            cmd = ["./three-miners.sh", "start", mode.value]

            self._miner_process = subprocess.Popen(
                cmd,
                cwd=PLAYBOOK_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self._running = True

            self.wait_for_miners_ready()
            logger.success("All 3 miners are ready.")
            return True

        except Exception as e:
            logger.error(f"Failed to start from scratch: {str(e)}")
            if self._miner_process and self._miner_process.poll() is None:
                self._miner_process.terminate()
            raise StacksException(
                f"Failed to start miners from scratch: {str(e)}"
            ) from e

    def start_auto(self) -> bool:
        """Start miners in auto mining mode."""
        return self.start(MiningMode.AUTO)

    def start_manual(self) -> bool:
        """Start miners in manual mining mode."""
        return self.start(MiningMode.MANUAL)

    def snapshot_create(self):
        """Create generic snapshot."""
        logger.info("Creating snapshot...", Colors.ORANGE)
        try:
            subprocess.run(
                ["./three-miners.sh", "snapshot", "create"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True,
            )
            logger.info("Snapshot created", Colors.ORANGE)
        except Exception as e:
            logger.error(f"Failed to create snapshot: {str(e)}")
            raise StacksException(f"Failed to create snapshot: {str(e)}") from e

    def snapshot_restore(self, mode: MiningMode) -> bool:
        """Restore snapshot in specified mode (required).

        Args:
            mode: Mining mode - MiningMode.AUTO or MiningMode.MANUAL
        """
        logger.info(f"Restoring snapshot in {mode.value} mode...", Colors.ORANGE)
        try:
            cmd = ["./three-miners.sh", "snapshot", "restore", mode.value]

            self._miner_process = subprocess.Popen(
                cmd,
                cwd=PLAYBOOK_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self._running = True

            # Wait for miners to be ready after snapshot restore
            try:
                self.wait_for_miners_ready(timeout=15)
            except StacksTimeoutException:
                logger.warning("Miners may not be fully ready after snapshot restore")

            if self._miner_process.poll() is not None:
                logger.error("Miners process exited early.")
                raise StacksException(
                    "Miners process exited early during snapshot restore"
                )

            logger.info("Snapshot restored", Colors.ORANGE)

            self.wait_for_miners_ready()

            return True
        except Exception as e:
            logger.error(f"Failed to restore snapshot: {str(e)}")
            if self._miner_process and self._miner_process.poll() is None:
                self._miner_process.terminate()
            raise StacksException(f"Failed to restore snapshot: {str(e)}") from e

    def snapshot_restore_auto(self) -> bool:
        """Restore snapshot in auto mining mode."""
        return self.snapshot_restore(MiningMode.AUTO)

    def snapshot_restore_manual(self) -> bool:
        """Restore snapshot in manual mining mode."""
        return self.snapshot_restore(MiningMode.MANUAL)

    def info(self) -> str:
        """Show status information."""
        logger.info("Getting mining info...", Colors.ORANGE)
        try:
            result = subprocess.run(
                ["./three-miners.sh", "info"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("Mining info retrieved", Colors.ORANGE)
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get mining info: {str(e)}")
            raise StacksException(f"Failed to get mining info: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting mining info: {str(e)}")
            raise StacksException(
                f"Unexpected error getting mining info: {str(e)}"
            ) from e

    def stop(self):
        """Stop the three miners."""
        logger.info("Stopping miners...", Colors.ORANGE)
        try:
            subprocess.run(
                ["./three-miners.sh", "stop"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True,
            )
            logger.info("Miners stopped", Colors.ORANGE)
        except Exception as e:
            logger.error(f"Failed to stop miners: {str(e)}")
            raise StacksException(f"Failed to stop miners: {str(e)}") from e

    def resume(self):
        """Resume the three miners."""
        logger.info("Resuming three miners...", Colors.ORANGE)
        try:
            subprocess.run(
                ["./three-miners.sh", "resume"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True,
            )
            logger.info("Miners resumed", Colors.ORANGE)
        except Exception as e:
            logger.error(f"Failed to resume miners: {str(e)}")
            raise StacksException(f"Failed to resume miners: {str(e)}") from e

    def _manage_miner(self, action: str, miner_id: int):
        """Internal helper to stop or resume a specific miner."""
        action_gerund = "Stopping" if action == "stop" else "Resuming"
        action_past = "stopped" if action == "stop" else "resumed"

        logger.info(f"{action_gerund} miner{miner_id}...", Colors.ORANGE)
        try:
            cmd = [
                "../../naka3.sh",
                "-c",
                f"./config-miner-{miner_id}.sh",
                "node",
                str(miner_id),
                action,
            ]
            subprocess.run(cmd, cwd=PLAYBOOK_DIR, check=True, capture_output=True)
            logger.info(f"Miner{miner_id} {action_past}", Colors.ORANGE)
        except Exception as e:
            logger.error(f"Failed to {action} miner{miner_id}: {str(e)}")
            raise StacksException(
                f"Failed to {action} miner{miner_id}: {str(e)}"
            ) from e

    def stop_miner(self, miner: Miner):
        """Stop specific miner."""
        self._manage_miner("stop", miner.value)

    def resume_miner(self, miner: Miner):
        """Resume specific miner."""
        self._manage_miner("resume", miner.value)

    def btc_auto(self):
        """Switch to automatic mining mode."""
        logger.info("Switching to automatic mining...", Colors.ORANGE)
        try:
            subprocess.run(
                ["./three-miners.sh", "btc_auto"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True,
            )
            logger.info("Switched to automatic mining", Colors.ORANGE)
        except Exception as e:
            logger.error(f"Failed to switch to automatic mining: {str(e)}")
            raise StacksException(
                f"Failed to switch to automatic mining: {str(e)}"
            ) from e

    def btc_manual(self):
        """Switch to manual mining mode."""
        logger.info("Switching to manual mining...", Colors.ORANGE)
        try:
            subprocess.run(
                ["./three-miners.sh", "btc_manual"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True,
            )
            logger.info("Switched to manual mining", Colors.ORANGE)
        except Exception as e:
            logger.error(f"Failed to switch to manual mining: {str(e)}")
            raise StacksException(f"Failed to switch to manual mining: {str(e)}") from e

    def btc_mine(self):
        """Mine single block (manual mode only)."""
        logger.info("Mining single BTC block...", Colors.ORANGE)
        try:
            subprocess.run(
                ["./three-miners.sh", "btc_mine"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True,
            )
            logger.info("Block mined", Colors.ORANGE)
        except Exception as e:
            logger.error(f"Failed to mine block: {str(e)}")
            raise StacksException(f"Failed to mine block: {str(e)}") from e

    def cleanup(self):
        """Clean up the miner process if it's running."""
        if self._miner_process and self._running:
            logger.info("Cleaning up background miner process...", Colors.ORANGE)
            self._miner_process.terminate()
            try:
                self._miner_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Miners process did not terminate gracefully, killing it."
                )
                self._miner_process.kill()
                self._miner_process.wait()
            self._running = False
            logger.info("Cleanup complete", Colors.ORANGE)
