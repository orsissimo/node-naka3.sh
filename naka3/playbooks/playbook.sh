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
            echo "Usage: $_SOURCER [COMMAND] [OPTIONS]"
            echo "Commands:"
            echo "  start <auto|manual>        - Start in automatic or manual mining mode (required)"
            echo "  resume                     - Resume from stopped state"
            echo "  stop                       - Stop all services"
            echo "  btc_auto                   - Switch to automatic mining mode"
            echo "  btc_manual                 - Switch to manual mining mode"
            echo "  btc_mine                   - Mine single block (manual mode only)"
            echo "  info                       - Show status information"
            echo "  snapshot create            - Create generic snapshot"
            echo "  snapshot restore <auto|manual> - Restore snapshot in specified mode (required)"
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
            local start_mode
            set +ue
            start_mode="$2"
            set -ue
            
            # Require explicit mode - no defaults
            if [ -z "$start_mode" ]; then
                echo "Error: Start mode is required. Use 'auto' or 'manual'"
                echo "Usage: start <auto|manual>"
                exit 1
            elif [ "$start_mode" = "auto" ]; then
                start_mode="automatic"
            elif [ "$start_mode" = "manual" ]; then
                start_mode="manual"
            else
                echo "Error: Invalid start mode '$start_mode'. Use 'auto' or 'manual'"
                echo "Usage: start <auto|manual>"
                exit 1
            fi
            
            echo "Starting $playbook_basedir in $start_mode mode... "
            
            require_func "playbook_start"
            require_func "playbook_loop"

            rm -rf "$playbook_basedir"
            playbook_start
            mkdir -p "$playbook_basedir"
            echo "$start_mode" > "$playbook_basedir/.btc_mining_state"
            
            if [ "$start_mode" = "automatic" ]; then
                echo "Starting in automatic mining mode"
            else
                echo "Starting in manual mining mode. Use 'btc_mine' to mine blocks manually."
            fi
            
            # Always start the loop to show logs and handle state changes
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

        btc_auto)
            state_file="$playbook_basedir/.btc_mining_state"
            
            if [ -f "$state_file" ] && [ "$(cat "$state_file")" = "automatic" ]; then
                echo "BTC mining is already in automatic mode. No action needed."
            else
                echo "Starting BTC automatic mining mode for $playbook_basedir ... "
                
                require_func "playbook_resume"
                require_func "playbook_loop"
                
                # Resume services but ignore errors if already running
                set +e
                playbook_resume
                set -e
                
                mkdir -p "$playbook_basedir"
                echo "automatic" > "$state_file"
                echo "Switched to automatic mining mode. The main loop will resume automatic mining."
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
            else
                echo "Playbook Status: not initialized"
            fi
            ;;

        stop)
            echo "Stopping $playbook_basedir ... "

            require_func "playbook_stop"

            # Stop services
            playbook_stop
            
            # Kill any running three-miners.sh background processes
            echo "Terminating background three-miners processes..."
            playbook_script_name="$(basename "$_SOURCER")"
            
            # Find and kill any background three-miners.sh processes (except current one)
            current_pid=$$
            pids_to_kill=$(pgrep -f "$playbook_script_name" | grep -v "^$current_pid$" || true)
            
            if [ -n "$pids_to_kill" ]; then
                echo "Found background processes to terminate: $pids_to_kill"
                echo "$pids_to_kill" | xargs kill -TERM 2>/dev/null || true
                sleep 2
                # Force kill if still running
                echo "$pids_to_kill" | xargs kill -KILL 2>/dev/null || true
                echo "Background processes terminated"
            else
                echo "No background processes found"
            fi
            
            echo "Stop completed"
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
                    echo "Creating generic snapshot of $playbook_basedir... "
                    
                    require_func "playbook_start"

                    rm -rf "$playbook_basedir"
                    rm -rf "$snap_basedir"
                    mkdir -p "$snap_basedir"

                    playbook_start
                    playbook_stop
                    sleep 10
                    cp -r "$playbook_basedir"/. "$snap_basedir"/
                    
                    echo "Generic snapshot created"
                    #rsync -a --ignore-errors "$playbook_basedir" "$snap_basedir"
                    ;;

                restore)
                    local restore_mode
                    set +ue
                    restore_mode="$3"
                    set -ue
                    
                    snap_basedir="$playbook_basedir"_snapshot
                    
                    if ! [ -d "$snap_basedir" ]; then
                        echo "Snapshot doesn't exist: $snap_basedir"
                        exit 1
                    fi
                    
                    # Require explicit restore mode - no defaults
                    if [ -z "$restore_mode" ]; then
                        echo "Error: Restore mode is required. Use 'auto' or 'manual'"
                        echo "Usage: snapshot restore <auto|manual>"
                        exit 1
                    elif [ "$restore_mode" = "auto" ]; then
                        restore_mode="automatic"
                        echo "Restoring snapshot from $snap_basedir in automatic mode..."
                    elif [ "$restore_mode" = "manual" ]; then
                        restore_mode="manual"
                        echo "Restoring snapshot from $snap_basedir in manual mode..."
                    else
                        echo "Error: Invalid snapshot restore mode '$restore_mode'. Use 'auto' or 'manual'"
                        echo "Usage: snapshot restore <auto|manual>"
                        exit 1
                    fi

                    require_func "playbook_resume"

                    rm -rf "$playbook_basedir"
                    mkdir -p "$playbook_basedir"
                    cp -r "$snap_basedir"/. "$playbook_basedir"/
                    #rsync -a --ignore-errors "$snap_basedir" "$playbook_basedir"

                    playbook_resume
                    echo "$restore_mode" > "$playbook_basedir/.btc_mining_state"
                    
                    if [ "$restore_mode" = "automatic" ]; then
                        echo "Snapshot restored in automatic mining mode"
                    else
                        echo "Snapshot restored in manual mining mode. Use 'btc_mine' to mine blocks manually."
                    fi
                    
                    # Always start the loop to show logs and handle state changes
                    playbook_loop
                    ;;

                *)        
                    echo "Usage: $_SOURCER snapshot [create|restore]"
                    echo "  create                    - Create generic snapshot"
                    echo "  restore <auto|manual>     - Restore snapshot in specified mode (required)"
                    ;;
            esac
            ;;

        *)
            echo "Usage: $_SOURCER [COMMAND] [OPTIONS]"
            echo "Commands:"
            echo "  start <auto|manual>        - Start in automatic or manual mining mode (required)"
            echo "  resume                     - Resume from stopped state"
            echo "  stop                       - Stop all services"
            echo "  btc_auto                   - Switch to automatic mining mode"
            echo "  btc_manual                 - Switch to manual mining mode"
            echo "  btc_mine                   - Mine single block (manual mode only)"
            echo "  info                       - Show status information"
            echo "  snapshot create            - Create generic snapshot"
            echo "  snapshot restore <auto|manual> - Restore snapshot in specified mode (required)"
            ;;
    esac
}
