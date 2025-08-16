#!/usr/bin/env python3

import subprocess
import time
import os
from .logger import Colors, logger
from .stacks_core_api import StacksCoreAPIWrapper
from .config import ACCOUNTS, AccountManager

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYBOOK_DIR = os.path.join(PROJECT_ROOT, "naka3", "playbooks", "three-miners")

class NodeManager:
    def __init__(self):
        self.node_process = None
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

    def start_node(self, mode: str = "auto") -> bool:
        """Start the three miners node from snapshot (backward compatibility).
        
        Args:
            mode: Mining mode - 'auto' (default) or 'manual'
        
        Note: This method restores from snapshot. Use start_from_scratch() for clean start.
        """
        logger.info(Colors.format_stacks("Starting three miners from snapshot..."))
        return self.restore_snapshot(mode)
    
    def stop_node(self):
        """Stop the three miners node."""
        logger.info(Colors.format_stacks("Stopping three miners..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "stop"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_stacks("Node stopped"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to stop node", str(e)))
    
    def resume_node(self):
        """Resume the three miners node."""
        logger.info(Colors.format_stacks("Resuming three miners..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "resume"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_stacks("Node resumed"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to resume node", str(e)))
    
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
            
            self.node_process = subprocess.Popen(
                cmd,
                cwd=PLAYBOOK_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            self.running = True
            
            time.sleep(5) 
            
            if self.node_process.poll() is not None:
                logger.error(Colors.format_fail("Node process exited early."))
                return False
                
            logger.info(Colors.format_stacks(f"Started from scratch in {mode} mode"))
            
            if not self.wait_for_miners_ready():
                raise RuntimeError("Not all miners became ready within the timeout period.")
                
            return True
        except Exception as e:
            logger.error(Colors.format_fail("Failed to start from scratch", str(e)))
            if self.node_process and self.node_process.poll() is None:
                self.node_process.terminate()
            return False
    
    def start_auto_mining(self):
        """Start three miners from scratch in automatic mining mode."""
        return self.start_from_scratch("auto")
    
    def start_manual_mining(self):
        """Start three miners from scratch in manual mining mode."""
        return self.start_from_scratch("manual")
    
    def switch_to_auto_mining(self):
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
    
    def switch_to_manual_mining(self):
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
    
    def mine_single_btc_block(self):
        """Mine a single BTC block (manual mode only)."""
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
    
    def create_snapshot(self):
        """Create a generic snapshot."""
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
    
    def restore_snapshot(self, mode: str = "auto"):
        """Restore snapshot in specified mode.
        
        Args:
            mode: Mining mode - 'auto' (default) or 'manual'
        """
        logger.info(Colors.format_stacks(f"Restoring snapshot in {mode} mode..."))
        try:
            cmd = ["./three-miners.sh", "snapshot", "restore", mode]
            
            self.node_process = subprocess.Popen(
                cmd,
                cwd=PLAYBOOK_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            self.running = True
            
            time.sleep(5) 
            
            if self.node_process.poll() is not None:
                logger.error(Colors.format_fail("Node process exited early."))
                return False
                
            logger.info(Colors.format_stacks("Snapshot restored"))
            
            if not self.wait_for_miners_ready():
                raise RuntimeError("Not all miners became ready within the timeout period.")
                
            return True
        except Exception as e:
            logger.error(Colors.format_fail("Failed to restore snapshot", str(e)))
            if self.node_process and self.node_process.poll() is None:
                self.node_process.terminate()
            return False
    
    def get_mining_info(self):
        """Get mining status information."""
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
        """Clean up the node process if it's running."""
        if self.node_process and self.running:
            logger.info(Colors.format_grey("Cleaning up background node process..."))
            self.node_process.terminate()
            try:
                self.node_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Node process did not terminate gracefully, killing it.")
                self.node_process.kill()
                self.node_process.wait()
            self.running = False
            logger.info(Colors.format_stacks("Cleanup complete"))