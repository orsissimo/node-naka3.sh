#!/usr/bin/env python3

import subprocess
import time
import signal
import sys
import json
import requests
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import NodeManager

class MempoolStressTester:
    def __init__(self):
        self.miners = {
            "miner1": {"port": 20443, "addr": "STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6", "key": "cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01"},
            "miner2": {"port": 30443, "addr": "ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y", "key": "21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601"},
            "miner3": {"port": 40443, "addr": "ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0", "key": "7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01"}
        }
        
        # Use miner1 as recipient for all transfers
        self.recipient_addr = "ST3KCNDSWZSFZCC6BE4VA9AXWXC9KEB16FBTRK36T"
        
        # Counters
        self.total_transactions = 0
        self.successful_transactions = 0
        self.failed_transactions = 0
        self.submitted_txids = []
        
        # Create directories
        Path("./tmp").mkdir(exist_ok=True)
        Path("./logs").mkdir(exist_ok=True)
    
    def cleanup_tmp_files(self):
        """Clean up temporary files created during testing"""
        try:
            tmp_dir = Path("./tmp")
            if tmp_dir.exists():
                # Remove all .bin and .clar files
                for file_pattern in ["*.bin", "*.clar"]:
                    for file_path in tmp_dir.glob(file_pattern):
                        file_path.unlink()
                        
                # Count remaining files for verification
                remaining_files = list(tmp_dir.iterdir())
                if remaining_files:
                    print(f"✓ Cleaned tmp folder, {len(remaining_files)} files remain")
                else:
                    print("✓ Cleaned tmp folder completely")
            else:
                print("✓ No tmp folder to clean")
        except Exception as e:
            print(f"⚠ Error cleaning tmp files: {e}")
    
    def get_account_info(self, miner_name, address):
        """Get account nonce and balance for a specific miner"""
        try:
            api_url = f"http://localhost:{self.miners[miner_name]['port']}"
            response = requests.get(f"{api_url}/v2/accounts/{address}")
            return response.json()
        except Exception as e:
            print(f"✗ Failed to get account info from {miner_name}: {e}")
            return None
    
    def get_mempool_info(self, miner_name):
        """Get mempool information"""
        try:
            api_url = f"http://localhost:{self.miners[miner_name]['port']}"
            response = requests.get(f"{api_url}/v2/info/mempool", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                # Mempool endpoint might not exist, try alternative
                return {"count": 0, "txids": []}
        except Exception as e:
            # Don't print error during final check when nodes are down
            return None
    
    def wait_for_nodes_ready(self):
        """Wait for all miners to be ready"""
        print("Waiting for all miners to be ready...")
        for miner_name, miner_info in self.miners.items():
            api_url = f"http://localhost:{miner_info['port']}"
            timeout = 60
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(f"{api_url}/v2/info", timeout=5)
                    if response.status_code == 200:
                        print(f"✓ {miner_name} is ready")
                        break
                except:
                    pass
                print(".", end="", flush=True)
                time.sleep(2)
            else:
                print(f"\n✗ {miner_name} not ready after {timeout}s")
                return False
        return True
    
    def create_transaction(self, miner_name, nonce, amount=100):
        """Create a single transaction"""
        try:
            miner_info = self.miners[miner_name]
            memo = f"Stress{nonce}_{miner_name}"
            
            cli_cmd = [
                "blockstack-cli", "--testnet", "token-transfer",
                miner_info["key"], "180", str(nonce), self.recipient_addr, str(amount), memo
            ]
            
            # Create transaction binary
            tx_file = f"./tmp/tx_{miner_name}_{nonce}.bin"
            with open(tx_file, "wb") as f:
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
                    return None
                    
                if xxd_process.returncode != 0:
                    return None
            
            return tx_file
            
        except Exception as e:
            print(f"✗ Error creating transaction for {miner_name}: {e}")
            return None
    
    def submit_transaction(self, miner_name, tx_file):
        """Submit a transaction to a specific miner with detailed error reporting"""
        try:
            api_url = f"http://localhost:{self.miners[miner_name]['port']}"
            
            with open(tx_file, "rb") as f:
                response = requests.post(
                    f"{api_url}/v2/transactions",
                    headers={"Content-Type": "application/octet-stream"},
                    data=f.read(),
                    timeout=15
                )
            
            if response.status_code == 200:
                txid = response.json()
                txid = txid.strip('"') if isinstance(txid, str) else str(txid)
                self.submitted_txids.append(txid)
                self.successful_transactions += 1
                return txid
            else:
                # Parse error details for better handling
                try:
                    error_data = response.json()
                    error_reason = error_data.get("reason", "Unknown")
                    if error_reason == "TooMuchChaining":
                        # Don't count as failure - this is expected under stress
                        print(f"[{miner_name}] TooMuchChaining - will retry")
                        return "RETRY"  # Special return value to indicate retry needed
                    elif error_reason == "FeeTooLow":
                        print(f"[{miner_name}] Fee too low: expected {error_data.get('reason_data', {}).get('expected', 'unknown')}")
                    elif error_reason == "BadNonce":
                        print(f"[{miner_name}] Bad nonce: {error_data.get('reason_data', {})}")
                    elif error_reason == "NotEnoughFunds":
                        print(f"[{miner_name}] Insufficient funds")
                    else:
                        print(f"[{miner_name}] Error: {error_reason}")
                except:
                    print(f"[{miner_name}] HTTP {response.status_code}: {response.text[:100]}")
                
                self.failed_transactions += 1
                return None
                
        except Exception as e:
            self.failed_transactions += 1
            print(f"[{miner_name}] Exception submitting tx: {e}")
            return None
    
    def create_contract_deployment(self, miner_name, nonce):
        """Create a contract deployment transaction"""
        try:
            miner_info = self.miners[miner_name]
            contract_name = f"contract{miner_name}{nonce}"
            
            # Copy contract from file
            import shutil
            contract_file = f"./tmp/contract_{miner_name}_{nonce}.clar"
            shutil.copy("./contracts/contract-counter.clar", contract_file)
            
            cli_cmd = [
                "blockstack-cli", "--testnet", "publish",
                miner_info["key"], "1000", str(nonce), contract_name, contract_file
            ]
            
            # Create contract deployment binary
            tx_file = f"./tmp/contract_{miner_name}_{nonce}.bin"
            with open(tx_file, "wb") as f:
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
                    return None
                    
                if xxd_process.returncode != 0:
                    return None
            
            return tx_file
            
        except Exception as e:
            print(f"✗ Error creating contract for {miner_name}: {e}")
            return None
    
    def worker_thread(self, worker_id, start_nonce, tx_count, include_contracts=False):
        """Worker thread for a specific miner with proper nonce management"""
        miner_results = {"transactions": 0, "contracts": 0, "failed": 0, "errors": []}
        current_nonce = start_nonce  # Local nonce counter - WE manage this, not the network
        
        # Extract actual miner name from worker ID
        miner_name = worker_id.split('_')[0] if '_' in worker_id else worker_id
        
        print(f"[{worker_id}] Starting with nonce {current_nonce}")
        
        for i in range(tx_count):
            # Create and submit transaction
            tx_success = False
            tx_nonce = current_nonce  # Use current nonce for this transaction
            
            # Keep trying until success or max attempts (including TooMuchChaining retries)
            max_attempts = 10  # Allow more attempts for chaining retries
            for attempt in range(max_attempts):
                try:
                    tx_file = self.create_transaction(miner_name, tx_nonce)
                    if tx_file:
                        txid = self.submit_transaction(miner_name, tx_file)
                        if txid == "RETRY":
                            # TooMuchChaining - wait and retry with same nonce
                            time.sleep(0.2)
                            continue
                        elif txid:
                            miner_results["transactions"] += 1
                            tx_success = True
                            print(f"[{worker_id}] ✓ TX nonce {tx_nonce}: {txid[:8]}...")
                            break
                        else:
                            if attempt < max_attempts - 1:
                                time.sleep(0.1)
                    else:
                        break  # CLI creation failed, don't retry
                        
                except Exception as e:
                    miner_results["errors"].append(f"TX nonce {tx_nonce} attempt {attempt}: {str(e)}")
                    if attempt < max_attempts - 1:
                        time.sleep(0.1)
            
            # ALWAYS increment nonce after attempting transaction, success or failure
            current_nonce += 1
            
            if not tx_success:
                miner_results["failed"] += 1
                print(f"[{worker_id}] ✗ TX nonce {tx_nonce} failed after 3 attempts")
            
            # Create contracts frequently for aggressive stress
            if include_contracts and i % 5 == 0:  # Contract every 5 transactions
                contract_success = False
                contract_nonce = current_nonce  # Use next available nonce
                
                # Allow more attempts for contracts with chaining retries
                max_contract_attempts = 8
                for attempt in range(max_contract_attempts):
                    try:
                        contract_file = self.create_contract_deployment(miner_name, contract_nonce)
                        if contract_file:
                            txid = self.submit_transaction(miner_name, contract_file)
                            if txid == "RETRY":
                                # TooMuchChaining - wait and retry with same nonce
                                time.sleep(0.2)
                                continue
                            elif txid:
                                miner_results["contracts"] += 1
                                contract_success = True
                                print(f"[{worker_id}] ✓ CONTRACT nonce {contract_nonce}: {txid[:8]}...")
                                break
                            else:
                                if attempt < max_contract_attempts - 1:
                                    time.sleep(0.1)
                        else:
                            break
                            
                    except Exception as e:
                        miner_results["errors"].append(f"Contract nonce {contract_nonce} attempt {attempt}: {str(e)}")
                        if attempt < max_contract_attempts - 1:
                            time.sleep(0.1)
                
                # ALWAYS increment nonce after contract attempt
                current_nonce += 1
                
                if not contract_success:
                    miner_results["failed"] += 1
                    print(f"[{worker_id}] ✗ CONTRACT nonce {contract_nonce} failed")
            
            # Aggressive mode - minimal delay
            time.sleep(0.05)  # Small delay to avoid overwhelming
        
        print(f"[{worker_id}] Completed: {miner_results['transactions']} txs, {miner_results['contracts']} contracts, {miner_results['failed']} failed")
        print(f"[{worker_id}] Final nonce: {current_nonce} (used {current_nonce - start_nonce} nonces)")
        
        # Show any critical errors
        if len(miner_results["errors"]) > 5:
            print(f"[{worker_id}] Sample errors: {miner_results['errors'][:3]}")
        
        return worker_id, miner_results
    
    def stress_test_mempool(self, transactions_per_miner=50, include_contracts=True):
        """Fill the mempool with as many transactions as possible"""
        print(f"\n=== Mempool Stress Test ===")
        print(f"Target: {transactions_per_miner} transactions per miner")
        print(f"Include contracts: {include_contracts}")
        
        if not self.wait_for_nodes_ready():
            return False
        
        # Get initial nonces for all miners
        initial_nonces = {}
        for miner_name, miner_info in self.miners.items():
            account_info = self.get_account_info(miner_name, miner_info["addr"])
            if account_info:
                initial_nonces[miner_name] = account_info["nonce"]
                print(f"{miner_name} starting nonce: {initial_nonces[miner_name]}")
            else:
                print(f"✗ Could not get initial nonce for {miner_name}")
                return False
        
        # Show initial mempool state (skip if no endpoint)
        print("\nInitial mempool state:")
        initial_mempool_total = 0
        for miner_name in self.miners.keys():
            mempool_info = self.get_mempool_info(miner_name)
            if mempool_info:
                count = mempool_info.get('count', 0)
                initial_mempool_total += count
                print(f"{miner_name}: {count} transactions")
            else:
                print(f"{miner_name}: mempool info unavailable")
        
        print(f"\nStarting parallel transaction creation...")
        start_time = time.time()
        
        # Run parallel workers  
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            # Single worker per miner for controlled stress
            for miner_name in self.miners.keys():
                future = executor.submit(
                    self.worker_thread, 
                    miner_name, 
                    initial_nonces[miner_name], 
                    transactions_per_miner,
                    include_contracts
                )
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                miner_name, results = future.result()
                print(f"✓ {miner_name}: {results['transactions']} txs, {results['contracts']} contracts, {results['failed']} failed")
        
        duration = time.time() - start_time
        print(f"\nCompleted in {duration:.2f} seconds")
        
        # Wait a moment for propagation and check if transactions are being processed
        print("\nWaiting for mempool and block processing...")
        time.sleep(5)
        
        # Check if transactions are being confirmed
        confirmed_transactions = 0
        for miner_name in self.miners.keys():
            account_info = self.get_account_info(miner_name, self.miners[miner_name]["addr"])
            if account_info:
                final_nonce = account_info["nonce"]
                initial_nonce = initial_nonces[miner_name]
                confirmed = final_nonce - initial_nonce
                confirmed_transactions += confirmed
                print(f"{miner_name}: {confirmed} transactions confirmed (nonce {initial_nonce} → {final_nonce})")
        
        # Show final mempool state (before stopping)
        print("\nFinal mempool state:")
        total_mempool = 0
        for miner_name in self.miners.keys():
            mempool_info = self.get_mempool_info(miner_name)
            if mempool_info:
                count = mempool_info.get('count', 0)
                total_mempool += count
                print(f"{miner_name}: {count} transactions in mempool")
                if count > 0:
                    print(f"  Sample txids: {mempool_info.get('txids', [])[:3]}")
            else:
                print(f"{miner_name}: mempool info unavailable")
        
        print(f"\nSUMMARY:")
        print(f"Total transactions submitted: {self.successful_transactions}")
        print(f"Total failed: {self.failed_transactions}")
        print(f"Total confirmed: {confirmed_transactions}")
        print(f"Total in mempool: {total_mempool}")
        print(f"Success rate: {(self.successful_transactions/(self.successful_transactions+self.failed_transactions)*100):.1f}%")
        
        # Store results for assertion
        self.total_confirmed = confirmed_transactions
        self.total_mempool = total_mempool
        
        return True
    
    def verify_chain_progression(self):
        """Verify that the blockchain is still progressing after our stress test"""
        print("\n=== Chain Progression Verification ===")
        
        try:
            # Get initial heights from miner1
            api_url = f"http://localhost:{self.miners['miner1']['port']}"
            initial_info = requests.get(f"{api_url}/v2/info", timeout=10).json()
            initial_stacks_height = initial_info.get('stacks_tip_height', 0)
            initial_burn_height = initial_info.get('burn_block_height', 0)
            
            print(f"Initial heights - Stacks: {initial_stacks_height}, Burn: {initial_burn_height}")
            
            max_retries = 5
            wait_time = 9  # 9 seconds per retry = 45 seconds total
            
            for retry in range(max_retries):
                print(f"Waiting {wait_time} seconds to check chain progression (attempt {retry + 1}/{max_retries})...")
                time.sleep(wait_time)
                
                # Get current heights
                current_info = requests.get(f"{api_url}/v2/info", timeout=10).json()
                current_stacks_height = current_info.get('stacks_tip_height', 0)
                current_burn_height = current_info.get('burn_block_height', 0)
                
                print(f"Current heights - Stacks: {current_stacks_height}, Burn: {current_burn_height}")
                
                # Check progression
                stacks_progressed = current_stacks_height > initial_stacks_height
                burn_progressed = current_burn_height >= initial_burn_height
                
                if stacks_progressed and burn_progressed:
                    print(f"✓ Stacks chain progressed: {initial_stacks_height} → {current_stacks_height}")
                    print(f"✓ Burn chain stable/progressed: {initial_burn_height} → {current_burn_height}")
                    print("✓ CHAIN PROGRESSION VERIFIED - Network is healthy")
                    return True
                elif stacks_progressed:
                    print(f"✓ Stacks chain progressed: {initial_stacks_height} → {current_stacks_height}")
                    print(f"⚠ Burn chain did not progress: {initial_burn_height} → {current_burn_height}")
                    print("✓ CHAIN PROGRESSION VERIFIED - Stacks network is healthy")
                    return True
                else:
                    print(f"⚠ Stacks chain did not progress yet: {initial_stacks_height} → {current_stacks_height}")
                    if retry < max_retries - 1:
                        print("Retrying...")
            
            # If we get here, all retries failed
            print("✗ CHAIN PROGRESSION FAILED - Network may be stalled after 5 retries")
            return False
                
        except Exception as e:
            print(f"✗ Error verifying chain progression: {e}")
            return False
    
    def verify_stress_test_success(self):
        """Verify that stress test was successful"""
        print("\n=== Stress Test Verification ===")
        print("Checking transaction processing and mempool stress...")
        
        # Check transaction submission success 
        if self.successful_transactions < 200:
            print(f"✗ ASSERTION FAILED: Only {self.successful_transactions} transactions submitted successfully")
            return False
        
        # Check that transactions were processed (confirmed or in mempool)
        total_processed = getattr(self, 'total_confirmed', 0) + getattr(self, 'total_mempool', 0)
        
        if total_processed >= 200:
            print(f"✓ ASSERTION PASSED: {total_processed} transactions processed")
            print(f"  - {getattr(self, 'total_confirmed', 0)} confirmed")
            print(f"  - {getattr(self, 'total_mempool', 0)} in mempool")
            print(f"  - Success rate: {(self.successful_transactions/(self.successful_transactions+self.failed_transactions)*100):.1f}%")
            return True
        else:
            print(f"✗ ASSERTION FAILED: Only {total_processed} transactions processed")
            print(f"  - Expected at least 200 transactions to stress the mempool")
            return False

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
        
        # Run aggressive mempool stress test
        tester = MempoolStressTester()
        success = tester.stress_test_mempool(transactions_per_miner=100, include_contracts=True)
        
        if success:
            print("\n✓ Stress test completed!")
        else:
            print("\n✗ Stress test failed!")
        
        # Verify chain progression BEFORE stopping the node
        chain_healthy = False
        if success:
            chain_healthy = tester.verify_chain_progression()
        
        # Terminal 3: Stop the node to return to initial quiet state
        node_manager.stop_node()
        
        # Run assertion test to verify stress test success
        if success:
            assertion_passed = tester.verify_stress_test_success()
            
            print(f"\n=== FINAL RESULT ===")
            if assertion_passed and chain_healthy:
                print("✓ ALL TESTS PASSED - Mempool stress test successful and chain healthy")
            elif assertion_passed:
                print("⚠ PARTIAL SUCCESS - Stress test passed but chain progression uncertain")
            else:
                print("✗ ASSERTION FAILED - Stress test did not meet success criteria")
        else:
            print("\n=== FINAL RESULT ===")
            print("✗ PRIMARY TEST FAILED - Skipping assertion test")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        node_manager.cleanup()
        
        # Clean up tmp files after test completion
        if 'tester' in locals():
            tester.cleanup_tmp_files()

if __name__ == "__main__":
    main()