# CLI Tool UI Patterns — AEDILIS Reference

## Output Formatting

### Colors (ANSI)
```
Red      — Errors, failures, destructive
Green    — Success, confirmation, positive values
Yellow   — Warnings, caution, pending
Blue     — Info, links, highlights
Cyan     — Secondary info, prompts
Gray     — Muted text, metadata, timestamps
Bold     — Headers, important values
Dim      — De-emphasized, optional info
```

**Rule:** ALWAYS respect `NO_COLOR` env variable. If set, output plain text only.
```bash
if [ -n "$NO_COLOR" ]; then
  # No ANSI codes
fi
```

### Tables
```
┌──────────┬─────────┬────────┐
│ Name     │ Status  │ Memory │
├──────────┼─────────┼────────┤
│ bot      │ online  │ 45 MB  │
│ tracker  │ stopped │ 0 MB   │
└──────────┴─────────┴────────┘
```

Libraries: `cli-table3` (Node), `tabulate` (Python), `tabled` (Rust)

### Progress Indicators
```
Spinner:    ⠋ Processing...  (for indeterminate operations)
Bar:        [████████░░░░░░░░] 53% (12/23)  (for determinate)
Dots:       Connecting...  (simple, low-overhead)
```

Libraries: `ora` / `cli-spinners` (Node), `tqdm` / `rich` (Python)

### Tree View
```
project/
├── src/
│   ├── index.ts
│   └── utils/
│       ├── format.ts
│       └── parse.ts
├── tests/
│   └── index.test.ts
└── package.json
```

### Status Output
```
✓ Database connected (23ms)
✓ Redis connected (5ms)
✗ Solana node unreachable (timeout 5000ms)
⚠ Disk usage at 87% (warn threshold: 80%)
```

## Interactive Patterns

### Prompts
```
? Select environment: (Use arrow keys)
❯ development
  staging
  production
```

Libraries: `inquirer` / `prompts` (Node), `questionary` (Python)

### Confirmation
```
? Delete 23 files? This cannot be undone. (y/N)
```
- Default answer: capitalize it (N = default No)
- Destructive actions: require explicit "yes", not just Enter

### Multi-Select
```
? Select features to enable: (Space to select, Enter to confirm)
 ◉ Copy-trading
 ◯ Paper trading
 ◉ Notifications
 ◯ Auto-buy
```

## Error Output

### Good
```
Error: Cannot connect to database at localhost:5432
  Reason: Connection refused
  Try: 1. Check if PostgreSQL is running: pg_isready
       2. Verify connection string in .env
       3. Run: sudo systemctl start postgresql
```

### Bad
```
Error: ECONNREFUSED
```

### Rules
- Error message: WHAT failed
- Reason: WHY it failed (if known)
- Suggestion: HOW to fix it (actionable steps)
- Error code: for programmatic handling
- stderr for errors, stdout for normal output

## Argument Conventions

### Standard Flags
```
-h, --help        Show help text
-v, --version     Show version
-q, --quiet       Suppress output
-V, --verbose     Increase output detail
    --json        Machine-readable JSON output
    --no-color    Disable color output
    --dry-run     Show what would be done without doing it
-y, --yes         Skip confirmations
```

### Subcommand Pattern
```
tool <command> [options] [arguments]

tool wallet list                    # List wallets
tool wallet create --name "Main"    # Create wallet
tool wallet delete <id> --force     # Delete wallet
```

## JSON Output Mode

When `--json` is specified:
- Output ONLY valid JSON to stdout
- Progress/logs go to stderr
- Exit code: 0 = success, 1 = error
- Error JSON: `{"error": "message", "code": "ERR_CODE"}`
- Success JSON: `{"data": {...}, "meta": {"timestamp": "..."}}`

## Help Text Layout

```
Usage: tool <command> [options]

Commands:
  list      List all items
  create    Create new item
  delete    Delete an item

Options:
  -h, --help       Show this help message
  -v, --version    Show version number
  --json           Output as JSON
  -q, --quiet      Suppress non-essential output

Examples:
  tool list --json
  tool create --name "Example"
  tool delete abc123 --force

Documentation: https://docs.example.com
```

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | General error |
| 2 | Misuse of command (wrong args) |
| 126 | Permission denied |
| 127 | Command not found |
| 130 | Interrupted (Ctrl+C) |

## Man Page / Help Priority
1. `--help` flag (always available, concise)
2. Subcommand help: `tool help <command>`
3. Examples section in help text (most useful)
4. Long-form documentation (README, website)
