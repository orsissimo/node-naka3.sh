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
            echo "Usage: $_SOURCER start|resume|stop"
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
            playbook_loop
            ;;
        
        resume)
            echo "Resuming $playbook_basedir ... "

            require_func "playbook_resume"
            require_func "playbook_stop"
            playbook_resume
            playbook_loop
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
                    playbook_loop
                    ;;

                *)        
                    echo "Usage: $_SOURCER start|resume|stop|snapshot [create, restore]"
                    ;;
            esac
            ;;

        *)
            echo "Usage: $_SOURCER start|resume|stop|snapshot [create, restore]"
            ;;
    esac
}
