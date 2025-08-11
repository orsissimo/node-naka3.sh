#!/bin/bash

set -ueo pipefail
naka3="../../naka3.sh"
source ../playbook.sh

function playbook_start() {
   "$naka3" -c "./config-signer-0.sh" signer 0 config
   "$naka3" -c "./config-signer-1.sh" signer 1 config
   "$naka3" -c "./config-signer-2.sh" signer 2 config

   "$naka3" -c "./config-miner-0.sh" node 0 config-miner-stacker "0,1,2"
   "$naka3" -c "./config-miner-1.sh" node 1 config-miner "none"
   "$naka3" -c "./config-miner-2.sh" node 2 config-miner "none"

   btcaddr_0="$("$naka3" -c "./config-miner-0.sh" node 0 miner-addr | jq -r '.BTC')"
   btcaddr_1="$("$naka3" -c "./config-miner-1.sh" node 1 miner-addr | jq -r '.BTC')"
   btcaddr_2="$("$naka3" -c "./config-miner-2.sh" node 2 miner-addr | jq -r '.BTC')"

   echo "Miner address is $btcaddr_0"
   echo "Miner address is $btcaddr_1"
   echo "Miner address is $btcaddr_2"

   "$naka3" -c "./config-bitcoind-0.sh" bitcoind start
   "$naka3" -c "./config-bitcoind-1.sh" bitcoind start
   "$naka3" -c "./config-bitcoind-2.sh" bitcoind start

   "$naka3" -c "./config-bitcoind-0.sh" bitcoind peer "127.0.0.1" "28332"
   "$naka3" -c "./config-bitcoind-0.sh" bitcoind peer "127.0.0.1" "38332"

   "$naka3" -c "./config-bitcoind-1.sh" bitcoind peer "127.0.0.1" "18332"
   "$naka3" -c "./config-bitcoind-1.sh" bitcoind peer "127.0.0.1" "38332"

   "$naka3" -c "./config-bitcoind-2.sh" bitcoind peer "127.0.0.1" "18332"
   "$naka3" -c "./config-bitcoind-2.sh" bitcoind peer "127.0.0.1" "28332"

   # Mined 105 bitcoin blocks
   for i in $(seq 0 34); do
      "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
      sleep 0.5s
      "$naka3" -c "./config-bitcoind-1.sh" bitcoind mine 1 "$btcaddr_1"
      sleep 0.5s
      "$naka3" -c "./config-bitcoind-2.sh" bitcoind mine 1 "$btcaddr_2"
      sleep 0.5s
   done
   
   # boot signers
   "$naka3" -c "./config-signer-0.sh" signer 0 start
   "$naka3" -c "./config-signer-1.sh" signer 1 start
   "$naka3" -c "./config-signer-2.sh" signer 2 start

   # boot miner nodes
   "$naka3" -c "./config-miner-0.sh" node 0 start
   "$naka3" -c "./config-miner-1.sh" node 1 start
   "$naka3" -c "./config-miner-2.sh" node 2 start

   # advance to epoch 2.5 (starts at 108)
   # Mined 112 bitcoin blocks
   for i in $(seq 0 6); do
      sleep 10
      "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
   done

   echo "stack stackity stack-stack-stack"
   for i in $(seq 0 2); do
      tx="$("$naka3" -c "./config-signer-$i.sh" signer "$i" stack-tx 5 9000000000000000 0 1)"
      "$naka3" -c "./config-miner-0.sh" node 0 send-tx "$tx"
   done

   # mine through Nakamoto activation (epoch 3.1 starts at 141)
   # Mined 141 bitcoin blocks
   for i in $(seq 0 28); do
      "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
      sleep 15s
   done
}

