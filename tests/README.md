# Stacks Modular Test Framework

Smart, efficient, minimal testing framework with reusable modules.

## Quick Start

```python
from utils import Runner, Recipes

runner = Runner()
result = runner.run(Recipes.tx_test())  # Basic transaction test
```

## Modules

- **Transaction**: `transfer()`, `batch()`, `stress()`
- **Contract**: `deploy()`, `read()`, `call()`, `deploy_and_test()`
- **NFT**: `mint()`, `transfer()`, `burn()`, `deploy_and_mint()`
- **Mempool**: `flood()`, `mixed_stress()`, `info()`
- **NodeManager**: `start_node()`, `stop_miner()`, `resume_miner()`

## Available Tests

```bash
./example_usage.py                    # Demo all modules
./test-modular-transaction.py         # Transaction tests
./test-modular-comprehensive.py       # Full test suite
./test-miner-control.py test          # Miner control test
```

## Recipe System

```python
recipe = Recipe("Test", "Description", [
    Step("Transfer", "transaction", "transfer", {...}),
    Step("Deploy", "contract", "deploy", {...})
])
result = runner.run(recipe)
```

## Predefined Recipes

- `Recipes.tx_test()` - Basic STX transfer
- `Recipes.contract_test()` - Contract deployment
- `Recipes.nft_test()` - NFT operations
- `Recipes.mempool_test()` - Mempool stress
- `Recipes.full_test()` - Complete test suite
- `Recipes.miner_control_test()` - Individual miner control

Efficient, working, modular.