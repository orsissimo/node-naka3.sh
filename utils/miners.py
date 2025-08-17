#!/usr/bin/env python3

import subprocess
import time
import os
from .logger import Colors, logger
from .stacks_core_api import StacksCoreAPIWrapper
from .config import ACCOUNTS, AccountManager

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYBOOK_DIR = os.path.join(PROJECT_ROOT, "naka3", "playbooks", "three-miners")

class MinerManager:
    def __init__(self):
        self.miner_process = None
        self.running = False
        self.apis = {
            name: StacksCoreAPIWrapper(base_url=account.api_url)
            for name, account in AccountManager.all().items()
        }

    def wait_for_miners_ready(self, timeout: int = 45) -> bool:
        """Waits for all managed miner APIs to become responsive."""
        logger.info("Verifying all miner endpoints are ready...")
        start_time = time.time()
        miners_to_check = list(self.apis.keys())
        
        while time.time() - start_time < timeout:
            ready_miners = []
            for miner_name, api in self.apis.items():
                try:
                    if api.get_info():
                        ready_miners.append(miner_name)
                except Exception:
                    pass 
            
            if len(ready_miners) == len(miners_to_check):
                logger.info(Colors.format_stacks(f"All {len(miners_to_check)} miners are ready."))
                return True
            
            logger.debug(f"Miners ready: {len(ready_miners)}/{len(miners_to_check)}. Waiting...")
            time.sleep(2)
            
        logger.error(Colors.format_fail(f"Timeout: Only {len(ready_miners)}/{len(miners_to_check)} miners became ready."))
        return False

    def start(self, mode: str) -> bool:
        """Start in automatic or manual mining mode (required).
        
        Args:
            mode: Mining mode - 'auto' or 'manual' (required)
        """
        if mode not in ["auto", "manual"]:
            raise ValueError(f"Invalid mode '{mode}'. Use 'auto' or 'manual'")
            
        logger.info(Colors.format_stacks(f"Starting three miners in {mode} mode..."))
        return self.start_from_scratch(mode)
    
    
    def stop(self):
        """Stop the three miners."""
        logger.info(Colors.format_stacks("Stopping miners..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "stop"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_stacks("Miners stopped"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to stop miners", str(e)))
    
    
    def resume(self):
        """Resume the three miners."""
        logger.info(Colors.format_stacks("Resuming three miners..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "resume"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_stacks("Miners resumed"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to resume miners", str(e)))
    
    
    def _manage_miner(self, action: str, miner_id: int):
        """Internal helper to stop or resume a specific miner."""
        action_gerund = "Stopping" if action == "stop" else "Resuming"
        action_past = "stopped" if action == "stop" else "resumed"

        logger.info(Colors.format_stacks(f"{action_gerund} miner{miner_id}..."))
        try:
            cmd = ["../../naka3.sh", "-c", f"./config-miner-{miner_id}.sh", "node", str(miner_id), action]
            subprocess.run(cmd, 
                cwd=PLAYBOOK_DIR, 
                check=True, 
                capture_output=True
            )
            logger.info(Colors.format_stacks(f"Miner{miner_id} {action_past}"))
        except Exception as e:
            logger.error(Colors.format_fail(f"Failed to {action} miner{miner_id}", str(e)))

    def stop_miner(self, miner_id: int):
        """Stop specific miner (1, 2, or 3)."""
        self._manage_miner("stop", miner_id)
    
    def resume_miner(self, miner_id: int):
        """Resume specific miner (1, 2, or 3)."""
        self._manage_miner("resume", miner_id)
    
    def start_from_scratch(self, mode: str):
        """Start three miners from scratch in specified mode.
        
        Args:
            mode: Mining mode - 'auto' or 'manual' (required)
        """
        if mode not in ["auto", "manual"]:
            raise ValueError(f"Invalid mode '{mode}'. Use 'auto' or 'manual'")
            
        logger.info(Colors.format_stacks(f"Starting three miners from scratch in {mode} mode..."))
        try:
            cmd = ["./three-miners.sh", "start", mode]
            
            self.miner_process = subprocess.Popen(
                cmd,
                cwd=PLAYBOOK_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            self.running = True
            
            time.sleep(5) 
            
            if self.miner_process.poll() is not None:
                logger.error(Colors.format_fail("Miners process exited early."))
                return False
                
            logger.info(Colors.format_stacks(f"Started from scratch in {mode} mode"))
            
            if not self.wait_for_miners_ready():
                raise RuntimeError("Not all miners became ready within the timeout period.")
                
            return True
        except Exception as e:
            logger.error(Colors.format_fail("Failed to start from scratch", str(e)))
            if self.miner_process and self.miner_process.poll() is None:
                self.miner_process.terminate()
            return False
    
    
    def btc_auto(self):
        """Switch to automatic mining mode."""
        logger.info(Colors.format_stacks("Switching to automatic mining..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "btc_auto"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_stacks("Switched to automatic mining"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to switch to automatic mining", str(e)))
    
    def btc_manual(self):
        """Switch to manual mining mode."""
        logger.info(Colors.format_stacks("Switching to manual mining..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "btc_manual"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_stacks("Switched to manual mining"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to switch to manual mining", str(e)))
    
    def btc_mine(self):
        """Mine single block (manual mode only)."""
        logger.info(Colors.format_stacks("Mining single BTC block..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "btc_mine"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_stacks("Block mined"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to mine block", str(e)))
    
    def snapshot_create(self):
        """Create generic snapshot."""
        logger.info(Colors.format_stacks("Creating snapshot..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "snapshot", "create"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_stacks("Snapshot created"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to create snapshot", str(e)))
    
    def snapshot_restore(self, mode: str):
        """Restore snapshot in specified mode (required).
        
        Args:
            mode: Mining mode - 'auto' (default) or 'manual'
        """
        logger.info(Colors.format_stacks(f"Restoring snapshot in {mode} mode..."))
        try:
            cmd = ["./three-miners.sh", "snapshot", "restore", mode]
            
            self.miner_process = subprocess.Popen(
                cmd,
                cwd=PLAYBOOK_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            self.running = True
            
            time.sleep(5) 
            
            if self.miner_process.poll() is not None:
                logger.error(Colors.format_fail("Miners process exited early."))
                return False
                
            logger.info(Colors.format_stacks("Snapshot restored"))
            
            if not self.wait_for_miners_ready():
                raise RuntimeError("Not all miners became ready within the timeout period.")
                
            return True
        except Exception as e:
            logger.error(Colors.format_fail("Failed to restore snapshot", str(e)))
            if self.miner_process and self.miner_process.poll() is None:
                self.miner_process.terminate()
            return False
    
    def info(self):
        """Show status information."""
        logger.info(Colors.format_stacks("Getting mining info..."))
        try:
            result = subprocess.run(
                ["./three-miners.sh", "info"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(Colors.format_stacks("Mining info retrieved"))
            return result.stdout
        except Exception as e:
            logger.error(Colors.format_fail("Failed to get mining info", str(e)))
            return None

    def cleanup(self):
        """Clean up the miner process if it's running."""
        if self.miner_process and self.running:
            logger.info(Colors.format_grey("Cleaning up background miner process..."))
            self.miner_process.terminate()
            try:
                self.miner_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Miners process did not terminate gracefully, killing it.")
                self.miner_process.kill()
                self.miner_process.wait()
            self.running = False
            logger.info(Colors.format_stacks("Cleanup complete"))