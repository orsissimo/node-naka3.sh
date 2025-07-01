# Stacks Blockchain Playground

Web interface and CLI scripts for testing Stacks blockchain operations with multi-miner support.

**Prerequisites:** Requires running Stacks miners. See that [README](../README.md) for setup instructions and playbook usage.

## Usage

### Web Interface

```bash
npm start
# Open http://localhost:3000
```

### CLI Scripts

```bash
# Default (Miner 1)
./create-transaction.sh
./monitor-chain.sh

# Specific miner (miner1/miner2/miner3)
./create-transaction.sh miner2
./monitor-chain.sh miner3
```

## Available Scripts

- **create-transaction.sh** - Create and submit STX token transfers
- **monitor-chain.sh** - Monitor blockchain status and progression
- **server.js** - Web server for browser-based script execution

### Funded Accounts (Used by Scripts)

Each miner uses a different funded account for transactions:

| **Miner** | **STX Address**                           | **Private Key**                                                    | **Balance** |
| --------- | ----------------------------------------- | ------------------------------------------------------------------ | ----------- |
| miner1    | STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6  | cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01 | ~10,000 STX |
| miner2    | ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y | 21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601 | ~10,000 STX |
| miner3    | ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0 | 7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01 | ~1,000 STX  |

**Recipient Account (for transfers):**

- STX Address: ST3KCNDSWZSFZCC6BE4VA9AXWXC9KEB16FBTRK36T

### API Endpoints

- Miner 1: `http://localhost:20443`
- Miner 2: `http://localhost:30443`
- Miner 3: `http://localhost:40443`
