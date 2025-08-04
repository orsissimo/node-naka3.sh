#!/usr/bin/env python3

import subprocess
import time
from colors import Colors, logger

class NodeManager:
    def __init__(self):
        self.node_process = None
        self.running = False
        
    def start_node(self) -> bool:
        """Start the three miners node with colorized logging."""
        logger.info(Colors.format_header("Starting three miners..."))
        try:
            cmd = ["./three-miners.sh", "snapshot", "restore"]
            self.node_process = subprocess.Popen(
                cmd,
                cwd="../naka3/playbooks/three-miners",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.running = True
            
            time.sleep(5) # Give the process a moment to start
            
            if self.node_process.poll() is not None:
                stdout, _ = self.node_process.communicate()
                logger.error(Colors.format_fail("Node process exited early", f"Output: {stdout}"))
                return False
                
            logger.info(Colors.format_success("Node process started"))
            
            logger.info(Colors.format_grey("Checking miners initialization..."))
            time.sleep(1)
            
            if self.node_process.poll() is not None:
                logger.error(Colors.format_fail("Node process died during initialization"))
                return False
            
            # Now check if miners are ready via endpoint
            from .base import StacksTestBase
            base = StacksTestBase()
            if not base.wait_for_miners_ready():
                logger.warning(Colors.format_warn("(some miners may not be fully ready)"))
            
        except Exception as e:
            logger.critical(Colors.format_fail("Failed to start node", str(e)))
            return False
        return True
    
    def stop_node(self):
        """Stop the three miners node."""
        logger.info(Colors.format_header("Stopping three miners..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "stop"],
                cwd="../naka3/playbooks/three-miners",
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_success("Node stopped"))
        except subprocess.CalledProcessError as e:
            logger.error(Colors.format_fail("Failed to stop node", e.stderr.decode().strip()))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to stop node", str(e)))
    
    def resume_node(self):
        """Resume the three miners node."""
        logger.info(Colors.format_header("Resuming three miners..."))
        try:
            subprocess.run(
                ["./three-miners.sh", "resume"],
                cwd="../naka3/playbooks/three-miners",
                check=True,
                capture_output=True
            )
            logger.info(Colors.format_success("Node resumed"))
        except subprocess.CalledProcessError as e:
            logger.error(Colors.format_fail("Failed to resume node", e.stderr.decode().strip()))
        except Exception as e:
            logger.error(Colors.format_fail("Failed to resume node", str(e)))
    
    def _manage_miner(self, action: str, miner_id: int):
        """Internal helper to stop or resume a specific miner."""
        action_gerund = "Stopping" if action == "stop" else "Resuming"
        action_past = "stopped" if action == "stop" else "resumed"

        logger.info(Colors.format_header(f"{action_gerund} miner{miner_id}..."))
        try:
            cmd = ["../../naka3.sh", "-c", f"./config-miner-{miner_id}.sh", "node", str(miner_id), action]
            subprocess.run(cmd, cwd="../naka3/playbooks/three-miners", check=True, capture_output=True)
            logger.info(Colors.format_success(f"Miner{miner_id} {action_past}"))
        except subprocess.CalledProcessError as e:
            logger.error(Colors.format_fail(f"Failed to {action} miner{miner_id}", e.stderr.decode().strip()))
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