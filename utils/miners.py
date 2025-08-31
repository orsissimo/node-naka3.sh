#!/usr/bin/env python3

import subprocess
import time
import os
from .logger import logger
from .stacks_core_api import StacksCoreAPI, StacksCoreAPIWrapper
from .config import ACCOUNTS, AccountManager, Miner, MiningMode

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYBOOK_DIR = os.path.join(PROJECT_ROOT, "naka3", "playbooks", "three-miners")

class MinerManager:
    def __init__(self):
        self.miner_process = None
        self.running = False
        self.apis = {
            name: StacksCoreAPI(base_url=account.api_url)
            for name, account in AccountManager.all().items()
        }

    def wait_for_miners_ready(self, timeout: int = 45) -> bool:
        """Waits for all managed miner APIs to become responsive with adaptive polling."""
        logger.info("Verifying all miner endpoints are ready...")
        time.sleep(10)

        start_time = time.time()
        miners_to_check = list(self.apis.keys())
        sleep_interval = 1  # Start with 1 second
        
        while time.time() - start_time < timeout:
            ready_miners = []
            progress_made = False
            
            for miner_name, api in self.apis.items():
                try:
                    if api.get_info():
                        ready_miners.append(miner_name)
                        if miner_name not in getattr(self, '_ready_miners', set()):
                            progress_made = True
                except Exception:
                    pass 
            
            # Track ready miners to detect progress
            if not hasattr(self, '_ready_miners'):
                self._ready_miners = set()
            
            if ready_miners:
                new_ready = set(ready_miners) - self._ready_miners
                if new_ready:
                    progress_made = True
                    for miner in new_ready:
                        logger.info(f"Miner {miner} is now ready")
                self._ready_miners.update(ready_miners)
            
            if len(ready_miners) == len(miners_to_check):
                logger.stacks(f"All {len(miners_to_check)} miners are ready.")
                return True
            
            # Adaptive polling: faster when making progress, slower when not
            if progress_made:
                sleep_interval = 1  # Reset to fast polling
            else:
                sleep_interval = min(sleep_interval * 1.2, 4)  # Gradual backoff, max 4s
            
            logger.debug(f"Miners ready: {len(ready_miners)}/{len(miners_to_check)}. Waiting {sleep_interval:.1f}s...")
            time.sleep(sleep_interval)
            
        logger.error(f"Timeout: Only {len(ready_miners)}/{len(miners_to_check)} miners became ready.")
        return False

    def start(self, mode: MiningMode) -> bool:
        """Start miners from scratch in specified mode.
        
        Args:
            mode: Mining mode - MiningMode.AUTO or MiningMode.MANUAL (required)
        """
        if not isinstance(mode, MiningMode):
            raise ValueError(f"Invalid mode '{mode}'. Use MiningMode.AUTO or MiningMode.MANUAL")
            
        logger.stacks(f"Starting three miners from scratch in {mode.value} mode...")
        try:
            cmd = ["./three-miners.sh", "start", mode.value]
            
            self.miner_process = subprocess.Popen(
                cmd,
                cwd=PLAYBOOK_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            self.running = True
            
            if self.wait_for_miners_ready():
                logger.success("All 3 miners are ready.")
                return True
            else:
                logger.error("Timeout waiting for miners to start.")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start from scratch: {str(e)}")
            if self.miner_process and self.miner_process.poll() is None:
                self.miner_process.terminate()
            return False
    
    def start_auto(self) -> bool:
        """Start miners in auto mining mode."""
        return self.start(MiningMode.AUTO)
    
    def start_manual(self) -> bool:
        """Start miners in manual mining mode."""
        return self.start(MiningMode.MANUAL)

    def snapshot_create(self):
        """Create generic snapshot."""
        logger.stacks("Creating snapshot...")
        try:
            subprocess.run(
                ["./three-miners.sh", "snapshot", "create"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.stacks("Snapshot created")
        except Exception as e:
            logger.error(f"Failed to create snapshot: {str(e)}")

    def snapshot_restore(self, mode: MiningMode):
        """Restore snapshot in specified mode (required).
        
        Args:
            mode: Mining mode - MiningMode.AUTO or MiningMode.MANUAL
        """
        logger.stacks(f"Restoring snapshot in {mode.value} mode...")
        try:
            cmd = ["./three-miners.sh", "snapshot", "restore", mode.value]
            
            self.miner_process = subprocess.Popen(
                cmd,
                cwd=PLAYBOOK_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            self.running = True
            
            # Wait for miners to be ready after snapshot restore
            if not self.wait_for_miners_ready(timeout=15):
                logger.warning("Miners may not be fully ready after snapshot restore") 
            
            if self.miner_process.poll() is not None:
                logger.error("Miners process exited early.")
                return False
                
            logger.stacks("Snapshot restored")
            
            if not self.wait_for_miners_ready():
                raise RuntimeError("Not all miners became ready within the timeout period.")
                
            return True
        except Exception as e:
            logger.error(f"Failed to restore snapshot: {str(e)}")
            if self.miner_process and self.miner_process.poll() is None:
                self.miner_process.terminate()
            return False

    def snapshot_restore_auto(self):
        """Restore snapshot in auto mining mode."""
        return self.snapshot_restore(MiningMode.AUTO)
    
    def snapshot_restore_manual(self):
        """Restore snapshot in manual mining mode.""" 
        return self.snapshot_restore(MiningMode.MANUAL)
    
    def info(self):
        """Show status information."""
        logger.stacks("Getting mining info...")
        try:
            result = subprocess.run(
                ["./three-miners.sh", "info"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True,
                text=True
            )
            logger.stacks("Mining info retrieved")
            return result.stdout
        except Exception as e:
            logger.error(f"Failed to get mining info: {str(e)}")
            return None
    
    def stop(self):
        """Stop the three miners."""
        logger.stacks("Stopping miners...")
        try:
            subprocess.run(
                ["./three-miners.sh", "stop"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.stacks("Miners stopped")
        except Exception as e:
            logger.error(f"Failed to stop miners: {str(e)}")
    
    
    def resume(self):
        """Resume the three miners."""
        logger.stacks("Resuming three miners...")
        try:
            subprocess.run(
                ["./three-miners.sh", "resume"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.stacks("Miners resumed")
        except Exception as e:
            logger.error(f"Failed to resume miners: {str(e)}")
    
    
    def _manage_miner(self, action: str, miner_id: int):
        """Internal helper to stop or resume a specific miner."""
        action_gerund = "Stopping" if action == "stop" else "Resuming"
        action_past = "stopped" if action == "stop" else "resumed"

        logger.stacks(f"{action_gerund} miner{miner_id}...")
        try:
            cmd = ["../../naka3.sh", "-c", f"./config-miner-{miner_id}.sh", "node", str(miner_id), action]
            subprocess.run(cmd, 
                cwd=PLAYBOOK_DIR, 
                check=True, 
                capture_output=True
            )
            logger.stacks(f"Miner{miner_id} {action_past}")
        except Exception as e:
            logger.error(f"Failed to {action} miner{miner_id}: {str(e)}")

    def stop_miner(self, miner: Miner):
        """Stop specific miner."""
        self._manage_miner("stop", miner.value)
    
    def resume_miner(self, miner: Miner):
        """Resume specific miner."""
        self._manage_miner("resume", miner.value)
    
    def btc_auto(self):
        """Switch to automatic mining mode."""
        logger.stacks("Switching to automatic mining...")
        try:
            subprocess.run(
                ["./three-miners.sh", "btc_auto"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.stacks("Switched to automatic mining")
        except Exception as e:
            logger.error(f"Failed to switch to automatic mining: {str(e)}")
    
    def btc_manual(self):
        """Switch to manual mining mode."""
        logger.stacks("Switching to manual mining...")
        try:
            subprocess.run(
                ["./three-miners.sh", "btc_manual"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.stacks("Switched to manual mining")
        except Exception as e:
            logger.error(f"Failed to switch to manual mining: {str(e)}")
    
    def btc_mine(self):
        """Mine single block (manual mode only)."""
        logger.stacks("Mining single BTC block...")
        try:
            subprocess.run(
                ["./three-miners.sh", "btc_mine"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.stacks("Block mined")
        except Exception as e:
            logger.error(f"Failed to mine block: {str(e)}")

    def cleanup(self):
        """Clean up the miner process if it's running."""
        if self.miner_process and self.running:
            logger.dim("Cleaning up background miner process...")
            self.miner_process.terminate()
            try:
                self.miner_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Miners process did not terminate gracefully, killing it.")
                self.miner_process.kill()
                self.miner_process.wait()
            self.running = False
            logger.stacks("Cleanup complete")