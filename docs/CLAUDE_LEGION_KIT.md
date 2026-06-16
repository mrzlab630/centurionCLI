# Claude Legion Kit

`integrations/claude-legion-kit` is the permanent CENTURION integration pack for Claude Code CLI.

It exists because Claude Code has native extension points that should be used directly instead of relying on prompt text alone: plugins, skills, subagents, session agents, tool allow/deny lists, permission modes, MCP config controls, safe/bare modes, and plugin validation.

## Source Of Truth

- Repository kit: `integrations/claude-legion-kit`
- Installed plugin target: `~/.claude/skills/centurion-legion`
- Canonical Legion skills: `skills/` in this repository and installed `~/.agents/skills`
- Existing Claude global config: `~/.claude/settings.json`, `~/.claude/settings.local.json`, `~/.claude.json`

The kit does not commit or print secrets. It deliberately does not rewrite Claude settings files; those contain host-local credentials, MCP definitions, project history, and permission state.

## Local Audit Summary

- `claude --version` reported `2.1.177 (Claude Code)`.
- `claude --help` confirmed `--agent`, `--agents`, `--allowedTools`, `--disallowedTools`, `--tools`, `--permission-mode`, `--mcp-config`, `--strict-mcp-config`, `--plugin-dir`, `--settings`, `--system-prompt`, `--json-schema`, `--safe-mode`, and `--bare`.
- `claude agents --help` confirmed default model, effort, permission mode, settings, MCP config, plugin dir, and strict MCP config controls for dispatched sessions.
- `claude plugin init --with skills agents hooks mcp output-style channel` confirmed the on-disk plugin shape.
- `claude plugin validate --strict` is the validation gate for plugin shape.
- `claude mcp list` showed the current MCP fleet connected: context7, brave-search, playwright, sequential-thinking, solanaMcp, memoria, and github.
- Existing `~/.claude/skills` had 27 Legion skills, while current Cohors Secunda has 37 canonical skills. The installer syncs the current repository surface when requested.
- Live `claude -p` execution on this workstation uses local `cli-proxy-api` at `http://127.0.0.1:8317`. If print-mode returns `Not logged in`, treat that as a missing proxy environment first: set `ANTHROPIC_BASE_URL`, set a proxy `ANTHROPIC_API_KEY` placeholder, and keep `NO_PROXY=127.0.0.1,localhost`.

## Design

The plugin uses two layers:

1. `centurion-legion` root skill: routing doctrine, one-owner contract, WAR ROOM, and `CLAUDE_ORDER v1` rules.
2. `agents/*.md`: one Claude Code subagent per Legionary. Each agent is scoped to one specialty and must hand back if adjacent skills are required.

This avoids duplicate ownership. It also lets Claude Code use its native `--agent <slug>` control when a controller wants one owner for a session.

Opus 4.8 does not change the ownership model. The kit uses it through compact references and deterministic guards: CURATOR prepares dossiers, TESTER plans frontend acceptance sweeps, GUARDIAN scans external skill candidates, and REVIEWER verifies completion claims before acceptance.

## Obedience Strategy

Prompt text is advisory. Enforcement comes from combining:

- exact owner: `--agent <slug>` or plugin subagent routing;
- exact tools: `--allowedTools`, `--disallowedTools`, or `--tools`;
- permission mode: `plan`, `default`, or `acceptEdits`, never defaulting to bypass;
- MCP minimization: `--mcp-config` plus `--strict-mcp-config`;
- structured result: `CLAUDE_RESULT.json` or `--json-schema` for print-mode pure output tasks;
- filesystem guard: `scripts/claude-order-guard.mjs` snapshot and verify;
- owner review: direct diff/artifact inspection plus rerun proof.

For long print-mode orders, pass the prompt through stdin. `--allowedTools` and similar options accept variable-length values, so stdin avoids the prompt being interpreted as another tool rule.

The repository includes `integrations/claude-legion-kit/scripts/proxy-env.sh.example` with the current proxy defaults for non-interactive tests.

`CLAUDE_ORDER v1` remains the Claude Code protocol. Its `CLAUDE_RESULT.json` shape is also validated through the shared Legion contract layer as a legacy result payload; see [LEGION_CONTRACTS.md](LEGION_CONTRACTS.md). The shared validator does not replace `claude-order-guard.mjs`, because the guard owns workspace snapshots, changed-file policy, forbidden-pattern checks, and Claude-specific strictness.

## Maintenance

Run before changing the kit:

```bash
cd integrations/claude-legion-kit
node --check installer/install.mjs
node --check scripts/smoke.mjs
node --check scripts/claude-order-guard.mjs
node --check scripts/claude-surface-audit.mjs
node --check scripts/external-skill-scan.mjs
node --check scripts/frontend-sweep-plan.mjs
claude plugin validate ./plugin --strict
npm run audit:surface
npm run smoke
```

`npm run audit:surface` proves the Claude surface is still one-owner: 37 canonical skills, 37 plugin agents, no high-overlap role descriptions, routing eval coverage for every Legionary, installed plugin drift checks, installed standalone skill drift checks, and loaded-plugin validation.

Additional guard commands are intentionally owner-scoped:

- `npm run scan:external-skill -- <candidate-dir>`: GUARDIAN gate for local external skills/plugins before install or adaptation.
- `npm run plan:frontend-sweep -- --workspace <dir> --base-url <url>`: TESTER plan for frontend proof; fixes still route to PICTOR and adjacent Product/UX owners.

When canonical Legion skills change, regenerate or update `plugin/agents/*.md` so every skill still has exactly one Claude subagent, then rerun `npm run audit:surface` before installing or accepting the change.
