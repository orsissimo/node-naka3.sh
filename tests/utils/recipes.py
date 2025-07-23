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
    
    @staticmethod
    def tx_test() -> Recipe:
        return Recipe(
            name="Basic Transaction",
            description="STX transfer test",
            steps=[
                Step(
                    name="Transfer STX",
                    module="transaction",
                    method="transfer",
                    params={
                        "from_miner": "miner1",
                        "to_address": Transaction.ACCOUNTS["miner2"].address,
                        "amount": 1000,
                        "memo": "test"
                    }
                )
            ]
        )
    
    @staticmethod
    def contract_test() -> Recipe:
        return Recipe(
            name="Contract Test",
            description="Deploy and test contract",
            steps=[
                Step(
                    name="Deploy counter",
                    module="contract",
                    method="deploy_and_test",
                    params={
                        "miner": "miner1",
                        "contract_file": "contracts/contract-counter.clar",
                        "contract_name": "counter-test",
                        "test_functions": [
                            {"name": "get-counter", "type": "read"},
                            {"name": "increment", "type": "public"},
                            {"name": "get-counter", "type": "read"}
                        ]
                    }
                )
            ]
        )
    
    @staticmethod
    def nft_test(count: int = 5) -> Recipe:
        return Recipe(
            name="NFT Test",
            description=f"Deploy NFT and mint {count} tokens",
            steps=[
                Step(
                    name=f"NFT stress test",
                    module="nft",
                    method="stress",
                    params={
                        "miner": "miner1",
                        "contract_file": "contracts/contract-nft.clar",
                        "contract_name": "nft-test",
                        "mint_count": count
                    }
                )
            ]
        )
    
    @staticmethod
    def mempool_test(count: int = 25) -> Recipe:
        return Recipe(
            name="Mempool Test",
            description=f"Flood mempool with {count} transactions",
            steps=[
                Step(
                    name="Flood mempool",
                    module="mempool",
                    method="flood",
                    params={
                        "miner": "miner1",
                        "count": count,
                        "amount": 1
                    }
                )
            ]
        )
    
    @staticmethod
    def full_test() -> Recipe:
        return Recipe(
            name="Full Test",
            description="Complete test suite",
            steps=[
                Step(
                    name="STX transfer",
                    module="transaction",
                    method="transfer",
                    params={
                        "from_miner": "miner1",
                        "to_address": Transaction.ACCOUNTS["miner2"].address,
                        "amount": 500,
                        "memo": "full_test"
                    }
                ),
                Step(
                    name="Deploy contract",
                    module="contract",
                    method="deploy",
                    params={
                        "miner": "miner1",
                        "contract_file": "contracts/contract-counter.clar",
                        "contract_name": "full-counter"
                    }
                ),
                Step(
                    name="Deploy and mint NFTs",
                    module="nft",
                    method="deploy_and_mint",
                    params={
                        "miner": "miner2",
                        "contract_file": "contracts/contract-nft.clar",
                        "contract_name": "full-nft",
                        "recipients": [
                            Transaction.ACCOUNTS["miner1"].address,
                            Transaction.ACCOUNTS["miner3"].address
                        ]
                    }
                ),
                Step(
                    name="Mempool stress",
                    module="mempool",
                    method="flood",
                    params={
                        "miner": "miner3",
                        "count": 10,
                        "amount": 1
                    }
                )
            ]
        )
    
    @staticmethod
    def miner_control_test() -> Recipe:
        return Recipe(
            name="Miner Control Test",
            description="Test individual miner stop/resume",
            setup=False,  # Manual node control
            cleanup=False,
            steps=[
                Step(
                    name="Start miners",
                    module="node",
                    method="start_node",
                    params={}
                ),
                Step(
                    name="Initial transaction",
                    module="transaction", 
                    method="transfer",
                    params={
                        "from_miner": "miner1",
                        "to_address": Transaction.ACCOUNTS["miner2"].address,
                        "amount": 100,
                        "memo": "before_stop"
                    }
                ),
                Step(
                    name="Stop miner2",
                    module="node",
                    method="stop_miner",
                    params={"miner_id": 2}
                ),
                Step(
                    name="Transaction with miner2 stopped",
                    module="transaction",
                    method="transfer", 
                    params={
                        "from_miner": "miner1",
                        "to_address": Transaction.ACCOUNTS["miner3"].address,
                        "amount": 200,
                        "memo": "miner2_stopped"
                    }
                ),
                Step(
                    name="Resume miner2",
                    module="node",
                    method="resume_miner",
                    params={"miner_id": 2}
                ),
                Step(
                    name="Transaction after resume",
                    module="transaction",
                    method="transfer",
                    params={
                        "from_miner": "miner3",
                        "to_address": Transaction.ACCOUNTS["miner1"].address,
                        "amount": 300,
                        "memo": "after_resume"
                    }
                ),
                Step(
                    name="Stop all miners",
                    module="node",
                    method="stop_node",
                    params={}
                )
            ]
        )