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
            
            # Give the node time to initialize properly
            print("Waiting 20 seconds for miners to initialize properly", end="", flush=True)
            for _ in range(20):
                print(".", end="", flush=True)
                time.sleep(1)
                # Check if process is still alive
                if self.node_process.poll() is not None:
                    print(f"\n✗ Node process died during initialization")
                    return False
            print(" ✓")
            
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
    
    def cleanup(self):
        """Clean up the node process"""
        if self.node_process and self.running:
            self.node_process.terminate()
            self.node_process.wait()
            self.running = False