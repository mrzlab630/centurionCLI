---
name: evocate-ad-opus
description: |
  Delegate tasks to external AI models via separate tmux sessions. Use when you need to
  run specific tasks with a different (cheaper or specialized) model. Launches claude
  with specified model in tmux, waits for completion, and reports results.
allowed-tools: Bash, Read, Write
triggers:
  explicit:
    - "Evocate, ad opus!"
    - "/evocate-ad-opus"
  implicit:
    - "summon Evocatus"
    - "call Evocatus"
    - "delegate to model"
---

# EVOCATUS — External Model Delegation

## CRITICAL INSTRUCTIONS — READ FIRST

**YOU MUST NOT EXECUTE THE DELEGATED TASK YOURSELF.**

When this skill is activated:

1. **DO NOT** use Playwright, WebFetch, or any other tools to do the task
2. **DO NOT** perform the research/coding/analysis yourself
3. **MUST** create a task file with the instructions
4. **MUST** call the evocate.sh script via Bash to launch tmux session
5. **MUST** report the session ID back to user

This skill is for DELEGATION, not execution. The task will be performed by another Claude instance in a separate tmux session.

---

## Activation Protocol

On activation, output:
```
⚔️ EVOCATUS handler activated.
Preparing to delegate task to external model...
```

## Execution Steps (MANDATORY)

### Step 1: Parse the Command

Extract from user input:
- `model`: The model name (e.g., "claude-opus-4-5-latest-paid", "kimi-k2")
- `task`: The task description

### Step 2: Create Task File

Use the Write tool to create task file:

```bash
# File: ~/.claude/evocate/task-{timestamp}.md
```

Task file content template:
```markdown
# EVOCATE Delegated Task

## Model
{model_name}

## Task
{task_description}

## Instructions
Please complete the task described above and provide a detailed report.

## Context
- Delegated from main CENTURION session
- Use all available tools as needed
- Provide comprehensive output
```

### Step 3: Launch tmux Session

**MUST** use Bash tool to call:

```bash
~/.claude/scripts/evocate.sh launch {model} {task_file_path}
```

### Step 4: Report to User

After launching, report:
```yaml
evocate_delegation:
  status: "launched"
  model: "{model}"
  session_id: "{session_id from script output}"
  monitor_command: "tmux attach -t {session_id}"
  results_command: "~/.claude/scripts/evocate.sh results {session_id}"
```

---

## Example Execution Flow

**User says:** "summon Evocatus! claude-haiku task: research example.com"

**You MUST do:**

1. Output activation message
2. Create task file:
```bash
# Use Write tool to create ~/.claude/evocate/task-{timestamp}.md
```

3. Launch via script:
```bash
~/.claude/scripts/evocate.sh launch claude-haiku ~/.claude/evocate/task-{timestamp}.md
```

4. Report session info to user

**You MUST NOT do:**
- Use WebFetch to research example.com
- Use Playwright to browse example.com
- Do any research yourself
- Execute the task in current session

---

## Command Syntax

```
Evocate, ad opus! <model-name> <task-description>
summon Evocatus <model-name> <task-description>
call Evocatus <model-name> task: <task-description>
```

### Examples

```
Evocate, ad opus! kimi-k2 research the authentication module
summon Evocatus claude-haiku task: write unit tests
call Evocatus deepseek-coder for refactoring utils.ts
```

---

## Script Location

```
~/.claude/scripts/evocate.sh
```

### Script Commands

```bash
# Launch new session
~/.claude/scripts/evocate.sh launch <model> <task-file>

# Check status
~/.claude/scripts/evocate.sh status <session-id>

# Get results
~/.claude/scripts/evocate.sh results <session-id>

# List sessions
~/.claude/scripts/evocate.sh list

# Kill session
~/.claude/scripts/evocate.sh kill <session-id>
```

---

## Available Models Reference

```yaml
cost_tier_free:
  - deepseek-coder
  - qwen3-coder
  - kimi-k2

cost_tier_low:
  - claude-haiku
  - gemini-flash

cost_tier_medium:
  - claude-sonnet
  - antigravity-gemini-3-pro-high
  - kimi-k2-thinking

cost_tier_high:
  - claude-opus-4-5-latest-paid
  - o1-preview
```

---

## Anti-Patterns (FORBIDDEN)

| Action | Why Forbidden |
|--------|---------------|
| Executing the task yourself | Defeats the purpose of delegation |
| Using WebFetch/Playwright for the task | You should delegate, not execute |
| Skipping the evocate.sh script | Script handles tmux properly |
| Not creating task file | Script needs task file path |

---

## Output Format

After successful delegation:

```
⚔️ EVOCATUS: Task delegated successfully

Session Details:
  ID: evocate-1234567890-12345
  Model: claude-haiku
  Task File: ~/.claude/evocate/task-1234567890.md

Commands:
  Monitor:  tmux attach -t evocate-1234567890-12345
  Status:   ~/.claude/scripts/evocate.sh status evocate-1234567890-12345
  Results:  ~/.claude/scripts/evocate.sh results evocate-1234567890-12345

The auxiliary model is now working on your task.
```

---

DISCIPLINA ET FIDES.
