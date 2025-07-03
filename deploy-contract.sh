MINER=${1:-miner1} && \
case "$MINER" in
    miner1) MINER_PORT=20443 ;;
    miner2) MINER_PORT=30443 ;;
    miner3) MINER_PORT=40443 ;;
    *) echo "Error: Invalid miner '$MINER'. Use miner1, miner2, or miner3" && exit 1 ;;
esac && \
API_URL="http://localhost:$MINER_PORT" && \
echo "Using $MINER on port: $MINER_PORT" && \
mkdir -p ./tmp ./logs && \
TIMESTAMP=$(date '+%Y%m%d_%H%M%S') && \
LOGFILE="./logs/contract_${TIMESTAMP}_${MINER}.log" && \
echo "=== CONTRACT DEPLOYMENT LOG START - $(date) ===" > "$LOGFILE" && \
echo "Miner: $MINER" >> "$LOGFILE" && \
echo "API URL: $API_URL" >> "$LOGFILE" && \
echo "Deploying contract..." && \
# Use funded accounts based on miner
case "$MINER" in
    miner1) PUBLISHER_ADDR="STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6"; PUBLISHER_KEY="cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01" ;;
    miner2) PUBLISHER_ADDR="ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y"; PUBLISHER_KEY="21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601" ;;
    miner3) PUBLISHER_ADDR="ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0"; PUBLISHER_KEY="7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01" ;;
esac && \
echo "Publisher: $PUBLISHER_ADDR" >> "$LOGFILE" && \
echo "Getting initial nonce..." >> "$LOGFILE" && \
NONCE_RESPONSE=$(curl -s $API_URL/v2/accounts/$PUBLISHER_ADDR | tee -a "$LOGFILE") && \
NONCE=$(echo "$NONCE_RESPONSE" | jq -r '.nonce') && \
echo "Nonce: $NONCE" && \
echo "Getting publisher balance..." >> "$LOGFILE" && \
BALANCE_BEFORE_RESPONSE=$(curl -s $API_URL/v2/accounts/$PUBLISHER_ADDR | tee -a "$LOGFILE") && \
BALANCE_BEFORE=$(echo "$BALANCE_BEFORE_RESPONSE" | jq -r '.balance' | xargs printf '%d\n') && \
printf "Publisher balance before: \033[37m$BALANCE_BEFORE\033[0m\n" && \
echo "Creating contract file..." >> "$LOGFILE" && \
echo '(define-public (say-hello) (begin (print "Hello!") (ok true)))' > ./tmp/contract.clar && \
echo "Contract content:" >> "$LOGFILE" && \
cat ./tmp/contract.clar >> "$LOGFILE" && \
echo "Creating blockstack-cli command..." >> "$LOGFILE" && \
echo "blockstack-cli --testnet publish $PUBLISHER_KEY 200 $NONCE mycontract$NONCE ./tmp/contract.clar" >> "$LOGFILE" && \
blockstack-cli --testnet publish $PUBLISHER_KEY 200 $NONCE mycontract$NONCE ./tmp/contract.clar | xxd -r -p > ./tmp/contract-tx-auto.bin && \
echo "Submitting contract transaction..." >> "$LOGFILE" && \
TXID=$(curl -s -X POST -H "Content-Type: application/octet-stream" --data-binary @./tmp/contract-tx-auto.bin $API_URL/v2/transactions | tee -a "$LOGFILE") && \
printf "\033[32mTransaction ID: $TXID\033[0m\n" && \
printf "\033[32mContract name: mycontract$NONCE\033[0m\n" && \
echo "Polling for contract deployment confirmation..." >> "$LOGFILE" && \
CLEAN_TXID=$(echo "$TXID" | tr -d '"') && \
printf "Waiting for transaction \033[36m$CLEAN_TXID\033[0m to be processed...\n" && \
POLL_COUNT=0 && \
MAX_POLLS=300 && \
INITIAL_NONCE=$NONCE && \
INITIAL_BLOCK_RESPONSE=$(curl -s $API_URL/v2/info) && \
INITIAL_BLOCK_HEIGHT=$(echo "$INITIAL_BLOCK_RESPONSE" | jq -r '.stacks_tip_height') && \
echo "Initial block height: $INITIAL_BLOCK_HEIGHT" >> "$LOGFILE" && \
while [ $POLL_COUNT -lt $MAX_POLLS ]; do \
  CURRENT_NONCE_RESPONSE=$(curl -s $API_URL/v2/accounts/$PUBLISHER_ADDR) && \
  CURRENT_NONCE=$(echo "$CURRENT_NONCE_RESPONSE" | jq -r '.nonce') && \
  CURRENT_BLOCK_RESPONSE=$(curl -s $API_URL/v2/info) && \
  CURRENT_BLOCK_HEIGHT=$(echo "$CURRENT_BLOCK_RESPONSE" | jq -r '.stacks_tip_height') && \
  if [ "$CURRENT_NONCE" -gt "$INITIAL_NONCE" ] && [ "$CURRENT_BLOCK_HEIGHT" -gt "$INITIAL_BLOCK_HEIGHT" ]; then \
    printf "\033[32m✓ Contract deployment confirmed!\033[0m Nonce: $INITIAL_NONCE→$CURRENT_NONCE, Block: $INITIAL_BLOCK_HEIGHT→$CURRENT_BLOCK_HEIGHT\n" && \
    echo "Contract deployment confirmed at poll $POLL_COUNT" >> "$LOGFILE" && \
    break; \
  fi && \
  POLL_COUNT=$((POLL_COUNT + 1)) && \
  printf "." && \
  sleep 1; \
