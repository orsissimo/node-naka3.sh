#!/bin/bash

set -ueo pipefail

_SOURCER=${BASH_SOURCE[1]} 

require_func() {
    local fn="$1"
    if ! declare -f "$fn" > /dev/null; then
        echo "Error: Required function '$fn' is not defined. Please define it in your playbook file: $_SOURCER"
        exit 1
    fi
}


function playbook_run() {
    while getopts "c:" OPT; do
    case "$OPT" in
        c)
            CONFIG="$OPTARG"
            shift 2
            ;;
        h)
            echo "Usage: $_SOURCER start|resume|stop|btc_automatic|btc_manual|btc_mine|info"
            exit 0
            ;;
        ?)
            echo "Unrecognized option -${OPT}"
            exit 1
            ;;
    esac
    done
    
    source "$CONFIG"

    local cmd
    set +ue
    cmd="$1"
    set -ue

    playbook_basedir="$(conf_get_basedir)"

    echo "Command is '$cmd'"
    case "$cmd" in 
        start)
            echo "Starting $playbook_basedir ... "
            
            require_func "playbook_start"
            require_func "playbook_loop"

            rm -rf "$playbook_basedir"
            playbook_start
            mkdir -p "$playbook_basedir"
            echo "automatic" > "$playbook_basedir/.btc_mining_state"
            playbook_loop
            ;;
        
        resume)
            echo "Resuming $playbook_basedir ... "

            require_func "playbook_resume"
            require_func "playbook_stop"
            playbook_resume
            mkdir -p "$playbook_basedir"
            echo "automatic" > "$playbook_basedir/.btc_mining_state"
            playbook_loop
            ;;

        btc_automatic)
            state_file="$playbook_basedir/.btc_mining_state"
            
            if [ -f "$state_file" ] && [ "$(cat "$state_file")" = "automatic" ]; then
                echo "BTC mining is already in automatic mode. No action needed."
            else
                echo "Starting BTC automatic mining mode for $playbook_basedir ... "
                
                require_func "playbook_resume"
                require_func "playbook_loop"
                
                playbook_resume
                mkdir -p "$playbook_basedir"
                echo "automatic" > "$state_file"
                playbook_loop
            fi
            ;;

        btc_manual)
            state_file="$playbook_basedir/.btc_mining_state"
            
            if [ -f "$state_file" ] && [ "$(cat "$state_file")" = "manual" ]; then
                echo "BTC mining is already in manual mode. No action needed."
            else
                echo "Switching to BTC manual mining mode for $playbook_basedir ... "
                
                require_func "playbook_resume"
                
                # Resume services but do NOT start the mining loop (ignore errors if already running)
                set +e
                playbook_resume
                set -e
                
                mkdir -p "$playbook_basedir"
                echo "manual" > "$state_file"
                echo "BTC mining is now in manual mode. Use 'btc_mine' command to mine blocks."
                echo "Note: Automatic BTC mining loop has been stopped."
            fi
            ;;

        btc_mine)
            state_file="$playbook_basedir/.btc_mining_state"
            
            if [ -f "$state_file" ] && [ "$(cat "$state_file")" = "automatic" ]; then
                echo "Error: BTC mining is in automatic mode. Switch to manual mode first with 'btc_manual' command."
                exit 1
            else
                echo "Mining single BTC block for $playbook_basedir ... "
                
                require_func "playbook_btc_mine"
                
                playbook_btc_mine
            fi
            ;;

        info)
            state_file="$playbook_basedir/.btc_mining_state"
            
            echo "=== BTC Mining Status ==="
            if [ -f "$state_file" ]; then
                mode=$(cat "$state_file")
                echo "Mining Mode: $mode"
            else
                echo "Mining Mode: unknown (no state file found)"
            fi
            
            echo "Playbook Directory: $playbook_basedir"
            
            # Check if processes are running
            if [ -d "$playbook_basedir" ]; then
                echo "Playbook Status: initialized"
                
                # Try to get BTC block height if bitcoind is accessible
                if command -v "$naka3" >/dev/null 2>&1; then
                    if [ -f "./config-bitcoind-0.sh" ]; then
                        set +e
                        block_height=$("$naka3" -c "./config-bitcoind-0.sh" bitcoind getblockcount 2>/dev/null)
                        if [ $? -eq 0 ]; then
                            echo "BTC Block Height: $block_height"
                        else
                            echo "BTC Block Height: unable to retrieve (bitcoind may not be running)"
                        fi
                        set -e
                    fi
                fi
            else
                echo "Playbook Status: not initialized"
            fi
            ;;

        stop)
            echo "Stopping $playbook_basedir ... "

            require_func "playbook_loop"

            playbook_stop
            ;;
        
        snapshot)
            local sub
            set +ue
            sub="$2"
            set -ue

            echo "Subcommand is '$sub'"
            case "$sub" in 
                create)
                    snap_basedir="$playbook_basedir"_snapshot
                    echo "Snapshotting $playbook_basedir ... "
                    
                    require_func "playbook_start"

                    rm -rf "$playbook_basedir"
                    rm -rf "$snap_basedir"
                    mkdir -p "$snap_basedir"

                    playbook_start
                    playbook_stop
                    sleep 10
                    cp -r "$playbook_basedir"/. "$snap_basedir"/
                    #rsync -a --ignore-errors "$playbook_basedir" "$snap_basedir"
                    ;;

                restore)
                    snap_basedir="$playbook_basedir"_snapshot
                    echo "Restoring snapshot from $snap_basedir ... "

                    require_func "playbook_resume"
                    
                    if ! [ -d "$snap_basedir" ]; then
                        echo "Snapshot doesn't exist: $snap_basedir"
                        exit 1
                    fi

                    rm -rf "$playbook_basedir"
                    mkdir -p "$playbook_basedir"
                    cp -r "$snap_basedir"/. "$playbook_basedir"/
                    #rsync -a --ignore-errors "$snap_basedir" "$playbook_basedir"

                    playbook_resume
                    echo "automatic" > "$playbook_basedir/.btc_mining_state"
                    playbook_loop
                    ;;

                *)        
                    echo "Usage: $_SOURCER start|resume|stop|btc_automatic|btc_manual|btc_mine|info|snapshot [create, restore]"
                    ;;
            esac
            ;;

        *)
            echo "Usage: $_SOURCER start|resume|stop|btc_automatic|btc_manual|btc_mine|info|snapshot [create, restore]"
            ;;
    esac
}
