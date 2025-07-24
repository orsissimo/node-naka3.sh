import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .base import StacksTestBase
from .node_manager import NodeManager
from .transaction import Transaction
from .contract import Contract
from .nft import NFT
from .mempool import Mempool

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
            'mempool': Mempool(),
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
            
            for step in recipe.steps:
                step_result = self._run_step(step)
                result['steps'].append(step_result)
                
                if not step_result['success'] and step.on_error == "stop":
                    result['success'] = False
                    break
            
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

class Recipes:
    pass  # All static methods removed - they were unused