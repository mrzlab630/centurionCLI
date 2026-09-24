#!/bin/bash
#
# EVOCATE — External Model Delegation Script
# Part of CENTURION COHORS PRIMA
#
# Usage:
#   evocate.sh launch <model> <task-file>  # retired; fails closed
#   evocate.sh status <session-id>
#   evocate.sh results <session-id>
#   evocate.sh kill <session-id>
#   evocate.sh list
#   evocate.sh cleanup [session-id]
#

EVOCATE_DIR="$HOME/.claude/evocate"
SCRIPT_NAME="evocate.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure evocate directory exists
mkdir -p "$EVOCATE_DIR"

usage() {
    echo "EVOCATE — External Model Delegation"
    echo ""
    echo "Usage:"
    echo "  $SCRIPT_NAME launch <model> <task-file>   Retired; use Result Gateway"
    echo "  $SCRIPT_NAME status <session-id>          Check session status"
    echo "  $SCRIPT_NAME results <session-id>         Get session results"
    echo "  $SCRIPT_NAME kill <session-id>            Kill session"
    echo "  $SCRIPT_NAME list                         List active sessions"
    echo "  $SCRIPT_NAME cleanup [session-id]         Clean temp files (all or specific)"
    echo ""
    echo "Examples:"
    echo "  $SCRIPT_NAME status evocate-1705312345"
    echo "  $SCRIPT_NAME results evocate-1705312345"
    echo "  $SCRIPT_NAME cleanup evocate-1705312345"
    echo "  $SCRIPT_NAME list"
}

# Raw tmux launches predate the canonical Result Gateway and are retired.
cmd_launch() {
    echo "Error: raw EVOCATE launches are retired. Use the active controller's Result Gateway with a validated AGENT_ORDER_JSON_V1 order." >&2
    return 1
}

# Check session status
cmd_status() {
    local session_id="$1"

    if [[ -z "$session_id" ]]; then
        echo -e "${RED}Error: Missing session-id${NC}"
        exit 1
    fi

    if tmux has-session -t "$session_id" 2>/dev/null; then
        echo -e "${GREEN}Session $session_id: RUNNING${NC}"

        # Show last few lines of activity
        echo ""
        echo "Recent output:"
        tmux capture-pane -t "$session_id" -p | tail -15
    else
        echo -e "${YELLOW}Session $session_id: COMPLETED or NOT FOUND${NC}"

        # Check for results file
        local results_file="$EVOCATE_DIR/results-${session_id}.md"
        if [[ -f "$results_file" ]]; then
            echo "Results available: $results_file"
            echo ""
            echo "Status from results file:"
            grep -E "^## (Status|Completed|Exit)" "$results_file" 2>/dev/null || echo "  (no status info)"
        fi
    fi
}

# Get session results
cmd_results() {
    local session_id="$1"
    local delete_after="${2:-}"

    if [[ -z "$session_id" ]]; then
        echo -e "${RED}Error: Missing session-id${NC}"
        exit 1
    fi

    local results_file="$EVOCATE_DIR/results-${session_id}.md"

    echo -e "${GREEN}=== EVOCATE Results: $session_id ===${NC}"
    echo ""

    if [[ -f "$results_file" ]]; then
        cat "$results_file"

        # Option to delete results after viewing
        if [[ "$delete_after" == "--delete" ]]; then
            echo ""
            echo -e "${YELLOW}Deleting results file...${NC}"
            rm -f "$results_file"
            echo -e "${GREEN}Results file deleted.${NC}"
        fi
    else
        echo -e "${RED}No results found for session: $session_id${NC}"
        echo ""
        echo "The session may still be running. Check status:"
        echo "  $SCRIPT_NAME status $session_id"
        exit 1
    fi
}

