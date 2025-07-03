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
LOGFILE="./logs/transaction_${TIMESTAMP}_${MINER}.log" && \
echo "=== TRANSACTION LOG START - $(date) ===" > "$LOGFILE" && \
echo "Miner: $MINER" >> "$LOGFILE" && \
echo "API URL: $API_URL" >> "$LOGFILE" && \
echo "Creating transaction..." && \
# Use funded accounts based on miner
case "$MINER" in
    miner1) SENDER_ADDR="STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6"; SENDER_KEY="cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01" ;;
    miner2) SENDER_ADDR="ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y"; SENDER_KEY="21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601" ;;
    miner3) SENDER_ADDR="ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0"; SENDER_KEY="7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01" ;;
esac && \
RECIPIENT_ADDR="ST3KCNDSWZSFZCC6BE4VA9AXWXC9KEB16FBTRK36T" && \
echo "Sender: $SENDER_ADDR" >> "$LOGFILE" && \
echo "Recipient: $RECIPIENT_ADDR" >> "$LOGFILE" && \
echo "Getting initial nonce..." >> "$LOGFILE" && \
NONCE_RESPONSE=$(curl -s $API_URL/v2/accounts/$SENDER_ADDR | tee -a "$LOGFILE") && \
NONCE=$(echo "$NONCE_RESPONSE" | jq -r '.nonce') && \
echo "Nonce: $NONCE" && \
echo "Transfer amount: 1000 microSTX" && \
echo "Getting sender balance..." >> "$LOGFILE" && \
SENDER_BEFORE_RESPONSE=$(curl -s $API_URL/v2/accounts/$SENDER_ADDR | tee -a "$LOGFILE") && \
SENDER_BEFORE=$(echo "$SENDER_BEFORE_RESPONSE" | jq -r '.balance' | xargs printf '%d\n') && \
echo "Getting recipient balance..." >> "$LOGFILE" && \
RECIPIENT_BEFORE_RESPONSE=$(curl -s $API_URL/v2/accounts/$RECIPIENT_ADDR | tee -a "$LOGFILE") && \
RECIPIENT_BEFORE=$(echo "$RECIPIENT_BEFORE_RESPONSE" | jq -r '.balance' | xargs printf '%d\n') && \
printf "Sender balance before: \033[37m$SENDER_BEFORE\033[0m\n" && \
printf "Recipient balance before: \033[37m$RECIPIENT_BEFORE\033[0m\n" && \
echo "Creating blockstack-cli command..." >> "$LOGFILE" && \
echo "blockstack-cli --testnet token-transfer $SENDER_KEY 180 $NONCE $RECIPIENT_ADDR 1000 HelloMemo$NONCE" >> "$LOGFILE" && \
blockstack-cli --testnet token-transfer $SENDER_KEY 180 $NONCE $RECIPIENT_ADDR 1000 HelloMemo$NONCE | xxd -r -p > ./tmp/stx-tx-auto.bin && \
echo "Submitting transaction..." >> "$LOGFILE" && \
TXID=$(curl -s -X POST -H "Content-Type: application/octet-stream" --data-binary @./tmp/stx-tx-auto.bin $API_URL/v2/transactions | tee -a "$LOGFILE") && \
printf "\033[32mTransaction ID: $TXID\033[0m\n" && \
echo "Polling for transaction confirmation..." >> "$LOGFILE" && \
CLEAN_TXID=$(echo "$TXID" | tr -d '"') && \
printf "Waiting for transaction \033[36m$CLEAN_TXID\033[0m to be processed...\n" && \
POLL_COUNT=0 && \
MAX_POLLS=300 && \
INITIAL_NONCE=$NONCE && \
INITIAL_BLOCK_RESPONSE=$(curl -s $API_URL/v2/info) && \
INITIAL_BLOCK_HEIGHT=$(echo "$INITIAL_BLOCK_RESPONSE" | jq -r '.stacks_tip_height') && \
echo "Initial block height: $INITIAL_BLOCK_HEIGHT" >> "$LOGFILE" && \
while [ $POLL_COUNT -lt $MAX_POLLS ]; do \
  CURRENT_NONCE_RESPONSE=$(curl -s $API_URL/v2/accounts/$SENDER_ADDR) && \
  CURRENT_NONCE=$(echo "$CURRENT_NONCE_RESPONSE" | jq -r '.nonce') && \
  CURRENT_BLOCK_RESPONSE=$(curl -s $API_URL/v2/info) && \
  CURRENT_BLOCK_HEIGHT=$(echo "$CURRENT_BLOCK_RESPONSE" | jq -r '.stacks_tip_height') && \
  if [ "$CURRENT_NONCE" -gt "$INITIAL_NONCE" ] && [ "$CURRENT_BLOCK_HEIGHT" -gt "$INITIAL_BLOCK_HEIGHT" ]; then \
    printf "\033[32m✓ Transaction confirmed!\033[0m Nonce: $INITIAL_NONCE→$CURRENT_NONCE, Block: $INITIAL_BLOCK_HEIGHT→$CURRENT_BLOCK_HEIGHT\n" && \
    echo "Transaction confirmed at poll $POLL_COUNT" >> "$LOGFILE" && \
    break; \
  fi && \
  POLL_COUNT=$((POLL_COUNT + 1)) && \
  printf "." && \
  sleep 1; \
