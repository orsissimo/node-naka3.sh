#!/usr/bin/env bash
set -euo pipefail

CONTRACT_PATH="contracts/contract-counter.clar"
CONTRACT_NAME="contract-counter"
STACKS_NODE="${STACKS_NODE:-https://stacks-node-api.mainnet.stacks.co}"
STACKS_CLI="${STACKS_CLI:-stacks-cli}"
JQ_BIN="${JQ_BIN:-jq}"

usage() {
  cat <<USAGE
Usage: $0 <hex-private-key> [fee-rate-ustx] [nonce]
  <hex-private-key>  32-byte Stacks private key (hex string)
  [fee-rate-ustx]    optional fee rate in microstacks (default 2000)
  [nonce]            optional account nonce; fetched automatically if omitted

Environment overrides:
  STACKS_NODE  override Stacks mainnet API endpoint
  STACKS_CLI   override stacks-cli binary (default: stacks-cli)
  JQ_BIN       override jq binary (default: jq)
USAGE
}

if [ $# -lt 1 ]; then
  usage >&2
  exit 1
fi

PRIVATE_KEY="$1"
shift
FEE_RATE="${1:-2000}"
NONCE_OVERRIDE="${2:-}"

command -v "$STACKS_CLI" >/dev/null 2>&1 || {
  echo "Error: '$STACKS_CLI' not found. Install @stacks/cli (npm i -g @stacks/cli)." >&2
  exit 1
}

command -v "$JQ_BIN" >/dev/null 2>&1 || {
  echo "Error: '$JQ_BIN' not found. Install jq." >&2
  exit 1
}

if [ ! -f "$CONTRACT_PATH" ]; then
  echo "Error: contract file '$CONTRACT_PATH' not found." >&2
  exit 1
fi

KEYCHAIN_JSON="$($STACKS_CLI keychain --private-key "$PRIVATE_KEY")" || {
  echo "Error: failed to derive deployer address from private key." >&2
  exit 1
}

DEPLOYER_ADDRESS=$(echo "$KEYCHAIN_JSON" | "$JQ_BIN" -r '.address // .stacksAddress // .stxAddress // empty')

if [ -z "$DEPLOYER_ADDRESS" ]; then
  echo "Error: unable to parse deployer address from CLI output." >&2
  exit 1
fi

if [ -n "$NONCE_OVERRIDE" ]; then
  NONCE="$NONCE_OVERRIDE"
else
  ACCOUNT_JSON=$(curl -sfL "$STACKS_NODE/v2/accounts/$DEPLOYER_ADDRESS?proof=0") || {
    echo "Error: failed to fetch account info for $DEPLOYER_ADDRESS from $STACKS_NODE." >&2
    exit 1
  }
  NONCE=$(echo "$ACCOUNT_JSON" | "$JQ_BIN" -r '.nonce')
fi

if [ -z "$NONCE" ] || ! [[ "$NONCE" =~ ^[0-9]+$ ]]; then
  echo "Error: invalid nonce value '$NONCE'." >&2
  exit 1
fi

echo "Deploying $CONTRACT_NAME from $DEPLOYER_ADDRESS"
echo "  stacks node : $STACKS_NODE"
echo "  contract    : $CONTRACT_PATH"
echo "  fee rate    : $FEE_RATE µSTX"
echo "  nonce       : $NONCE"

deploy_cmd=(
  "$STACKS_CLI" contract deploy
  --contract-name "$CONTRACT_NAME"
  --nonce "$NONCE"
  --fee-rate "$FEE_RATE"
  --private-key "$PRIVATE_KEY"
  --stacks-node "$STACKS_NODE"
  "$CONTRACT_PATH"
  --clarity-version 2
  --send
)

DEPLOY_OUTPUT="$(${deploy_cmd[@]})"

TXID=$(echo "$DEPLOY_OUTPUT" | "$JQ_BIN" -r '.transactionId // .txid // empty')

if [ -n "$TXID" ] && [[ "$TXID" != null ]]; then
  echo "Broadcasted transaction: $TXID"
else
  echo "$DEPLOY_OUTPUT"
fi
