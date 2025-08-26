# Developer Must-Know

## Autocompletion Available

### Miner Management
```python
miners.snapshot_restore_auto()
miners.snapshot_restore_manual()
miners.start_auto()
miners.start_manual()
miners.start_from_scratch_auto()
miners.start_from_scratch_manual()
miner_manager.stop_miner(Miner.MINER2)
miner_manager.resume_miner(Miner.MINER3)
```

### Enums
```python
Miner.MINER1
Miner.MINER2
Miner.MINER3
TxStatus.SUCCESS
TxStatus.PENDING
```

## No Autocompletion

### Contract Function Names
**Counter Contract:**
```python
api.call_read_only_function(account.address, "mycontract", "get-counter", ...)
api.call_read_only_function(account.address, "mycontract", "get-last-caller", ...)
cli.call_contract(..., "mycontract", "increment", [])
cli.call_contract(..., "mycontract", "reset", [])
```

**NFT Contract:**
```python
api.call_read_only_function(account.address, "cyberpunk2140a", "get-last-token-id", ...)
api.call_read_only_function(account.address, "cyberpunk2140a", "get-mint-price", ...)
cli.call_contract(..., "cyberpunk2140a", "set-token-uri", ...)
cli.call_contract(..., "cyberpunk2140a", "mint", [])
```

### Contract Names
```python
"mycontract"        # Counter contract
"cyberpunk2140a"    # NFT contract
```


### File Paths
```python
"contracts/contract-counter.clar"
"contracts/cyberpunk2140a.clar"
```