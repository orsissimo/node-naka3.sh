#!/usr/bin/env python3

import subprocess
import time

class NodeManager:
    def __init__(self):
        self.node_process = None
        self.running = False
        
    def start_node(self):
        """Start the three miners node"""
        print("Terminal 1: Starting three miners...")
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
            
            # Give the process a moment to start
            time.sleep(5)
            
            # Check if process is still running
            if self.node_process.poll() is not None:
                stdout, _ = self.node_process.communicate()
                print(f"✗ Node process exited early. Output: {stdout}")
                return False
                
            print("✓ Node process started")
            
            # Give the node time to initialize properly with 1 second + endpoint check
            print("Checking miners initialization", end="\n", flush=True)
            time.sleep(1)  # Brief initial wait as requested
            
            # Check if process is still alive
            if self.node_process.poll() is not None:
                print(f"\n✗ Node process died during initialization")
                return False
            
            # Now check if miners are ready via endpoint
            from .base import StacksTestBase
            base = StacksTestBase()
            if not base.wait_for_miners_ready():
                print(" ⚠ (some miners may not be fully ready)")
                # Continue anyway as long as the process is alive
            
        except Exception as e:
            print(f"✗ Failed to start node: {e}")
            return False
        return True
    
    def stop_node(self):
        """Stop the three miners node"""
        print("Terminal 3: Stopping three miners...")
        try:
            subprocess.run(
                ["./three-miners.sh", "stop"],
                cwd="../naka3/playbooks/three-miners",
                check=True
            )
            print("✓ Node stopped")
        except Exception as e:
            print(f"✗ Failed to stop node: {e}")
    
    def resume_node(self):
        """Resume the three miners node"""
        print("Terminal 3: Resuming three miners...")
        try:
            subprocess.run(
                ["./three-miners.sh", "resume"],
                cwd="../naka3/playbooks/three-miners",
                check=True
            )
            print("✓ Node resumed")
        except Exception as e:
            print(f"✗ Failed to resume node: {e}")
    
    def stop_miner(self, miner_id: int):
        """Stop specific miner (1, 2, or 3)"""
        print(f"Stopping miner{miner_id}...")
        try:
            cmd = [f"../../naka3.sh", "-c", f"./config-miner-{miner_id}.sh", "node", str(miner_id), "stop"]
            subprocess.run(cmd, cwd="../naka3/playbooks/three-miners", check=True)
            print(f"✓ Miner{miner_id} stopped")
        except Exception as e:
            print(f"✗ Failed to stop miner{miner_id}: {e}")
    
    def resume_miner(self, miner_id: int):
        """Resume specific miner (1, 2, or 3)"""
        print(f"Resuming miner{miner_id}...")
        try:
            cmd = [f"../../naka3.sh", "-c", f"./config-miner-{miner_id}.sh", "node", str(miner_id), "resume"]
            subprocess.run(cmd, cwd="../naka3/playbooks/three-miners", check=True)
            print(f"✓ Miner{miner_id} resumed")
        except Exception as e:
            print(f"✗ Failed to resume miner{miner_id}: {e}")
    
    def cleanup(self):
        """Clean up the node process"""
        if self.node_process and self.running:
            self.node_process.terminate()
            self.node_process.wait()
            self.running = False