done && \
if [ $POLL_COUNT -eq $MAX_POLLS ]; then \
  printf "\033[31m✗ Timeout waiting for confirmation\033[0m\n" && \
  echo "Contract deployment confirmation timeout" >> "$LOGFILE"; \
else \
  printf "\n\033[33mFetching detailed transaction data...\033[0m\n" && \
  RETRY_COUNT=0 && \
  MAX_RETRIES=5 && \
  while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do \
    DELAY=$((2 ** RETRY_COUNT)) && \
    sleep $DELAY && \
    TX_DETAILS=$(curl -s $API_URL/v3/transaction/$CLEAN_TXID 2>/dev/null) && \
    if echo "$TX_DETAILS" | jq . >/dev/null 2>&1; then \
      echo "$TX_DETAILS" | jq . && \
      echo "Transaction details: $TX_DETAILS" >> "$LOGFILE" && \
      break; \
    else \
      RETRY_COUNT=$((RETRY_COUNT + 1)) && \
      if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then \
        printf "Retry $RETRY_COUNT/$MAX_RETRIES after ${DELAY}s delay...\n"; \
      fi; \
    fi; \
  done && \
  if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then \
    printf "\033[33mTransaction details: $TX_DETAILS\033[0m\n" && \
    echo "Transaction raw response after $MAX_RETRIES retries: $TX_DETAILS" >> "$LOGFILE"; \
  fi; \
fi && \
echo "Getting final balance..." >> "$LOGFILE" && \
BALANCE_AFTER_RESPONSE=$(curl -s $API_URL/v2/accounts/$PUBLISHER_ADDR | tee -a "$LOGFILE") && \
BALANCE_AFTER=$(echo "$BALANCE_AFTER_RESPONSE" | jq -r '.balance' | xargs printf '%d\n') && \
NONCE_AFTER=$(echo "$BALANCE_AFTER_RESPONSE" | jq -r '.nonce') && \
if [ "$NONCE_AFTER" -gt "$NONCE" ]; then NONCE_DIFF=$((NONCE_AFTER - NONCE)); printf "Publisher nonce after: \033[32m$NONCE_AFTER\033[0m (increased by $NONCE_DIFF)\n"; elif [ "$NONCE_AFTER" -lt "$NONCE" ]; then NONCE_DIFF=$((NONCE - NONCE_AFTER)); printf "Publisher nonce after: \033[31m$NONCE_AFTER\033[0m (decreased by $NONCE_DIFF)\n"; else printf "Publisher nonce after: \033[37m$NONCE_AFTER\033[0m (unchanged)\n"; fi && \
if [ "$BALANCE_AFTER" -lt "$BALANCE_BEFORE" ]; then DIFF=$((BALANCE_BEFORE - BALANCE_AFTER)); printf "Publisher balance after: \033[31m$BALANCE_AFTER\033[0m (decreased by $DIFF)\n"; elif [ "$BALANCE_AFTER" -gt "$BALANCE_BEFORE" ]; then DIFF=$((BALANCE_AFTER - BALANCE_BEFORE)); printf "Publisher balance after: \033[32m$BALANCE_AFTER\033[0m (increased by $DIFF)\n"; else printf "Publisher balance after: \033[37m$BALANCE_AFTER\033[0m (unchanged)\n"; fi && \
echo "=== CONTRACT DEPLOYMENT LOG END - $(date) ===" >> "$LOGFILE" && \
echo "Log saved: $LOGFILE"