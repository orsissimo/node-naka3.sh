#!/usr/bin/env python3

import os
import sys
import time

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_api, get_nonce, get_balance, get_account_info_typed
from utils.config import MinerName, AccountManager
from utils.miners import MinerManager
from utils.logger import Colors

def check_miner_connectivity(miner: MinerName) -> dict:
    """Check if miner API is responsive"""
    result = {'miner': miner, 'connected': False, 'error': None}
    
    try:
        api = get_api(miner)
        account = AccountManager.get(miner)
        
        # Try to get account info
        account_info = get_account_info_typed(api, account.address)
        nonce = account_info.nonce
        
        # Try to get node info
        info = api.get_info()
        height = info.get('stacks_tip_height', 0)
        
        result['connected'] = True
        result['nonce'] = nonce
        result['height'] = height
        result['address'] = account.address
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

def print_connectivity_status(miners: list):
    """Print connectivity status for all miners"""
    print(f"\n{Colors.format_header('Miner Connectivity Status')}")
    
    for miner in miners:
        status = check_miner_connectivity(miner)
        if status['connected']:
            print(f"  {miner.value}: {Colors.format_success('CONNECTED')} - Height: {status['height']}, Nonce: {status['nonce']}")
        else:
            print(f"  {miner.value}: {Colors.format_error('DISCONNECTED')} - Error: {status['error']}")

def main():
    """Execute the miner stop/resume test"""
    print(f"{Colors.format_dim('=' * 80)}")
    print(f"{Colors.format_header('MINER STOP/RESUME TEST')}")
    print(f"{Colors.format_dim('=' * 80)}")
    
    # Raw minimal setup
    miner_manager = MinerManager()
    miners = [MinerName.MINER1, MinerName.MINER2, MinerName.MINER3]
    
    try:
        # Start all miners
        print(f"\n{Colors.format_stacks('Starting all miners...')}")
        if not miner_manager.snapshot_restore("auto"):
            raise RuntimeError("Failed to start miners")
        
        # Initial connectivity check
        print(f"\n{Colors.format_header('Step 1: Initial connectivity check')}")
        print_connectivity_status(miners)
        
        # Stop miner2
        print(f"\n{Colors.format_header('Step 2: Stopping miner2')}")
        miner_manager.stop_miner(2)
        time.sleep(5)  # Give time for miner to stop
        
        print(f"\n{Colors.format_subheader('Connectivity after stopping miner2:')}")
        print_connectivity_status(miners)
        
        # Verify miner1 and miner3 still work
        print(f"\n{Colors.format_header('Step 3: Testing remaining miners')}")
        for miner in [MinerName.MINER1, MinerName.MINER3]:
            try:
                api = get_api(miner)
                account = AccountManager.get(miner)
                balance = get_balance(api, account.address)
                nonce = get_nonce(api, account.address)
                print(f"  {miner.value}: Balance: {balance:,} µSTX, Nonce: {nonce}")
            except Exception as e:
                print(f"  {miner.value}: {Colors.format_error('ERROR')} - {e}")
        
        # Stop miner3
        print(f"\n{Colors.format_header('Step 4: Stopping miner3')}")
        miner_manager.stop_miner(3)
        time.sleep(5)  # Give time for miner to stop
        
        print(f"\n{Colors.format_subheader('Connectivity after stopping miner3:')}")
        print_connectivity_status(miners)
        
        # Resume miner2
        print(f"\n{Colors.format_header('Step 5: Resuming miner2')}")
        miner_manager.resume_miner(2)
        time.sleep(10)  # Give time for miner to start
        
        print(f"\n{Colors.format_subheader('Connectivity after resuming miner2:')}")
        print_connectivity_status(miners)
        
        # Resume miner3
        print(f"\n{Colors.format_header('Step 6: Resuming miner3')}")
        miner_manager.resume_miner(3)
        time.sleep(10)  # Give time for miner to start
        
        print(f"\n{Colors.format_subheader('Connectivity after resuming miner3:')}")
        print_connectivity_status(miners)
        
        # Final connectivity check
        print(f"\n{Colors.format_header('Step 7: Final connectivity check')}")
        print_connectivity_status(miners)
        
        # Count working miners
        working_miners = 0
        for miner in miners:
            status = check_miner_connectivity(miner)
            if status['connected']:
                working_miners += 1
        
        # Test summary
        print(f"\n{Colors.format_dim('=' * 80)}")
        print(f"{Colors.format_header('TEST SUMMARY')}")
        print(f"{Colors.format_dim('=' * 80)}")
        
        print(f"{Colors.format_info('Working miners')}: {Colors.format_dim(f'{working_miners}/3')}")
        
        if working_miners == 3:
            print(f"{Colors.format_success('✓ All miners working - stop/resume test PASSED')}")
            return True
        else:
            print(f"{Colors.format_error('✗ Some miners not working - stop/resume test FAILED')}")
            return False
        
    except Exception as e:
        print(f"\n{Colors.format_error('TEST FAILED')}: {Colors.format_error(str(e))}")
        return False
        
    finally:
        # Cleanup
        print(f"\n{Colors.format_header('Cleaning up...')}")
        miner_manager.stop()
        miner_manager.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)