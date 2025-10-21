#!/usr/bin/env python3
"""Manager for controlling and interacting with the 'three-miners' Stacks miners."""

import subprocess
import time

from ..types.stacks.exceptions import *
from ..logger import logger, Colors
from .stacks_core_api import StacksCoreAPI
from ..base import account_manager, PLAYBOOK_DIR
from ..types.stacks.infrastructure import Miner, MiningMode


class MinerManager:
    def __init__(self):
        self._miner_process = None
        self._running = False
        self._apis = {
            name: StacksCoreAPI(base_url=account.api_url)
            for name, account in account_manager.all().items()
        }
        self._validate_initialization()

    def _validate_initialization(self):
        if not self._apis:
            raise ValueError("No miner APIs were initialized")
        if not isinstance(self._running, bool):
            raise TypeError("Running state must be boolean")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def api_count(self) -> int:
        return len(self._apis)

    def wait_for_miners_ready(self, timeout: int = 45) -> bool:
        logger.info(
            f"Waiting for {len(self._apis)} miners to be ready...", Colors.ORANGE
        )
        time.sleep(15)

        start_time = time.time()
        poll_interval = 2
        ready_miners = []

        while time.time() - start_time < timeout:
            ready_miners = []
            failed_miners = []

            for miner_name, api in self._apis.items():
                try:
                    if api.get_info():
                        ready_miners.append(miner_name)
                except (
                    StacksNetworkException,
                    StacksTimeoutException,
                    StacksAPIException,
                ):
                    failed_miners.append(miner_name)

            if len(ready_miners) == len(self._apis):
                logger.debug(f"All {len(self._apis)} miners are ready.", Colors.ORANGE)
                return True

            elapsed = time.time() - start_time
            if elapsed > 0 and int(elapsed) % 10 == 0:
                logger.debug(
                    f"Miners ready: {len(ready_miners)}/{len(self._apis)} "
                    f"({timeout - int(elapsed)}s remaining)"
                )

            time.sleep(poll_interval)

        # Timeout reached
        logger.error(
            f"Timeout after {timeout}s: Only {len(ready_miners)}/{len(self._apis)} miners ready"
        )
        raise StacksTimeoutException(
            f"Timeout: Only {len(ready_miners)}/{len(self._apis)} miners became ready"
        )

    def start(self, mode: MiningMode) -> bool:
        """Start miners in the specified mining mode."""
        if not isinstance(mode, MiningMode):
            raise ValueError(f"Invalid mode '{mode}'.")

        logger.info(f"Starting three miners in {mode.value} mode...", Colors.ORANGE)
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
            logger.error(f"Failed to start miners: {str(e)}")
            if self._miner_process and self._miner_process.poll() is None:
                self._miner_process.terminate()
            raise StacksException(f"Failed to start miners: {str(e)}") from e

    def start_auto(self) -> bool:
        return self.start(MiningMode.AUTO)

    def start_manual(self) -> bool:
        return self.start(MiningMode.MANUAL)

    def snapshot_create(self):
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
        """Restore snapshot in the specified mining mode."""
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

            # Wait for miners to be ready after snapshot restore: quick check → health check → patient wait
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
        return self.snapshot_restore(MiningMode.AUTO)

    def snapshot_restore_manual(self) -> bool:
        return self.snapshot_restore(MiningMode.MANUAL)

    def info(self) -> str:
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
        self._manage_miner("stop", miner.value)

    def resume_miner(self, miner: Miner):
        self._manage_miner("resume", miner.value)

    def btc_auto(self):
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
