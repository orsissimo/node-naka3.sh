#!/usr/bin/env python3

import subprocess
import time
import os
from .colors import Colors, logger
from .stacks_core_api import StacksCoreAPIWrapper
from .config import ACCOUNTS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYBOOK_DIR = os.path.join(PROJECT_ROOT, "naka3", "playbooks", "three-miners")

class NodeManager:
    def __init__(self):
        self.node_process = None
        self.running = False
        self.node_log_handle = None
        self.node_log_path = os.path.join(PROJECT_ROOT, "logs", "three-miners-test.log")
        self.apis = {
            name: StacksCoreAPIWrapper(base_url=account.api_url)
            for name, account in ACCOUNTS.items()
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
                logger.info(Colors.format_success(f"All {len(miners_to_check)} miners are ready."))
                return True
            
            logger.debug(f"Miners ready: {len(ready_miners)}/{len(miners_to_check)}. Waiting...")
            time.sleep(2)
            
        logger.error(Colors.format_fail(f"Timeout: Only {len(ready_miners)}/{len(miners_to_check)} miners became ready."))
        return False

    def start_node(self) -> bool:
        """Start the three miners node with colorized logging."""
        logger.info(Colors.format_header("Starting three miners..."))
        try:
            cmd = ["./three-miners.sh", "snapshot", "restore"]
            # Ensure logs directory exists
            os.makedirs(os.path.dirname(self.node_log_path), exist_ok=True)
            logger.info(f"Redirecting three-miners.sh output to: {self.node_log_path}")
            self.node_log_handle = open(self.node_log_path, 'w')
            
            self.node_process = subprocess.Popen(
                cmd,
                cwd=PLAYBOOK_DIR,
                stdout=self.node_log_handle,
                stderr=subprocess.STDOUT,
                text=True
            )
            self.running = True
            
            time.sleep(5) 
            
            if self.node_process.poll() is not None:
                logger.error(Colors.format_fail("Node process exited early."))
                return False
                
            logger.info(Colors.format_success("Node process started"))
            
            if not self.wait_for_miners_ready():
                raise RuntimeError("Not all miners became ready within the timeout period.")

        except Exception as e:
            logger.critical(Colors.format_fail("Failed to start node", str(e)))
            if self.node_process and self.node_process.poll() is None:
                self.node_process.terminate()
            if self.node_log_handle:
                self.node_log_handle.close()
            return False
        return True
    
    def stop_node(self):
        """Stop the three miners node."""
        logger.info(Colors.format_header("Stopping three miners..."))
        if self.node_log_handle:
            self.node_log_handle.close()
            self.node_log_handle = None
        try:
            subprocess.run(
                ["./three-miners.sh", "stop"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_success("Node stopped"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to stop node", str(e)))
    
    def resume_node(self):
        """Resume the three miners node."""
        logger.info(Colors.format_header("Resuming three miners..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "resume"],
                cwd=PLAYBOOK_DIR,
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_success("Node resumed"))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to resume node", str(e)))
    
    def _manage_miner(self, action: str, miner_id: int):
        """Internal helper to stop or resume a specific miner."""
        action_gerund = "Stopping" if action == "stop" else "Resuming"
        action_past = "stopped" if action == "stop" else "resumed"

        logger.info(Colors.format_header(f"{action_gerund} miner{miner_id}..."))
        try:
            cmd = ["../../naka3.sh", "-c", f"./config-miner-{miner_id}.sh", "node", str(miner_id), action]
            subprocess.run(cmd, 
                cwd=PLAYBOOK_DIR, 
                check=True, 
                capture_output=True
            )
            logger.info(Colors.format_success(f"Miner{miner_id} {action_past}"))
        except Exception as e:
            logger.error(Colors.format_fail(f"Failed to {action} miner{miner_id}", str(e)))

    def stop_miner(self, miner_id: int):
        """Stop specific miner (1, 2, or 3)."""
        self._manage_miner("stop", miner_id)
    
    def resume_miner(self, miner_id: int):
        """Resume specific miner (1, 2, or 3)."""
        self._manage_miner("resume", miner_id)
    
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
            logger.info(Colors.format_success("Cleanup complete"))