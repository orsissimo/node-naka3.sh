### Accounts (11)

- ~~`GET /extended/v1/address/{principal}/stx` - Get account STX balance `(Deprecated)`~~
- ~~`GET /extended/v1/address/{principal}/balances` - Get account balances `(Deprecated)`~~
- ~~`GET /extended/v1/address/{principal}/transactions` - Get account transactions `(Deprecated)`~~
- ~~`GET /extended/v1/address/{principal}/{tx_id}/with_transfers` - Get account transaction information for a specific transaction `(Deprecated)`~~
- ~~`GET /extended/v1/address/{principal}/transactions_with_transfers` - Get account transactions with STX transfers `(Deprecated)`~~
- `GET /extended/v1/address/{principal}/assets` - Get account assets
- `GET /extended/v1/address/{principal}/stx_inbound` - Get inbound STX transfers
- `GET /extended/v1/address/{principal}/nonces` - Get the latest nonce used by an account
- `GET /extended/v2/addresses/{principal}/balances/stx` - Get principal STX balance
- `GET /extended/v2/addresses/{principal}/balances/ft` - Get principal FT balances
- `GET /extended/v2/addresses/{principal}/balances/ft/{token}` - Get a specific principal FT balance

### Blocks (10)

- ~~`GET /extended/v1/block/` - Get recent blocks `(Deprecated)`~~
- ~~`GET /extended/v1/block/by_height/{height}` - Get block by height `(Deprecated)`~~
- ~~`GET /extended/v1/block/by_burn_block_height/{burn_block_height}` - Get block by burnchain height `(Deprecated)`~~
- ~~`GET /extended/v1/block/{hash}` - Get block by hash `(Deprecated)`~~
- ~~`GET /extended/v1/block/by_burn_block_hash/{burn_block_hash}` - Get block by burnchain block hash `(Deprecated)`~~
- `GET /extended/v2/blocks/` - Get blocks
- `GET /extended/v2/blocks/average-times` - Get average block times
- `GET /extended/v2/blocks/{height_or_hash}` - Get a single block
- `GET /extended/v2/blocks/{height_or_hash}/signer-signatures` - Get signer signatures for a block
- `GET /extended/v2/block-tenures/{tenure_height}/blocks` - Get blocks by tenure

### Burn Blocks (3)

- `GET /extended/v2/burn-blocks/` - Get burn blocks
- `GET /extended/v2/burn-blocks/{height_or_hash}` - Get a single burn block
- `GET /extended/v2/burn-blocks/{height_or_hash}/blocks` - Get blocks confirmed by a specific burn block

### Faucets (3)

- `POST /extended/v1/faucets/btc` - Add regtest BTC tokens to an address
- `GET /extended/v1/faucets/btc/{address}` - Get BTC balance for an address
- `POST /extended/v1/faucets/stx` - Get STX testnet tokens

### ~~Fees (1)~~

- ~~`POST /extended/v1/fee_rate/` - Fetch fee rate for a transaction `(Deprecated)`~~

### Info (7)

- `GET /extended` - Get API status
- `GET /extended/v1/stx_supply/` - Get total and unlocked STX supply
- ~~`GET /extended/v1/stx_supply/total/plain` - Get total STX supply (plain text) `(Deprecated)`~~
- ~~`GET /extended/v1/stx_supply/circulating/plain` - Get circulating STX supply (plain text) `(Deprecated)`~~
- ~~`GET /extended/v1/stx_supply/legacy_format` - Get STX supply (legacy format) `(Deprecated)`~~
- `GET /extended/v1/info/network_block_times` - Get the network target block times
- `GET /extended/v1/info/network_block_time/{network}` - Get a specific network's target block time

### Mempool (1)

- `GET /extended/v2/mempool/fees` - Get mempool transaction fee priorities

### Microblocks (3)

- `GET /extended/v1/microblock/` - Get recent microblocks
- `GET /extended/v1/microblock/{hash}` - Get a single microblock by hash
- `GET /extended/v1/microblock/unanchored/txs` - Get transactions from unanchored microblocks

### Names (10)

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

### Non-Fungible Tokens (3)