function playbook_resume() {
   "$naka3" -c "./config-bitcoind-0.sh" bitcoind resume
   "$naka3" -c "./config-bitcoind-1.sh" bitcoind resume
   "$naka3" -c "./config-bitcoind-2.sh" bitcoind resume
   "$naka3" -c "./config-bitcoind-0.sh" bitcoind peer "127.0.0.1" "28332"
   "$naka3" -c "./config-bitcoind-0.sh" bitcoind peer "127.0.0.1" "38332"
   "$naka3" -c "./config-bitcoind-1.sh" bitcoind peer "127.0.0.1" "18332"
   "$naka3" -c "./config-bitcoind-1.sh" bitcoind peer "127.0.0.1" "38332"
   "$naka3" -c "./config-bitcoind-2.sh" bitcoind peer "127.0.0.1" "18332"
   "$naka3" -c "./config-bitcoind-2.sh" bitcoind peer "127.0.0.1" "28332"

   "$naka3" -c "./config-signer-0.sh" signer 0 resume
   "$naka3" -c "./config-signer-1.sh" signer 1 resume
   "$naka3" -c "./config-signer-2.sh" signer 2 resume

   "$naka3" -c "./config-miner-0.sh" node 0 resume
   "$naka3" -c "./config-miner-1.sh" node 1 resume
   "$naka3" -c "./config-miner-2.sh" node 2 resume
}

function playbook_stop() {
   "$naka3" -c "./config-miner-0.sh" node 0 stop
   "$naka3" -c "./config-miner-1.sh" node 1 stop
   "$naka3" -c "./config-miner-2.sh" node 2 stop
   "$naka3" -c "./config-signer-0.sh" signer 0 stop
   "$naka3" -c "./config-signer-1.sh" signer 1 stop
   "$naka3" -c "./config-signer-2.sh" signer 2 stop
   "$naka3" -c "./config-bitcoind-0.sh" bitcoind stop
   "$naka3" -c "./config-bitcoind-1.sh" bitcoind stop
   "$naka3" -c "./config-bitcoind-2.sh" bitcoind stop
}

function playbook_loop() {
   btcaddr_0="$("$naka3" -c "./config-miner-0.sh" node 0 miner-addr | jq -r '.BTC')"
   echo "Miner 0 address is $btcaddr_0"

   playbook_basedir="$(conf_get_basedir)"
   state_file="$playbook_basedir/.btc_mining_state"

   while true; do
      current_mode="automatic"
      if [ -f "$state_file" ]; then
         current_mode=$(cat "$state_file")
      fi

      if [ "$current_mode" = "automatic" ]; then
         # Automatic mining mode
         "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
         sleep 0.75s
         
         "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
         
         # Check state more frequently during long sleeps
         for i in {1..15}; do
            sleep 1s
            if [ -f "$state_file" ] && [ "$(cat "$state_file")" != "automatic" ]; then
               echo "BTC mining mode changed to $(cat "$state_file"). Switching to manual mode."
               break
            fi
         done
         
         "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
         
         # Check state more frequently during long sleeps
         for i in {1..15}; do
            sleep 1s
            if [ -f "$state_file" ] && [ "$(cat "$state_file")" != "automatic" ]; then
               echo "BTC mining mode changed to $(cat "$state_file"). Switching to manual mode."
               break
            fi
         done
         
      elif [ "$current_mode" = "manual" ]; then
         # Manual mining mode - wait and watch for manual mining requests
         echo "Manual mining mode active. Waiting for mining commands..."
         
         # Create a trigger file for manual mining
         trigger_file="$playbook_basedir/.btc_mine_trigger"
         
         while [ "$current_mode" = "manual" ]; do
            # Check for mining trigger
            if [ -f "$trigger_file" ]; then
               echo "Manual mining triggered!"
               "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
               rm -f "$trigger_file"
               echo "Manual mining completed. Waiting for next command..."
            fi
            
            sleep 1s
            
            # Check if mode changed back to automatic
            if [ -f "$state_file" ]; then
               current_mode=$(cat "$state_file")
               if [ "$current_mode" = "automatic" ]; then
                  echo "BTC mining mode changed back to automatic. Resuming automatic mining."
                  break
               fi
            fi
         done
      else
         # Unknown mode, default to waiting
         echo "Unknown mining mode: $current_mode. Waiting..."
         sleep 5s
      fi
   done
}

function playbook_btc_mine() {
   playbook_basedir="$(conf_get_basedir)"
   trigger_file="$playbook_basedir/.btc_mine_trigger"
   
   # Create trigger file to signal the main loop to mine
   touch "$trigger_file"
   echo "Manual mining request sent. Check the main terminal for mining activity."
}

playbook_run -c "./config.sh" $@
