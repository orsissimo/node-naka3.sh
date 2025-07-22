# Test Scripts

## Overview
Test scripts for Stacks blockchain functionality using three-miner setup.

## Scripts

**test-mempool.py** - Batched transaction stress testing
- Creates 5 blocks with progressive batch sizes (20→25→30→35→40 txs per miner)
- Submits transactions rapidly to fill blocks, then waits for mining
- Tests mempool capacity, transaction processing, and network resilience

**test-contract.py** - Contract deployment and interaction
- Deploys specified contract using blockstack-cli
- Calls read-only and public contract functions
- Verifies deployment confirmation and chain progression
```bash
python3 test-contract.py --contract contract-counter.clar --miner miner1
```

**test-nft.py** - NFT contract deployment and operations  
- Deploys SIP-009 NFT contract
- Tests minting, ownership queries, and token transfers
- Validates NFT functionality and metadata
```bash
python3 test-nft.py --contract contract-nft.clar --miner miner1
```

**test-transaction.py** - Basic token transfers
- Creates and submits STX token transfer transactions
- Tests basic network functionality and transaction confirmation

## Contracts
- `contract-counter.clar` - Simple counter with increment/reset
- `contract-nft.clar` - SIP-009 compliant NFT
- `cyberpunk2140a.clar` - Custom NFT contract

## Usage
All scripts auto-start/stop the three-miner network. Use `--help` for options.