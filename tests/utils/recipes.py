import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .base import StacksTestBase
from .node_manager import NodeManager
from .transaction import Transaction
from .contract import Contract
from .nft import NFT

@dataclass
class Step:
    name: str
    module: str
    method: str
    params: Dict[str, Any]
    wait: bool = True
    on_error: str = "stop"
    retries: int = 0

@dataclass
class Recipe:
    name: str
    description: str
    steps: List[Step]
    setup: bool = True
    cleanup: bool = True

class Runner(StacksTestBase):
    
    def __init__(self):
        super().__init__()
        self.node = NodeManager()
        self.modules = {
            'transaction': Transaction(),
            'contract': Contract(),
            'nft': NFT(),
                        'node': self.node
        }
    
    def run(self, recipe: Recipe) -> Dict[str, Any]:
        start_time = time.time()
        result = {
            'name': recipe.name,
            'success': True,
            'steps': [],
            'start_time': start_time,
            'setup_success': True,
            'cleanup_success': True
        }
        
        try:
            if recipe.setup:
                self.node.start_node()
                if not self.verify_chain_progression("miner1"):
                    result['setup_success'] = False
                    result['success'] = False
                    return result
            
            # Capture initial chain state before executing steps
            initial_chain_state = self._capture_chain_state()
            
            for step in recipe.steps:
                step_result = self._run_step(step)
                result['steps'].append(step_result)
                
                if not step_result['success'] and step.on_error == "stop":
                    result['success'] = False
                    break
            
            # Verify final chain progression after all steps complete
            final_chain_verification = self._verify_final_chain_progression(initial_chain_state)
            result.update(final_chain_verification)
            
            if any(not s['success'] for s in result['steps']):
                result['success'] = False
                
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            
        finally:
            if recipe.cleanup:
                try:
                    self.node.stop_node()
                except Exception as e:
                    result['cleanup_success'] = False
                    result['cleanup_error'] = str(e)
        
        result['duration'] = time.time() - start_time
        return result
    
    def _run_step(self, step: Step) -> Dict[str, Any]:
        result = {'name': step.name, 'success': False, 'start_time': time.time(), 'retries': 0}
        
        for attempt in range(step.retries + 1):
            try:
                if step.module not in self.modules:
                    raise ValueError(f"Unknown module: {step.module}")
                
                module = self.modules[step.module]
                method = getattr(module, step.method)
                res = method(**step.params)
                
                result.update({'success': True, 'result': res, 'retries': attempt})
                break
                
            except Exception as e:
                result['error'] = str(e)
                if attempt < step.retries:
                    time.sleep(2 ** attempt)
                else:
                    result['success'] = False
        
        result['duration'] = time.time() - result['start_time']
        return result
    
    def _capture_chain_state(self) -> Dict[str, Any]:
        """Capture initial chain state for all miners"""
        try:
            chain_state = {}
            for miner in ["miner1", "miner2", "miner3"]:
                account = self.get_account(miner)
                chain_state[miner] = {
                    'block_height': self.get_block_height(miner),
                    'balance': self.get_balance(miner),
                    'nonce': self.get_nonce(miner),
                    'address': account.address
                }
            return chain_state
        except Exception as e:
            return {'error': f"Failed to capture initial chain state: {str(e)}"}
    
    def _verify_final_chain_progression(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """Verify chain progression across all miners after recipe completion"""
        verification_result = {
            'chain_progression_verified': True,
            'chain_verification_details': {}
        }
        
        try:
            if 'error' in initial_state:
                verification_result['chain_progression_verified'] = False
                verification_result['chain_verification_error'] = initial_state['error']
                return verification_result
            
            final_state = {}
            chain_details = {}
            
            for miner in ["miner1", "miner2", "miner3"]:
                try:
                    initial = initial_state[miner]
                    final_state[miner] = {
                        'block_height': self.get_block_height(miner),
                        'balance': self.get_balance(miner),
                        'nonce': self.get_nonce(miner),
                        'address': initial['address']
                    }
                    
                    # Calculate progression
                    height_change = final_state[miner]['block_height'] - initial['block_height']
                    balance_change = final_state[miner]['balance'] - initial['balance']
                    nonce_change = final_state[miner]['nonce'] - initial['nonce']
                    
                    chain_details[miner] = {
                        'initial_height': initial['block_height'],
                        'final_height': final_state[miner]['block_height'],
                        'height_progression': height_change,
                        'initial_balance': initial['balance'],
                        'final_balance': final_state[miner]['balance'],
                        'balance_change': balance_change,
                        'initial_nonce': initial['nonce'],
                        'final_nonce': final_state[miner]['nonce'],
                        'nonce_progression': nonce_change
                    }
                    
                    # Verify reasonable progression
                    if height_change < 0:
                        verification_result['chain_progression_verified'] = False
                        chain_details[miner]['error'] = "Block height decreased"
                    if nonce_change < 0:
                        verification_result['chain_progression_verified'] = False
                        chain_details[miner]['error'] = "Nonce decreased"
                        
                except Exception as e:
                    verification_result['chain_progression_verified'] = False
                    chain_details[miner] = {'error': f"Failed to verify {miner}: {str(e)}"}
            
            verification_result['chain_verification_details'] = chain_details
            
            # Check cross-miner consistency
            heights = [details.get('final_height', 0) for details in chain_details.values() if 'error' not in details]
            if len(heights) > 1:
                height_variance = max(heights) - min(heights)
                verification_result['height_variance'] = height_variance
                if height_variance > 5:  # Allow some variance but flag large differences
                    verification_result['chain_progression_verified'] = False
                    verification_result['chain_verification_error'] = f"Large height variance across miners: {height_variance} blocks"
            
        except Exception as e:
            verification_result['chain_progression_verified'] = False
            verification_result['chain_verification_error'] = f"Chain verification failed: {str(e)}"
        
        return verification_result

class Recipes:
    pass  # All static methods removed - they were unused