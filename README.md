# Node Naka3

## Setup

1. Install dependencies: `npm install`
2. Start the web server: `npm start`
3. In another terminal, navigate to `naka3/playbooks/three-miners/` and run a `./three-miners.sh [command]`

## Commands

Available playbook commands:

- `start` - Initialize and start the three miners setup
- `resume` - Resume from existing state
- `stop` - Stop all miners and services
- `snapshot create` - Create a snapshot of current state
- `snapshot restore` - Restore from snapshot

**Important:** Run each command in a separate terminal to avoid interrupting processes with Ctrl+C.

## Shell Scripts

Three shell scripts are available in the main directory:

- `create-transaction.sh`
- `deploy-contract.sh`
- `monitor-chain.sh`
