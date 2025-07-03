#!/bin/bash

# Topology:
#
#
#            `bitcoind 0`
#                 |
#                 |
#                 V
#             `stacks 0`
#             `(miner) `
#              ^  ^  ^
#    .---------*  |  *---------.
#    |            |            |
#    |            |            |
#`signer 0`   `signer 1`   `signer 2`
set -ueo pipefail
naka3="../../naka3.sh"
source ../playbook.sh

function playbook_start() {
   "$naka3" -c "./config-signer-0.sh" signer 0 config
   "$naka3" -c "./config-signer-1.sh" signer 1 config
   "$naka3" -c "./config-signer-2.sh" signer 2 config
   "$naka3" node 0 config-miner-stacker "0,1,2"

   btcaddr="$("$naka3" node 0 miner-addr | jq -r '.BTC')"
   echo "Miner address is $btcaddr"
   
   "$naka3" bitcoind start
   "$naka3" bitcoind mine 101 "$btcaddr"

   "$naka3" -c "./config-signer-0.sh" signer 0 start
   "$naka3" -c "./config-signer-1.sh" signer 1 start
   "$naka3" -c "./config-signer-2.sh" signer 2 start
   "$naka3" node 0 start

   # advance to epoch 2.5 (starts at 108)
   # go to 112
   for i in $(seq 0 10); do
      sleep 10
      "$naka3" bitcoind mine 1 "$btcaddr"
   done

   echo "stack stackity stack-stack-stack"
   for i in $(seq 0 2); do
      tx="$("$naka3" -c "./config-signer-$i.sh" signer "$i" stack-tx 5 9000000000000000 0 1)"
      "$naka3" node 0 send-tx "$tx"
   done

   burn_mined=112
   TARGET_HEIGHT=141
   while true; do
      curr_bh="$("$naka3" node 0 burn-height)"
      echo "Node Burn Height: $curr_bh"

      if [[ "$curr_bh" -ge "$TARGET_HEIGHT" ]]; then
        echo "Target burn_block_height $TARGET_HEIGHT reached!"
        break
      fi

      if [[ "$curr_bh" -lt "$burn_mined" ]]; then
        echo "Waiting to catch-up: $curr_bh/$burn_mined"
        sleep 1s
        continue
      fi

      "$naka3" bitcoind mine 1 "$btcaddr"
      burn_mined=$((burn_mined + 1))
      sleep 15s
   done
}

function playbook_resume() {
   "$naka3" bitcoind resume
   "$naka3" -c "./config-signer-0.sh" signer 0 resume
   "$naka3" -c "./config-signer-1.sh" signer 1 resume
   "$naka3" -c "./config-signer-2.sh" signer 2 resume
   "$naka3" node 0 resume
}

function playbook_stop() {
   "$naka3" tx end-transfers "/tmp/one-miner/end-transfers"
   "$naka3" node 0 stop
   "$naka3" -c "./config-signer-0.sh" signer 0 stop
   "$naka3" -c "./config-signer-1.sh" signer 1 stop
   "$naka3" -c "./config-signer-2.sh" signer 2 stop
   "$naka3" bitcoind stop
}

function playbook_loop() {
   touch "/tmp/one-miner/mine"

   btcaddr="$("$naka3" node 0 miner-addr | jq -r '.BTC')"
   echo "Miner address is $btcaddr"

   # run forever, but only mine on command
   while true; do
      "$naka3" bitcoind mine 1 "$btcaddr"
      sleep 0.75s
      
      "$naka3" bitcoind mine 1 "$btcaddr"
      sleep 15s
      
      "$naka3" bitcoind mine 1 "$btcaddr"
      sleep 15s
   done
}

playbook_run -c "./config.sh" $@
