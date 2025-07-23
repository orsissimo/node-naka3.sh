import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Callable
from .base import StacksTestBase
from .transaction import Transaction
from .contract import Contract

class Mempool(StacksTestBase):
    
    def __init__(self):
        super().__init__()
        self.tx = Transaction()
        self.contract = Contract()
    
    def flood(self, miner: str, count: int, amount: int = 1, max_workers: int = 5) -> Dict[str, Any]:
        target = self.ACCOUNTS["miner2" if miner != "miner2" else "miner3"].address
        initial_nonce = self.get_nonce(miner)
        initial_balance = self.get_balance(miner)
        initial_height = self.get_block_height(miner)
        
        results, errors = [], []
        
        def create_tx(nonce_offset):
            try:
                txid = self.tx.transfer(miner, target, amount, f"flood_{nonce_offset}", initial_nonce + nonce_offset)
                return {'success': True, 'txid': txid, 'nonce': initial_nonce + nonce_offset}
            except Exception as e:
                error_msg = str(e)
                if "TooMuchChaining" in error_msg:
                    return {'success': False, 'error': 'TooMuchChaining', 'nonce': initial_nonce + nonce_offset}
                return {'success': False, 'error': error_msg, 'nonce': initial_nonce + nonce_offset}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for future in as_completed([executor.submit(create_tx, i) for i in range(count)]):
                result = future.result()
                (results if result['success'] else errors).append(result)
        
        confirmation_success = False
        if results:
            max_nonce = max(r['nonce'] for r in results)
            confirmation_success = self.wait_for_confirmation(miner, max_nonce, initial_height, timeout=180)
        
        return {
            'success': len(results) > 0,
            'total_attempted': count,
            'successful_submissions': len(results),
            'failed_submissions': len(errors),
            'confirmation_success': confirmation_success,
            'successful_txids': [r['txid'] for r in results],
            'errors': errors,
            'initial_balance': initial_balance,
            'final_balance': self.get_balance(miner)
        }
    
    def mixed_stress(self, miner: str, tx_count: int, contract_count: int, contract_file: str, max_workers: int = 3) -> Dict[str, Any]:
        initial_nonce = self.get_nonce(miner)
        initial_height = self.get_block_height(miner)
        results = {'transactions': [], 'contracts': [], 'errors': []}
        
        def create_op(nonce_offset, op_type):
            try:
                if op_type == 'transaction':
                    target = self.ACCOUNTS["miner2" if miner != "miner2" else "miner3"].address
                    txid = self.tx.transfer(miner, target, 1, f"mixed_{nonce_offset}", initial_nonce + nonce_offset)
                    return {'type': 'transaction', 'success': True, 'txid': txid, 'nonce': initial_nonce + nonce_offset}
                else:
                    txid = self.contract.deploy(miner, contract_file, f"counter-stress-{nonce_offset}", initial_nonce + nonce_offset)
                    return {'type': 'contract', 'success': True, 'txid': txid, 'contract_name': f"counter-stress-{nonce_offset}", 'nonce': initial_nonce + nonce_offset}
            except Exception as e:
                return {'type': op_type, 'success': False, 'error': str(e), 'nonce': initial_nonce + nonce_offset}
        
        operations = [(i, 'transaction') for i in range(tx_count)] + [(tx_count + i, 'contract') for i in range(contract_count)]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for future in as_completed([executor.submit(create_op, nonce, op_type) for nonce, op_type in operations]):
                result = future.result()
                if result['success']:
                    results[result['type'] + 's'].append(result)
                else:
                    results['errors'].append(result)
        
        total_successful = len(results['transactions']) + len(results['contracts'])
        confirmation_success = False
        if total_successful > 0:
            confirmation_success = self.wait_for_confirmation(miner, initial_nonce + len(operations) - 1, initial_height, timeout=240)
        
        return {
            'success': total_successful > 0,
            'total_attempted': tx_count + contract_count,
            'successful_transactions': len(results['transactions']),
            'successful_contracts': len(results['contracts']),
            'failed_operations': len(results['errors']),
            'confirmation_success': confirmation_success,
            'results': results
        }
    
    def info(self, miner: str) -> Dict[str, Any]:
        try:
            response = self.api_call(self.get_account(miner), "/v2/info")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {'error': str(e)}
    
    def monitor_stress(self, miner: str, stress_function: Callable, monitor_interval: int = 5) -> Dict[str, Any]:
        monitoring_data = []
        monitoring_active = True
        
        def monitor():
            while monitoring_active:
                try:
                    monitoring_data.append({'timestamp': time.time(), 'info': self.info(miner)})
                except Exception:
                    pass
                time.sleep(monitor_interval)
        
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.start()
        
        try:
            stress_result = stress_function()
        finally:
            monitoring_active = False
            monitor_thread.join(timeout=10)
        
        return {'stress_result': stress_result, 'monitoring_data': monitoring_data}