- `GET /extended/v1/tokens/nft/holdings` - Get NFT holdings for a principal
- `GET /extended/v1/tokens/nft/history` - Get history for an NFT
- `GET /extended/v1/tokens/nft/mints` - Get mint events for an NFT collection

### Fungible Tokens (1)

- `GET /extended/v1/tokens/ft/{token}/holders` - Get all holders of a fungible token

### Proof of Transfer (5)

- `GET /extended/v2/pox/cycles` - Get PoX cycles
- `GET /extended/v2/pox/cycles/{cycle_number}` - Get a specific PoX cycle
- `GET /extended/v2/pox/cycles/{cycle_number}/signers` - Get signers in a PoX cycle
- `GET /extended/v2/pox/cycles/{cycle_number}/signers/{signer_key}` - Get a specific signer in a PoX cycle
- `GET /extended/v2/pox/cycles/{cycle_number}/signers/{signer_key}/stackers` - Get stackers for a specific signer in a PoX cycle

### Search (1)

- `GET /extended/v1/search/{id}` - Search for a block, transaction, contract, or account by hash/ID

### Smart Contracts (4)

- `GET /extended/v1/contract/by_trait` - Get contracts by trait
- `GET /extended/v1/contract/{contract_id}` - Get contract info
- `GET /extended/v1/contract/{contract_id}/events` - Get contract events
- `GET /extended/v2/smart-contracts/status` - Get status for multiple contracts

### Stacking (4)

- `GET /extended/v1/{pox}/events` - Get latest PoX events
- `GET /extended/v1/{pox}/tx/{tx_id}` - Get PoX events for a transaction
- `GET /extended/v1/{pox}/stacker/{principal}` - Get events for a stacking address
- `GET /extended/v1/{pox}/{pool_principal}/delegations` - Get stacking pool members

### Stacking Rewards (5)

- `GET /extended/v1/burnchain/reward_slot_holders` - Get recent reward slot holders
- `GET /extended/v1/burnchain/reward_slot_holders/{address}` - Get reward slot holders for a specific address
- `GET /extended/v1/burnchain/rewards` - Get recent burnchain reward recipients
- `GET /extended/v1/burnchain/rewards/{address}` - Get burnchain rewards for a specific recipient
- `GET /extended/v1/burnchain/rewards/{address}/total` - Get total burnchain rewards for a recipient

### Transactions (13)

- `GET /extended/v1/tx/` - Get recent transactions
- `GET /extended/v1/tx/multiple` - Get details for a list of transactions
- `GET /extended/v1/tx/mempool` - Get mempool transactions
- `GET /extended/v1/tx/mempool/stats` - Get statistics for mempool transactions
- `GET /extended/v1/tx/events` - Get transaction events
- `GET /extended/v1/tx/{tx_id}` - Get a single transaction by ID
- `GET /extended/v1/tx/{tx_id}/raw` - Get raw transaction data
- ~~`GET /extended/v1/tx/block/{block_hash}` - Get transactions by block hash `(Deprecated)`~~
- ~~`GET /extended/v1/tx/block_height/{height}` - Get transactions by block height `(Deprecated)`~~
- `GET /extended/v1/address/{principal}/mempool` - Get mempool transactions for an address
- `GET /extended/v2/blocks/{height_or_hash}/transactions` - Get transactions by block
- `GET /extended/v2/addresses/{address}/transactions` - Get address transactions
- `GET /extended/v2/addresses/{address}/transactions/{tx_id}/events` - Get events for an address transaction

---

### **Base URLs**

- **Mainnet** : `https://api.mainnet.hiro.so`
- **Testnet** : `https://api.testnet.hiro.so`
- **Local** : `http://localhost:3999`

### Examples

```
# Get account balance
curl "https://api.mainnet.hiro.so/extended/v1/address/SP31DA6FTSJX2WGTZ69SFY11BH51NZMB0ZW97B5P0/balances"

# Get recent blocks
curl "https://api.mainnet.hiro.so/extended/v1/block?limit=10"

# Call read-only function
curl -X POST "https://api.mainnet.hiro.so/extended/v1/contract/SP000000000000000000002Q6VF78/pox/call-read/get-pox-info" \
  -H "Content-Type: application/json" \
  -d '{"sender": "SP000000000000000000002Q6VF78", "arguments": []}'
```
