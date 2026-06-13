# Claude Legion Kit

Portable CENTURION integration for Claude Code CLI.

This kit installs a Claude Code plugin with one CENTURION entry skill, 37 Legionary subagents generated from the canonical repository skill surface, and a `CLAUDE_ORDER v1` guard for bounded implementation work.

## Observed Local Baseline

- Claude CLI: `Claude Code 2.1.177` from `/home/mrz/.local/bin/claude`.
- Local model access uses `cli-proxy-api` on `http://127.0.0.1:8317`; non-interactive shells may not inherit this from `~/.bashrc` because that file returns early when not interactive.
- Native control surfaces confirmed by `claude --help`: `--agent`, `--agents`, `--allowedTools`, `--disallowedTools`, `--tools`, `--permission-mode`, `--mcp-config`, `--strict-mcp-config`, `--plugin-dir`, `--settings`, `--system-prompt`, `--json-schema`, `--safe-mode`, and `--bare`.
- Claude Code supports plugin scaffolding and validation via `claude plugin init` and `claude plugin validate`.
- Local `~/.claude/skills` existed but held an older Legion surface than the current 37-skill Cohors Secunda repository surface.
- Existing MCP servers were connected during audit: context7, brave-search, playwright, sequential-thinking, solanaMcp, memoria, and github.

Secrets were not copied into this kit. The installer does not edit `~/.claude/settings.json`, `~/.claude/settings.local.json`, or `~/.claude.json`.

## What It Installs

- `plugin/.claude-plugin/plugin.json`: Claude Code plugin manifest.
- `plugin/SKILL.md`: CENTURION entrypoint skill for routing and proof discipline.
- `plugin/agents/*.md`: 37 Claude Code subagents, one per Legionary owner.
- `plugin/skills/claude-order/SKILL.md`: `CLAUDE_ORDER v1` protocol.
- `plugin/output-styles/centurion-legion.md`: proof-first output style for plugin sessions.
- `scripts/claude-order-guard.mjs`: snapshot and verify guard for bounded Claude execution.
- `installer/install.mjs`: installs the plugin and optionally syncs canonical repository skills to `~/.claude/skills`.

## Quick Start

```bash
cd integrations/claude-legion-kit
node ./scripts/smoke.mjs
node ./installer/install.mjs --dry-run
node ./installer/install.mjs
claude plugin validate /home/mrz/.claude/skills/centurion-legion --strict
```

To install into a temporary Claude home for validation:

```bash
node ./installer/install.mjs --claude-home /tmp/claude-home-test
```

To install only the plugin and leave existing `~/.claude/skills/<legionary>` directories untouched:

```bash
node ./installer/install.mjs --no-skill-sync
```

## CLAUDE_ORDER v1

Use `CLAUDE_ORDER v1` when Claude Code is delegated a bounded implementation slice.

```bash
node integrations/claude-legion-kit/scripts/claude-order-guard.mjs snapshot \
  --workspace <dir> \
  --out /tmp/claude-before.json
```

Then run Claude with the smallest practical tool surface. On this workstation, print-mode live tests should use the local Claude proxy environment instead of the OAuth login path:

```bash
source integrations/claude-legion-kit/scripts/proxy-env.sh.example
claude -p 'Say OK only.'
```

If `claude -p` returns `Not logged in`, first confirm that `ANTHROPIC_BASE_URL` points at the local proxy and `ANTHROPIC_API_KEY` is set for the proxy session. That error can mean the proxy env was not present, not that Claude Code is misconfigured.

For long orders, pass the prompt through stdin so variadic tool options cannot consume the prompt text:

```bash
claude -p \
  --agent pictor \
  --permission-mode default \
  --allowedTools 'Read,Grep,Edit,Write,Bash(npm test)' \
  < /tmp/claude-order-prompt.txt
```

Include `Write` whenever the order requires `CLAUDE_RESULT.json` or any newly created file. If the tool surface omits `Write`, Claude may edit existing files but fail to produce the required result artifact.

For planning-only work:

```bash
claude -p \
  --agent orchestrator \
  --permission-mode plan \
  --tools 'Read,Grep' \
  '<planning prompt>'
```

Verify before accepting:

```bash
node integrations/claude-legion-kit/scripts/claude-order-guard.mjs verify \
  --workspace <dir> \
  --before /tmp/claude-before.json \
  --allowed <paths> \
  --result CLAUDE_RESULT.json \
  --forbidden <patterns>
```

Never accept Claude stdout, narration, or confidence alone. Accept only after guard verification, owner proof, and direct diff or artifact inspection.

Live proxy testing showed that short bounded orders can pass end to end, while longer print-mode orders may edit files and then hit the controller timeout before clean stdout. Treat timeout, missing result files, `proof` values other than `passed`, or partial artifacts as rejection conditions. Retry with a smaller order instead of accepting partial work.

## WAR ROOM Verdict

**Prosecutor:** Prompt-only obedience is fragile. Claude can drift through broad tools, old skills, permissive settings, MCP access, or self-reported success. A 27-skill `~/.claude/skills` surface conflicts with the current 37-owner repository surface.

**Advocate:** Claude Code has better native control surfaces than a plain chat model: plugin agents, session `--agent`, explicit tool gates, permission modes, strict MCP config, structured output schema, and plugin validation.

**Judge:** The winning design is a reproducible plugin plus guard protocol. Use native Claude Code controls for prevention and `claude-order-guard.mjs` for acceptance. Keep one owner per task and sync the Claude skill surface from the canonical repository, not by hand.

## Security Rules

- Do not store secrets in this kit.
- Do not widen global Claude permissions from the installer.
- Do not enable `--dangerously-skip-permissions` or `bypassPermissions` as a default.
- Do not delegate production deploys, destructive commands, wallet/payment/KYC flows, exploit execution, or final architecture/security/legal/product-risk judgment without explicit target, owner, and proof gate.
- Use `--strict-mcp-config` for bounded sessions that need MCP access.
- Use `--safe-mode` or `--bare` to isolate broken or overactive customizations while debugging Claude Code behavior.

## Validation

```bash
node --check installer/install.mjs
node --check scripts/smoke.mjs
node --check scripts/claude-order-guard.mjs
claude plugin validate ./plugin --strict
npm run smoke
```

The smoke check validates the plugin manifest, root skill, `claude-order` skill, output style, 37 generated subagents, canonical skill surface, installer dry target, and `CLAUDE_ORDER v1` guard pass/fail behavior.
