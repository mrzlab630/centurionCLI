#!/bin/bash
#
# EVOCATE — External Model Delegation Script
# Part of CENTURION COHORS PRIMA
#
# Usage:
#   evocate.sh launch <model> <task-file>
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
    echo "  $SCRIPT_NAME launch <model> <task-file>   Launch new evocate session"
    echo "  $SCRIPT_NAME status <session-id>          Check session status"
    echo "  $SCRIPT_NAME results <session-id>         Get session results"
    echo "  $SCRIPT_NAME kill <session-id>            Kill session"
    echo "  $SCRIPT_NAME list                         List active sessions"
    echo "  $SCRIPT_NAME cleanup [session-id]         Clean temp files (all or specific)"
    echo ""
    echo "Examples:"
    echo "  $SCRIPT_NAME launch kimi-k2 ~/.claude/evocate/task-001.md"
    echo "  $SCRIPT_NAME status evocate-1705312345"
    echo "  $SCRIPT_NAME results evocate-1705312345"
    echo "  $SCRIPT_NAME cleanup evocate-1705312345"
    echo "  $SCRIPT_NAME list"
}

# Generate unique session ID
generate_session_id() {
    echo "evocate-$(date +%s)-$$"
}

# Launch new evocate session
cmd_launch() {
    local model="$1"
    local task_file="$2"

    if [[ -z "$model" ]] || [[ -z "$task_file" ]]; then
        echo -e "${RED}Error: Missing arguments${NC}"
        echo "Usage: $SCRIPT_NAME launch <model> <task-file>"
        exit 1
    fi

    if [[ ! -f "$task_file" ]]; then
        echo -e "${RED}Error: Task file not found: $task_file${NC}"
        exit 1
    fi

    local session_id=$(generate_session_id)
    local results_file="$EVOCATE_DIR/results-${session_id}.md"
    local log_file="$EVOCATE_DIR/log-${session_id}.txt"
    local wrapper_script="$EVOCATE_DIR/run-${session_id}.sh"

    # Create results file placeholder
    cat > "$results_file" << EOF
# EVOCATE Results
## Session: $session_id
## Model: $model
## Status: RUNNING
## Started: $(date -Iseconds)
## Task File: $task_file

---

EOF

    # Create wrapper script (avoids escaping issues)
    # Note: Using 'WRAPPER_EOF' (quoted) to prevent variable expansion
    cat > "$wrapper_script" << 'WRAPPER_EOF'
#!/bin/bash
# Auto-generated EVOCATE wrapper script

SESSION_ID="__SESSION_ID__"
MODEL="__MODEL__"
TASK_FILE="__TASK_FILE__"
LOG_FILE="__LOG_FILE__"
RESULTS_FILE="__RESULTS_FILE__"
WRAPPER_SCRIPT="__WRAPPER_SCRIPT__"
EVOCATE_DIR="__EVOCATE_DIR__"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  EVOCATE Session: $SESSION_ID"
echo "║  Model: $MODEL"
echo "║  Task: $TASK_FILE"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Run claude with task file content via stdin pipe
# This avoids all escaping issues with special characters
echo "Starting claude with model: $MODEL"
echo "---"
echo ""

cat "$TASK_FILE" | claude --model "$MODEL" --print 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=$?

echo ""
echo "---"
echo "Session completed with exit code: $EXIT_CODE"
echo ""

# Update results file with output
{
    echo ""
    echo "## Completed: $(date -Iseconds)"
    echo "## Exit Code: $EXIT_CODE"
    echo ""
    echo "### Output:"
    echo '```'
    cat "$LOG_FILE"
    echo '```'
} >> "$RESULTS_FILE"

# Mark as complete
sed -i 's/Status: RUNNING/Status: COMPLETE/' "$RESULTS_FILE"

echo ""
echo "Results saved to: $RESULTS_FILE"
echo ""

# Auto-cleanup temporary files (keep only results)
echo "Cleaning up temporary files..."
rm -f "$TASK_FILE" 2>/dev/null
rm -f "$LOG_FILE" 2>/dev/null
rm -f "$WRAPPER_SCRIPT" 2>/dev/null
echo "Cleanup complete."
echo ""
echo "Session $SESSION_ID finished. Tmux will close automatically."

# Small delay so user can see the message if attached
sleep 2

# Session ends here - tmux will auto-close
WRAPPER_EOF

    # Replace placeholders in wrapper script
    sed -i "s|__SESSION_ID__|$session_id|g" "$wrapper_script"
    sed -i "s|__MODEL__|$model|g" "$wrapper_script"
    sed -i "s|__TASK_FILE__|$task_file|g" "$wrapper_script"
    sed -i "s|__LOG_FILE__|$log_file|g" "$wrapper_script"
    sed -i "s|__RESULTS_FILE__|$results_file|g" "$wrapper_script"
    sed -i "s|__WRAPPER_SCRIPT__|$wrapper_script|g" "$wrapper_script"
    sed -i "s|__EVOCATE_DIR__|$EVOCATE_DIR|g" "$wrapper_script"

    # Make wrapper executable
    chmod +x "$wrapper_script"

    echo -e "${GREEN}⚔️ EVOCATE: Launching auxiliary session${NC}"
    echo -e "  Session: ${BLUE}$session_id${NC}"
    echo -e "  Model:   ${YELLOW}$model${NC}"
    echo -e "  Task:    $task_file"
    echo -e "  Results: $results_file"
    echo ""

    # Launch tmux session with wrapper script
    tmux new-session -d -s "$session_id" "$wrapper_script"

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}Session launched successfully${NC}"
        echo ""
        echo "Commands:"
        echo "  View:    tmux attach -t $session_id"
        echo "  Status:  $SCRIPT_NAME status $session_id"
        echo "  Results: $SCRIPT_NAME results $session_id"
        echo "  Kill:    $SCRIPT_NAME kill $session_id"
        echo ""
        echo -e "${YELLOW}Note: Session will auto-close after completion.${NC}"
        echo -e "${YELLOW}      Temp files will be auto-deleted. Only results file remains.${NC}"

        # Output machine-readable info
        echo ""
        echo "---"
        echo "session_id: $session_id"
        echo "model: $model"
        echo "results_file: $results_file"
    else
        echo -e "${RED}Failed to launch session${NC}"
        rm -f "$wrapper_script"
        exit 1
    fi
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
