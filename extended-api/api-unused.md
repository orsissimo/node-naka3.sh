# Unused Stacks Blockchain API Endpoints

This document lists all the API endpoints from the Stacks Blockchain API that are **NOT currently implemented** in the index.html explorer. These endpoints are available for future implementation to extend the explorer's functionality.

## Summary

- **Total unused endpoints:** 53
- **Total available endpoints:** 83 (excluding deprecated)
- **Currently implemented:** 30 (36% coverage)
- **Remaining to implement:** 53 (64% uncovered)

---

### **Accounts (1 unused)**

- `GET /extended/v2/addresses/{principal}/balances/ft/{token}` - Get a specific principal FT balance

### **Blocks (3 unused)**

- `GET /extended/v2/blocks/{height_or_hash}/signer-signatures` - Get signer signatures for a block
- `GET /extended/v2/block-tenures/{tenure_height}/blocks` - Get blocks by tenure
- `GET /extended/v2/blocks/{height_or_hash}/transactions` - Get transactions by block

### **Burn Blocks (2 unused)**

- `GET /extended/v2/burn-blocks/{height_or_hash}` - Get a single burn block
- `GET /extended/v2/burn-blocks/{height_or_hash}/blocks` - Get blocks confirmed by a specific burn block

### **Faucets (3 unused)**

- `POST /extended/v1/faucets/btc` - Add regtest BTC tokens to an address
- `GET /extended/v1/faucets/btc/{address}` - Get BTC balance for an address
- `POST /extended/v1/faucets/stx` - Get STX testnet tokens

### **Info (1 unused)**

- `GET /extended/v1/info/network_block_time/{network}` - Get a specific network's target block time

### **Names (10 unused)**

- `GET /v1/addresses/{blockchain}/{address}` - Get Names Owned by an Address
- `GET /v1/names/` - Get All Names
- `GET /v1/names/{name}` - Get Name Details
- `GET /v1/names/{name}/subdomains` - Get Name Subdomains
- `GET /v1/names/{name}/zonefile` - Get Zone File
- `GET /v1/names/{name}/zonefile/{zoneFileHash}` - Get Historical Zone File
- `GET /v1/namespaces/` - Get All Namespaces
- `GET /v1/namespaces/{tld}/names` - Get Names in a Namespace
- `GET /v2/prices/names/{name}` - Get Name Price
- `GET /v2/prices/namespaces/{tld}` - Get Namespace Price

### **Proof of Transfer (5 unused)**

- `GET /extended/v2/pox/cycles` - Get PoX cycles
- `GET /extended/v2/pox/cycles/{cycle_number}` - Get a specific PoX cycle
- `GET /extended/v2/pox/cycles/{cycle_number}/signers` - Get signers in a PoX cycle
- `GET /extended/v2/pox/cycles/{cycle_number}/signers/{signer_key}` - Get a specific signer in a PoX cycle
- `GET /extended/v2/pox/cycles/{cycle_number}/signers/{signer_key}/stackers` - Get stackers for a specific signer in a PoX cycle

### **Smart Contracts (2 unused)**

- `GET /extended/v1/contract/by_trait` - Get contracts by trait
- `GET /extended/v2/smart-contracts/status` - Get status for multiple contracts

### **Stacking (4 unused)**

- `GET /extended/v1/{pox}/events` - Get latest PoX events
- `GET /extended/v1/{pox}/tx/{tx_id}` - Get PoX events for a transaction
- `GET /extended/v1/{pox}/stacker/{principal}` - Get events for a stacking address
- `GET /extended/v1/{pox}/{pool_principal}/delegations` - Get stacking pool members

### **Stacking Rewards (5 unused)**

- `GET /extended/v1/burnchain/reward_slot_holders` - Get recent reward slot holders
- `GET /extended/v1/burnchain/reward_slot_holders/{address}` - Get reward slot holders for a specific address
- `GET /extended/v1/burnchain/rewards` - Get recent burnchain reward recipients
- `GET /extended/v1/burnchain/rewards/{address}` - Get burnchain rewards for a specific recipient
- `GET /extended/v1/burnchain/rewards/{address}/total` - Get total burnchain rewards for a recipient

### **Transactions (4 unused)**

- `GET /extended/v1/tx/multiple` - Get details for a list of transactions
- `GET /extended/v1/tx/{tx_id}/raw` - Get raw transaction data
- `GET /extended/v1/tx/events` - Get transaction events (requires address or tx_id parameter)
- `GET /extended/v1/tx/mempool` - Get mempool transactions
