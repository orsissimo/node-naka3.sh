#!/bin/bash

MINER=${1:-miner1} && \
case "$MINER" in
    miner1) MINER_PORT=20443 ;;
    miner2) MINER_PORT=30443 ;;
    miner3) MINER_PORT=40443 ;;
    *) echo "Error: Invalid miner '$MINER'. Use miner1, miner2, or miner3" && exit 1 ;;
esac && \
API_URL="http://localhost:$MINER_PORT" && \
echo "Using $MINER on port: $MINER_PORT" && \
mkdir -p ./tmp && \

echo "Starting Stacks chain monitoring..." && \
echo "Press Ctrl+C to stop monitoring" && \
echo "" && \

ITERATION=0 && \
LAST_STACKS_HEIGHT="" && \
LAST_BURN_HEIGHT="" && \

while true; do
    ITERATION=$((ITERATION + 1)) && \
    
    echo "[$ITERATION] Checking chain status..." && \
    
    INFO_RESPONSE=$(curl -s $API_URL/v2/info) && \
    STACKS_HEIGHT=$(echo "$INFO_RESPONSE" | jq -r '.stacks_tip_height') && \
    BURN_HEIGHT=$(echo "$INFO_RESPONSE" | jq -r '.burn_block_height') && \
    STACKS_TIP=$(echo "$INFO_RESPONSE" | jq -r '.stacks_tip') && \
    IS_SYNCED=$(echo "$INFO_RESPONSE" | jq -r '.is_fully_synced') && \
    TENURE_HEIGHT=$(echo "$INFO_RESPONSE" | jq -r '.tenure_height') && \
    
    POX_RESPONSE=$(curl -s $API_URL/v2/pox) && \
    CURRENT_CYCLE=$(echo "$POX_RESPONSE" | jq -r '.current_cycle.id') && \
    NEXT_CYCLE=$(echo "$POX_RESPONSE" | jq -r '.next_cycle.id') && \
    BLOCKS_UNTIL_REWARD=$(echo "$POX_RESPONSE" | jq -r '.next_cycle.blocks_until_reward_phase') && \
    POX_ACTIVE=$(echo "$POX_RESPONSE" | jq -r '.current_cycle.is_pox_active') && \
    
    printf "Stacks height: \033[36m$STACKS_HEIGHT\033[0m" && \
    if [ "$LAST_STACKS_HEIGHT" != "" ] && [ "$STACKS_HEIGHT" != "$LAST_STACKS_HEIGHT" ]; then
        STACKS_DIFF=$((STACKS_HEIGHT - LAST_STACKS_HEIGHT))
        if [ "$STACKS_DIFF" -gt 0 ]; then
            printf " \033[32m(+$STACKS_DIFF)\033[0m"
        else
            printf " \033[31m($STACKS_DIFF)\033[0m"
        fi
    fi
    echo "" && \
    
    printf "Burn height: \033[36m$BURN_HEIGHT\033[0m" && \
    if [ "$LAST_BURN_HEIGHT" != "" ] && [ "$BURN_HEIGHT" != "$LAST_BURN_HEIGHT" ]; then
        BURN_DIFF=$((BURN_HEIGHT - LAST_BURN_HEIGHT))
        if [ "$BURN_DIFF" -gt 0 ]; then
            printf " \033[32m(+$BURN_DIFF)\033[0m"
        else
            printf " \033[31m($BURN_DIFF)\033[0m"
        fi
    fi
    echo "" && \
    
    echo "Tenure height: $TENURE_HEIGHT" && \
    echo "Stacks tip: ${STACKS_TIP:0:16}..." && \
    
    if [ "$IS_SYNCED" = "true" ]; then
        printf "Sync status: \033[32mSynced\033[0m\n"
    else
        printf "Sync status: \033[31mNot synced\033[0m\n"
    fi && \
    
    echo "Current PoX cycle: $CURRENT_CYCLE" && \
    echo "Next PoX cycle: $NEXT_CYCLE" && \
    
    if [ "$POX_ACTIVE" = "true" ]; then
        printf "PoX status: \033[32mActive\033[0m\n"
    else
        printf "PoX status: \033[33mInactive\033[0m\n"
    fi && \
    
    echo "Blocks until reward phase: $BLOCKS_UNTIL_REWARD" && \
    
    # Process monitoring from old-monitor.sh
    echo "" && \
    printf "\033[33mstacks-node:\033[0m\n" && \
    ports=(20443 30443 40443) && \
    pids=$(pgrep stacks-node) && \
    i=0 && \
    for p in "${ports[@]}"; do
        pid=$(echo "$pids" | sed -n "$((i + 1))p")
        i=$((i + 1))
        [ -z "${pid:-}" ] && continue
        
        exe=$(readlink -f /proc/"$pid"/exe 2>/dev/null)
        stats=$(curl -sL 127.0.0.1:"$p"/v2/info 2>/dev/null |
            jq -r '[.stacks_tip_height, .burn_block_height] | @tsv' 2>/dev/null |
            tr '\t' ' ')
        
        printf "  \033[36m$pid\033[0m:\033[32m$p\033[0m(\033[35m$stats\033[0m) -> \033[90m$exe\033[0m\n"
    done && \
    
    printf "\033[33mstacks-signer:\033[0m\n" && \
    for pid in $(pgrep stacks-signer); do
        exe=$(readlink -f /proc/"$pid"/exe 2>/dev/null)
        printf "  \033[36m$pid\033[0m -> \033[90m$exe\033[0m\n"
    done && \
    
    LAST_STACKS_HEIGHT="$STACKS_HEIGHT" && \
    LAST_BURN_HEIGHT="$BURN_HEIGHT" && \
    
    echo "" && \
    sleep 10
done && \

echo "Monitoring stopped."