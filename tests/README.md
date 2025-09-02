# Test Suite (Must be updated for the new, updated, structure)

This directory contains the test suite for the Stacks blockchain project. Tests are written in Python and focus on contract deployment, interaction, and blockchain functionality.

## Getting Started

### Prerequisites

- Python 3.8+
- to add...

## Writing Tests

### Basic Test Template

All tests should follow this structure:

```python
#!/usr/bin/env python3

import os
import sys
import json

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.helpers import get_account_info_typed, wait_for_tx_confirmation
from utils.config import AccountManager, Miner, MiningMode
from utils.miners import MinerManager
from utils.logger import Colors
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.stacks_core_api import StacksCoreAPIWrapper

def main():
    """Execute your test logic"""
    print(f"{Colors.format_dim('=' * 60)}")
    print(f"{Colors.format_header('YOUR TEST NAME')}")
    print(f"{Colors.format_dim('=' * 60)}")
    
    # Setup
    miners = MinerManager()
    account = AccountManager.get(Miner.MINER1)
    api = StacksCoreAPIWrapper(base_url=account.api_url)
    cli = BlockstackCLIWrapper()
    
    try:
        # Start miners
        print(f"\n{Colors.format_stacks('Starting miners...')}")
        if not miners.start(MiningMode.AUTO):
            raise RuntimeError("Failed to start miners")
        
        # Your test logic here with typed functions
        account_info = get_account_info_typed(api, account.address)
        initial_nonce = account_info.nonce
        initial_height = get_block_height(api)
        
        return True
        
    except Exception as e:
        print(f"\n{Colors.format_error('TEST FAILED')}: {Colors.format_error(str(e))}")
        return False
        
    finally:
        # Cleanup
        print(f"\n{Colors.format_header('Cleaning up...')}")
        miners.stop()
        miners.cleanup()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
```

### Essential Components

#### 1. Environment Setup

```python
# Add utils to path for importing helper modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import required modules
from utils.helpers import get_account_info_typed, get_block_height, wait_for_tx_confirmation
from utils.config import AccountManager, Miner, MiningMode
from utils.miners import MinerManager
from utils.logger import Colors
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.stacks_core_api import StacksCoreAPIWrapper
```

#### 2. Test Initialization

```python
# Initialize core components
miners = MinerManager()           # Manages blockchain miners
account = AccountManager.get(Miner.MINER1)  # Test account
api = StacksCoreAPIWrapper(base_url=account.api_url)  # API wrapper
cli = BlockstackCLIWrapper()     # CLI wrapper for transactions
```

#### 3. Miner Management

```python
# Start miners in auto mode
if not miners.start(MiningMode.AUTO):
    raise RuntimeError("Failed to start miners")

# Always cleanup in finally block
finally:
    miners.stop()
    miners.cleanup()
```

### Contract Deployment

To deploy a contract:

```python
# Get initial state (with autocompletion)
account_info = get_account_info_typed(api, account.address)
initial_nonce = account_info.nonce
initial_height = get_block_height(api)

# Deploy contract
tx_hex = cli.publish_contract(
    account.private_key,    # Private key for signing
    5000,                  # Fee in µSTX
    initial_nonce,         # Transaction nonce
    "contract-name",       # Contract identifier
    "path/to/contract.clar" # Contract file path
)

# Submit and wait for confirmation
txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
if not wait_for_tx_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
    raise RuntimeError("Contract deployment confirmation timeout")
```

### Contract Function Calls

#### Read-Only Functions

```python
result = api.call_read_only_function(
    account.address,    # Caller address
    "contract-name",    # Contract identifier
    "function-name",    # Function to call
    account.address,    # Sender address
    []                  # Function arguments (list)
)
print(f"Response: {json.dumps(result, indent=2)}")
```

#### Write Functions

```python
# Get current state
account_info = get_account_info_typed(api, account.address)
initial_nonce = account_info.nonce
initial_height = api.get_info()["stacks_tip_height"]

# Call contract function
tx_hex = cli.call_contract(
    account.private_key,  # Private key
    5000,                # Fee in µSTX
    initial_nonce,       # Nonce
    account.address,     # Contract owner
    "contract-name",     # Contract identifier
    "function-name",     # Function to call
    ["arg1", "arg2"]     # Function arguments
)

# Submit and confirm
txid = api.post_raw_transaction(bytes.fromhex(tx_hex))
if not wait_for_tx_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
    raise RuntimeError("Contract call confirmation timeout")
```

### Testing Best Practices

1. **Always use proper cleanup**: Use try/finally blocks to ensure miners are stopped and cleaned up
2. **Wait for confirmations**: Always wait for transaction confirmations before proceeding
3. **Handle errors gracefully**: Catch exceptions and provide meaningful error messages
4. **Use colored output**: Use the Colors utility for consistent, readable output
5. **Test incrementally**: Break complex tests into clear, numbered steps
6. **Verify state changes**: Read contract state before and after operations to verify changes
7. **No hardcoded symbols**: Never use hardcoded "✓" or "✗" symbols in tests - the utils already provide proper formatting through Colors utility functions

### Available Utilities

For detailed documentation on all utility functions, data structures, and advanced patterns, see the **[Utils README](../utils/README.md)**.

#### Quick Reference

**Essential Functions (`utils.helpers`)**
- `get_account_info_typed(api, address)` - Get account info with IDE autocompletion (use .nonce and .balance)
- `get_block_height(api)` - Current block height with autocompletion
- `wait_for_tx_confirmation(api, address, nonce, height, timeout)` - Wait for confirmation

**Direct API/CLI Usage**
- `account = AccountManager.get(Miner.MINER1)` - Get account config
- `api = StacksCoreAPIWrapper(base_url=account.api_url)` - Create API instance
- `cli = BlockstackCLIWrapper()` - Create CLI instance
- `api.post_raw_transaction(bytes.fromhex(tx_hex))` - Submit transaction
- `get_block_height(api)` - Current block height with autocompletion

**Miner Management**
- `miners.start(MiningMode.AUTO)` - Start miners from scratch
- `miners.snapshot_restore_auto()` - Alternative: restore from snapshot

**Configuration (`utils.config`)**
- `AccountManager.get(miner)` - Get account info
- `Miner.MINER1/MINER2/MINER3` - Type-safe miner access
- `TransferInfo`, `DeploymentInfo` - Type-safe data structures

**Miner Management (`utils.miners`)**
- `MinerManager()` - Control blockchain miners
- `snapshot_restore_auto()` - Start with clean state
- `stop()`, `cleanup()` - Proper teardown

**Logging (`utils.logger`)**  
- `Colors.format_*()` functions - Consistent colored output
- Never use hardcoded "✓" or "✗" symbols

### Example Tests

#### Simple Contract Test

See `example-counter-deploy-rw.py` for a complete example of:
- Contract deployment
- Read-only function calls
- Contract state modification
- State verification

#### NFT Contract Test

See `example-nft-deploy-rw.py` for an advanced example of:
- Complex contract deployment
- Multiple contract function calls
- NFT minting and metadata handling

### Running Tests

Execute individual tests:

```bash
cd tests/
python3 example-counter-deploy-rw.py
python3 example-nft-deploy-rw.py
```

### Known Issues

Check `improvements.txt` for current known issues and planned improvements.

### Debugging

- All transactions include detailed logging with transaction IDs
- Failed operations include error details and stack traces
- Miners automatically clean up on test completion or failure
- Use the colored output to quickly identify success/failure states