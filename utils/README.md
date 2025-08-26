# Utils Library

This directory contains the utility modules that power the Stacks blockchain test framework. Each file provides specific functionality for blockchain operations, API interactions, and test infrastructure.

## Files Overview

```
utils/
├── config.py              # Configuration, accounts, and type definitions
├── helpers.py             # Essential helper functions for common operations
├── stacks_core_api.py     # Low-level Stacks Core API wrapper
├── blockstack_cli.py      # Blockstack CLI wrapper for transactions
├── miners.py              # Miner management and control
└── logger.py              # Colored logging and output formatting
```

---

## config.py

**Purpose**: Centralized configuration, account management, and type-safe data structures.

### Account Management

```python
from utils.config import AccountManager, Miner

# Get specific miner account
account = AccountManager.get(Miner.MINER1)
print(f"Address: {account.address}")
print(f"API URL: {account.api_url}")  # http://localhost:20443
print(f"Private Key: {account.private_key}")
```

### Available Accounts

- **MINER1**: `STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6` (port 20443)
- **MINER2**: `ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y` (port 30443)  
- **MINER3**: `ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0` (port 40443)

### Type-Safe Data Structures

```python
from utils.config import TransferInfo, DeploymentInfo, TransactionStatus

# Transfer tracking
transfer = TransferInfo(
    miner=Miner.MINER1,
    to_address="ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM",
    amount=50000,
    memo="Test transfer",
    nonce=10,
    status=TransactionStatus.PENDING
)
```

---

## helpers.py

**Purpose**: Essential convenience functions for common operations.

### Core Functions

```python
from utils.helpers import get_account_info_typed, get_block_height, wait_for_confirmation

# Account operations (require API instance) - with type safety and autocompletion
account_info = get_account_info_typed(api, account.address)  # Typed account info
nonce = account_info.nonce          # Current nonce as int (with autocompletion)
balance = account_info.balance      # Balance in µSTX as int (with autocompletion)
height = get_block_height(api)      # Current block height as int

# Confirmation waiting
confirmed = wait_for_confirmation(
    api, account.address, initial_nonce, initial_height, timeout=120
)  # Returns True/False
```

### Typed Account Info

```python
from utils.helpers import get_account_info_typed

# Get typed account info with autocompletion
account_info = get_account_info_typed(api, account.address)
print(f"Balance: {account_info.balance}")     # IDE autocompletion works!
print(f"Nonce: {account_info.nonce}")         # IDE autocompletion works!
print(f"Address: {account_info.address}")     # IDE autocompletion works!
```

### CLI Command Processing

```python
from utils.helpers import prepare_cli_binary, submit_cli_command

# Prepare CLI command for submission
tx_binary = prepare_cli_binary(["blockstack-cli", "publish", ...])

# Execute CLI command and submit to blockchain
txid = submit_cli_command(api, ["blockstack-cli", "publish", ...])
```

### Safe API Calls

```python
from utils.helpers import safe_api_call

result = safe_api_call(api.get_account_info, account.address)
if result.success:
    account_data = result.data
else:
    print(f"Error: {result.error_message}")
```

### Transaction Status

```python
from utils.helpers import get_tx_status_typed

status = get_tx_status_typed(api, txid)
if status == TxStatus.SUCCESS:
    print("Transaction succeeded")
```

---

## stacks_core_api.py

**Purpose**: Low-level wrapper for the Stacks Core RPC API.

### Basic Usage

```python
from utils.stacks_core_api import StacksCoreAPIWrapper
from utils.config import AccountManager, Miner

# Create API instance (no helper function)
account = AccountManager.get(Miner.MINER1)
api = StacksCoreAPIWrapper(base_url=account.api_url)

# Node information
info = api.get_info()
print(f"Stacks tip height: {info['stacks_tip_height']}")

# Account information
account_data = api.get_account_info(account.address)
print(f"Balance: {account_data['balance']}")  # Hex string
print(f"Nonce: {account_data['nonce']}")      # Integer

# Submit raw transaction
txid = api.post_raw_transaction(transaction_binary)
```

---

## blockstack_cli.py

**Purpose**: Python wrapper for the blockstack-cli command-line tool.

### Basic Usage

```python
from utils.blockstack_cli import BlockstackCLIWrapper

# Create CLI instance (no helper function)
cli = BlockstackCLIWrapper()
```

### Contract Operations

```python
# Deploy contract - returns transaction hex
tx_hex = cli.publish_contract(
    publisher_sk=account.private_key,
    fee_rate=5000,
    nonce=current_nonce,
    contract_name="my-contract",
    file_name="/path/to/contract.clar"
)

# Call contract function - returns transaction hex
tx_hex = cli.call_contract(
    caller_sk=account.private_key,
    fee_rate=5000,
    nonce=current_nonce,
    contract_address=account.address,
    contract_name="my-contract",
    function_name="increment",
    arguments=[]
)

# STX transfer - returns transaction hex
tx_hex = cli.token_transfer(
    sender_sk=account.private_key,
    fee_rate=180,
    nonce=current_nonce,
    recipient_address=recipient.address,
    amount=50000,
    memo="Test transfer"
)
```