# Kill session
cmd_kill() {
    local session_id="$1"

    if [[ -z "$session_id" ]]; then
        echo -e "${RED}Error: Missing session-id${NC}"
        exit 1
    fi

    if tmux has-session -t "$session_id" 2>/dev/null; then
        tmux kill-session -t "$session_id"
        echo -e "${GREEN}Session $session_id killed${NC}"

        # Update results file status
        local results_file="$EVOCATE_DIR/results-${session_id}.md"
        if [[ -f "$results_file" ]]; then
            sed -i 's/Status: RUNNING/Status: KILLED/' "$results_file"
        fi
    else
        echo -e "${YELLOW}Session $session_id not found or already closed${NC}"
    fi

    # Cleanup any remaining temp files for this session
    echo "Cleaning up session files..."
    rm -f "$EVOCATE_DIR/task-${session_id}.md" 2>/dev/null
    rm -f "$EVOCATE_DIR/log-${session_id}.txt" 2>/dev/null
    rm -f "$EVOCATE_DIR/run-${session_id}.sh" 2>/dev/null
    echo "Done."
}

# List active sessions
cmd_list() {
    echo -e "${GREEN}=== EVOCATE Sessions ===${NC}"
    echo ""

    local sessions=$(tmux ls 2>/dev/null | grep "^evocate-" || true)

    if [[ -z "$sessions" ]]; then
        echo "No active evocate sessions"
    else
        echo "Active sessions:"
        echo "$sessions"
    fi

    echo ""
    echo "Results files:"
    local results_count=$(ls -1 "$EVOCATE_DIR"/results-*.md 2>/dev/null | wc -l)
    if [[ $results_count -gt 0 ]]; then
        ls -lt "$EVOCATE_DIR"/results-*.md 2>/dev/null | head -10
        echo ""
        echo "Total: $results_count results file(s)"
    else
        echo "  No results files"
    fi
}

# Cleanup files
cmd_cleanup() {
    local session_id="$1"

    if [[ -n "$session_id" ]]; then
        # Cleanup specific session
        echo -e "${YELLOW}Cleaning up session: $session_id${NC}"

        # Kill if still running
        if tmux has-session -t "$session_id" 2>/dev/null; then
            echo "Session still running, killing..."
            tmux kill-session -t "$session_id"
        fi

        # Remove all files for this session
        rm -f "$EVOCATE_DIR/task-"*"${session_id##evocate-}"*.md 2>/dev/null
        rm -f "$EVOCATE_DIR/log-${session_id}.txt" 2>/dev/null
        rm -f "$EVOCATE_DIR/run-${session_id}.sh" 2>/dev/null
        rm -f "$EVOCATE_DIR/results-${session_id}.md" 2>/dev/null

        echo -e "${GREEN}Session $session_id cleaned up.${NC}"
    else
        # Cleanup all old files
        echo -e "${YELLOW}Cleaning up old evocate files (older than 24h)...${NC}"

        local count_before=$(ls -1 "$EVOCATE_DIR"/* 2>/dev/null | wc -l)

        # Remove files older than 24 hours
        find "$EVOCATE_DIR" -name "*.md" -mtime +1 -delete 2>/dev/null
        find "$EVOCATE_DIR" -name "*.txt" -mtime +1 -delete 2>/dev/null
        find "$EVOCATE_DIR" -name "run-*.sh" -mtime +1 -delete 2>/dev/null
        find "$EVOCATE_DIR" -name "task-*.md" -mtime +1 -delete 2>/dev/null

        local count_after=$(ls -1 "$EVOCATE_DIR"/* 2>/dev/null | wc -l)

        echo -e "${GREEN}Cleanup complete${NC}"
        echo "  Files before: $count_before"
        echo "  Files after: $count_after"
        echo "  Removed: $((count_before - count_after))"
    fi
}

# Main command router
case "$1" in
    launch)
        cmd_launch "$2" "$3"
        ;;
    status)
        cmd_status "$2"
        ;;
    results)
        cmd_results "$2" "$3"
        ;;
    kill)
        cmd_kill "$2"
        ;;
    list)
        cmd_list
        ;;
    cleanup)
        cmd_cleanup "$2"
        ;;
    *)
        usage
        ;;
esac
