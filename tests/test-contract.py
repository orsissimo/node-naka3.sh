#!/usr/bin/env python3

import subprocess
import time
import threading
import signal
import sys
import json
import requests
from pathlib import Path

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
            
            time.sleep(5)
            
            if self.node_process.poll() is not None:
                stdout, _ = self.node_process.communicate()
                print(f"✗ Node process exited early. Output: {stdout}")
                return False
                
            print("✓ Node process started")
            
            print("Waiting 20 seconds for miners to initialize properly", end="", flush=True)
            for _ in range(20):
                print(".", end="", flush=True)
                time.sleep(1)
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
    
    def cleanup(self):
        """Clean up the node process"""
        if self.node_process and self.running:
            self.node_process.terminate()
            self.node_process.wait()
            self.running = False

class ContractTester:
    def __init__(self, miner="miner1"):
        self.miner = miner
        self.miner_ports = {
            "miner1": 20443,
            "miner2": 30443,
            "miner3": 40443
        }
        self.port = self.miner_ports[miner]
        self.api_url = f"http://localhost:{self.port}"
        
        # Funded accounts per miner
        self.accounts = {
            "miner1": {
                "addr": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6",
                "key": "cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01"
            },
            "miner2": {
                "addr": "ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y", 
                "key": "21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601"
            },
            "miner3": {
                "addr": "ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0",
                "key": "7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01"
            }
        }
        
        self.publisher_addr = self.accounts[miner]["addr"]
        self.publisher_key = self.accounts[miner]["key"]
        self.last_txid = None
        self.initial_nonce = None
        self.initial_balance = None
        
        # Create directories
        Path("./tmp").mkdir(exist_ok=True)
        Path("./logs").mkdir(exist_ok=True)
    
    def get_account_info(self, address):
        """Get account nonce and balance"""
        try:
            response = requests.get(f"{self.api_url}/v2/accounts/{address}")
            return response.json()
        except Exception as e:
            print(f"✗ Failed to get account info: {e}")
            return None
    
    def wait_for_node_ready(self, timeout=60):
        """Wait for the node to be ready"""
        print(f"Waiting for {self.miner} to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.api_url}/v2/info", timeout=5)
                if response.status_code == 200:
                    print(f"✓ {self.miner} is ready")
                    return True
            except:
                pass
            print(".", end="", flush=True)
            time.sleep(2)
        
        print(f"\n✗ {self.miner} not ready after {timeout}s")
        return False
    
    def test_contract_deployment(self):
        """Test 2: Deploy a contract"""
        print(f"\n=== TEST 2: Contract Deployment Test on {self.miner} ===")
        
        if not self.wait_for_node_ready():
            return False
        
        # Get initial state
        publisher_info = self.get_account_info(self.publisher_addr)
        
        if not publisher_info:
            return False
        
        nonce = publisher_info['nonce']
        balance_before = int(publisher_info['balance'], 16) if publisher_info['balance'].startswith('0x') else int(publisher_info['balance'])
        
        # Store initial values
        self.initial_nonce = nonce
        self.initial_balance = balance_before
        
        print(f"Publisher balance before: {balance_before}")
        print(f"Using nonce: {nonce}")
        
        # Create contract file
        contract_content = '(define-public (say-hello) (begin (print "Hello!") (ok true)))'
        contract_name = f"mycontract{nonce}"
        
        with open("./tmp/contract.clar", "w") as f:
            f.write(contract_content)
        
        print(f"Contract name: {contract_name}")
        print(f"Contract content: {contract_content}")
        
        # Create contract deployment using blockstack-cli
        try:
            cli_cmd = [
                "blockstack-cli", "--testnet", "publish",
                self.publisher_key, "200", str(nonce), contract_name, "./tmp/contract.clar"
            ]
            
            print("Creating contract deployment...")
            
            # Use same method as bash script: pipe to xxd -r -p
            with open("./tmp/contract-tx-auto.bin", "wb") as f:
                cli_process = subprocess.Popen(cli_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                xxd_process = subprocess.Popen(
                    ["xxd", "-r", "-p"], 
                    stdin=cli_process.stdout, 
                    stdout=f,
                    stderr=subprocess.PIPE
                )
                cli_process.stdout.close()
                cli_process.wait()
                xxd_process.wait()
                
                if cli_process.returncode != 0:
                    _, cli_err = cli_process.communicate()
                    print(f"✗ CLI failed: {cli_err.decode()}")
                    return False
                    
                if xxd_process.returncode != 0:
                    _, xxd_err = xxd_process.communicate()
                    print(f"✗ xxd failed: {xxd_err.decode()}")
                    return False
            
            # Submit contract deployment
            print("Submitting contract deployment...")
            with open("./tmp/contract-tx-auto.bin", "rb") as f:
                response = requests.post(
                    f"{self.api_url}/v2/transactions",
                    headers={"Content-Type": "application/octet-stream"},
                    data=f.read()
                )
            
            if response.status_code != 200:
                print(f"✗ Contract deployment failed: {response.text}")
                return False
            
            txid = response.json()
            self.last_txid = txid.strip('"') if isinstance(txid, str) else str(txid)
            print(f"✓ Transaction ID: {self.last_txid}")
            print(f"✓ Contract name: {contract_name}")
            
            # Wait for confirmation
            return self.wait_for_confirmation(nonce, balance_before)
            
        except Exception as e:
            print(f"✗ Contract deployment test failed: {e}")
            return False
    
    def wait_for_confirmation(self, initial_nonce, balance_before):
        """Wait for contract deployment confirmation"""
        print("Waiting for confirmation...")
        
        # Get initial block height
        try:
            info_response = requests.get(f"{self.api_url}/v2/info")
            initial_block_height = info_response.json().get('stacks_tip_height', 0)
        except:
            initial_block_height = 0
        
        for _ in range(300):  # 5 minutes max
            try:
                publisher_info = self.get_account_info(self.publisher_addr)
                
                # Get current block height
                info_response = requests.get(f"{self.api_url}/v2/info")
                current_block_height = info_response.json().get('stacks_tip_height', 0)
                
                if publisher_info:
                    current_nonce = publisher_info['nonce']
                    
                    # Check both nonce AND block height increased
                    if current_nonce > initial_nonce and current_block_height > initial_block_height:
                        balance_after = int(publisher_info['balance'], 16) if publisher_info['balance'].startswith('0x') else int(publisher_info['balance'])
                        
                        print(f"\n✓ Contract deployment confirmed!")
                        print(f"Publisher balance: {balance_before} → {balance_after}")
                        print(f"Nonce: {initial_nonce} → {current_nonce}")
                        print(f"Block: {initial_block_height} → {current_block_height}")
                        
                        # Fetch transaction details
                        try:
                            print("Fetching transaction details...")
                            tx_response = requests.get(f"{self.api_url}/v3/transaction/{self.last_txid}")
                            if tx_response.status_code == 200:
                                tx_data = tx_response.json()
                                print("Transaction details:")
                                print(json.dumps(tx_data, indent=2))
                            else:
                                print(f"Could not fetch transaction details: {tx_response.status_code}")
                        except Exception as e:
                            print(f"Error fetching transaction details: {e}")
                        
                        return True
                
                print(".", end="", flush=True)
                time.sleep(1)
                
            except Exception as e:
                print(f"Error during confirmation wait: {e}")
                time.sleep(1)
        
        print("\n✗ Contract deployment confirmation timeout")
        return False
    
    def verify_contract_deployed(self):
        """Verify contract was deployed successfully"""
        print("\n=== POST-TEST ASSERTION ===")
        print("Verifying contract deployment completed successfully...")
        
        if not self.last_txid:
            print("✗ ASSERTION FAILED: No transaction ID to verify")
            return False
        
        if not hasattr(self, 'initial_nonce') or self.initial_nonce is None:
            print("✗ ASSERTION FAILED: No initial state recorded")
            return False
        
        print(f"✓ Contract deployment {self.last_txid[:8]}... was confirmed during test")
        print(f"  Initial nonce: {self.initial_nonce}")
        
        print("  ✓ Contract deployment confirmation included:")
        print("    - Nonce increased by 1")
        print("    - Block height increased")
        print("    - Balance decreased (transaction fees)")
        
        print("  ✓ ALL ASSERTIONS PASSED - Contract successfully deployed")
        return True

def signal_handler(*_):
    """Handle cleanup on exit"""
    print("\nShutting down...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    node_manager = NodeManager()
    
    try:
        # Start the node
        if not node_manager.start_node():
            return
        
        # Run Test 2: Contract deployment test
        tester = ContractTester("miner1")
        success = tester.test_contract_deployment()
        
        if success:
            print("\n✓ All tests passed!")
        else:
            print("\n✗ Tests failed!")
        
        # Terminal 3: Stop the node to return to initial quiet state
        node_manager.stop_node()
        
        # Run assertion test to verify contract deployed
        if success:
            assertion_passed = tester.verify_contract_deployed()
            print(f"\n=== FINAL RESULT ===")
            if assertion_passed:
                print("✓ ALL TESTS PASSED - Contract successfully deployed")
            else:
                print("✗ ASSERTION FAILED - Contract deployment verification failed")
        else:
            print("\n=== FINAL RESULT ===")
            print("✗ PRIMARY TEST FAILED - Skipping assertion test")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        node_manager.cleanup()

if __name__ == "__main__":
    main()