**All CLI methods return transaction hex strings that must be submitted via `api.post_raw_transaction()`**

---

## miners.py

**Purpose**: Manages blockchain miners for testing.

### Basic Operations

```python
from utils.miners import MinerManager
from utils.config import MiningMode

miners = MinerManager()

# Start miners from scratch in specified mode
if miners.start(MiningMode.AUTO):
    print("Miners started successfully")

# Convenience methods
if miners.start_auto():    # Uses MiningMode.AUTO
    print("Auto mining started")

if miners.start_manual():  # Uses MiningMode.MANUAL
    print("Manual mining started")

# Wait for miners to be ready
if miners.wait_for_miners_ready(timeout=60):
    print("All miners are ready")

# Snapshot restore
if miners.snapshot_restore_auto():
    print("Snapshot restored")

# Cleanup
miners.stop()
miners.cleanup()
```

### Mining Control

```python
# Manual mining operations
miners.switch_to_manual_mining()
miners.mine_block()  # Mine single block
miners.switch_to_auto_mining()

# Individual miner control
miners.stop_miner(3)
miners.resume_miner(3)

# Snapshot management
miners.create_snapshot()
miners.restore_snapshot()
```

---

## logger.py

**Purpose**: Provides colored terminal output and structured logging.

### Colors Utility

```python
from utils.logger import Colors

# Basic formatting (includes symbols automatically)
print(Colors.format_success("Operation completed"))  # Green with ✓
print(Colors.format_error("Something failed"))       # Red with ✗
print(Colors.format_header("Test Section"))          # Blue header
print(Colors.format_info("Information"))             # White text
print(Colors.format_dim("Dimmed details"))           # Gray text
print(Colors.format_stacks("Stacks message"))        # Orange
```

### Structured Logging

```python
from utils.logger import logger

logger.info("General information")
logger.error("Error occurred")
logger.warning("Warning message")
```

---

## Common Usage Patterns

### Standard Test Setup

```python
from utils.helpers import get_account_info_typed, wait_for_confirmation
from utils.config import AccountManager, Miner, MiningMode
from utils.miners import MinerManager
from utils.logger import Colors
from utils.blockstack_cli import BlockstackCLIWrapper
from utils.stacks_core_api import StacksCoreAPIWrapper

def test_function():
    # Setup
    miners = MinerManager()
    account = AccountManager.get(Miner.MINER1)
    api = StacksCoreAPIWrapper(base_url=account.api_url)
    cli = BlockstackCLIWrapper()
    
    try:
        # Start miners
        if not miners.start(MiningMode.AUTO):
            raise RuntimeError("Failed to start miners")
        
        # Your test logic here with typed access
        account_info = get_account_info_typed(api, account.address)
        nonce = account_info.nonce
        balance = account_info.balance
        
        return True
        
    except Exception as e:
        print(f"{Colors.format_error('TEST FAILED')}: {Colors.format_error(str(e))}")
        return False
        
    finally:
        miners.stop()
        miners.cleanup()
```

### Transaction Pattern

```python
# Get current state (with autocompletion)
account_info = get_account_info_typed(api, account.address)
initial_nonce = account_info.nonce
initial_height = get_block_height(api)

# Create and submit transaction
tx_hex = cli.some_operation(...)  # Any CLI operation returns hex
txid = api.post_raw_transaction(bytes.fromhex(tx_hex))

# Wait for confirmation
if not wait_for_confirmation(api, account.address, initial_nonce, initial_height, timeout=120):
    raise RuntimeError("Transaction confirmation timeout")
```

### Contract Deployment

```python
# Deploy contract
tx_hex = cli.publish_contract(
    account.private_key, 5000, nonce, "contract-name", "contract.clar"
)
deploy_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))

# Call contract function
tx_hex = cli.call_contract(
    account.private_key, 5000, nonce, account.address, 
    "contract-name", "function-name", []
)
call_txid = api.post_raw_transaction(bytes.fromhex(tx_hex))

# Read contract state
result = api.call_read_only_function(
    account.address, "contract-name", "get-state", account.address, []
)
```

## Key Simplifications Made

- **Removed wrapper functions**: No more `get_api()`, `get_cli()`, `submit_tx_hex()`, `get_block_height()`
- **Direct instantiation**: Create `StacksCoreAPIWrapper` and `BlockstackCLIWrapper` directly
- **Simplified miners**: Single `start()` method instead of multiple variations
- **Direct API access**: Access `api.get_account_info()` directly instead of typed wrappers
- **Clear transaction flow**: `cli.operation() → api.post_raw_transaction(bytes.fromhex(tx_hex))`