done && \
if [ $POLL_COUNT -eq $MAX_POLLS ]; then \
  printf "\033[31m✗ Timeout waiting for confirmation\033[0m\n" && \
  echo "Transaction confirmation timeout" >> "$LOGFILE"; \
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
echo "Getting final sender balance..." >> "$LOGFILE" && \
SENDER_AFTER_RESPONSE=$(curl -s $API_URL/v2/accounts/$SENDER_ADDR | tee -a "$LOGFILE") && \
SENDER_AFTER=$(echo "$SENDER_AFTER_RESPONSE" | jq -r '.balance' | xargs printf '%d\n') && \
echo "Getting final recipient balance..." >> "$LOGFILE" && \
RECIPIENT_AFTER_RESPONSE=$(curl -s $API_URL/v2/accounts/$RECIPIENT_ADDR | tee -a "$LOGFILE") && \
RECIPIENT_AFTER=$(echo "$RECIPIENT_AFTER_RESPONSE" | jq -r '.balance' | xargs printf '%d\n') && \
NONCE_AFTER=$(echo "$SENDER_AFTER_RESPONSE" | jq -r '.nonce') && \
if [ "$NONCE_AFTER" -gt "$NONCE" ]; then NONCE_DIFF=$((NONCE_AFTER - NONCE)); printf "Sender nonce after: \033[32m$NONCE_AFTER\033[0m (increased by $NONCE_DIFF)\n"; elif [ "$NONCE_AFTER" -lt "$NONCE" ]; then NONCE_DIFF=$((NONCE - NONCE_AFTER)); printf "Sender nonce after: \033[31m$NONCE_AFTER\033[0m (decreased by $NONCE_DIFF)\n"; else printf "Sender nonce after: \033[37m$NONCE_AFTER\033[0m (unchanged)\n"; fi && \
if [ "$SENDER_AFTER" -lt "$SENDER_BEFORE" ]; then DIFF=$((SENDER_BEFORE - SENDER_AFTER)); printf "Sender balance after: \033[31m$SENDER_AFTER\033[0m (decreased by $DIFF)\n"; elif [ "$SENDER_AFTER" -gt "$SENDER_BEFORE" ]; then DIFF=$((SENDER_AFTER - SENDER_BEFORE)); printf "Sender balance after: \033[32m$SENDER_AFTER\033[0m (increased by $DIFF)\n"; else printf "Sender balance after: \033[37m$SENDER_AFTER\033[0m (unchanged)\n"; fi && \
if [ "$RECIPIENT_AFTER" -gt "$RECIPIENT_BEFORE" ]; then DIFF=$((RECIPIENT_AFTER - RECIPIENT_BEFORE)); printf "Recipient balance after: \033[32m$RECIPIENT_AFTER\033[0m (increased by $DIFF)\n"; elif [ "$RECIPIENT_AFTER" -lt "$RECIPIENT_BEFORE" ]; then DIFF=$((RECIPIENT_BEFORE - RECIPIENT_AFTER)); printf "Recipient balance after: \033[31m$RECIPIENT_AFTER\033[0m (decreased by $DIFF)\n"; else printf "Recipient balance after: \033[37m$RECIPIENT_AFTER\033[0m (unchanged)\n"; fi && \
echo "=== TRANSACTION LOG END - $(date) ===" >> "$LOGFILE" && \
echo "Log saved: $LOGFILE"