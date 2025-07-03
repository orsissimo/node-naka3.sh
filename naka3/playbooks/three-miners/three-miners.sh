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

   while true; do
      "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
      sleep 0.75s
      
      "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
      sleep 15s
      
      "$naka3" -c "./config-bitcoind-0.sh" bitcoind mine 1 "$btcaddr_0"
      sleep 15s
   done
}

playbook_run -c "./config.sh" $@
