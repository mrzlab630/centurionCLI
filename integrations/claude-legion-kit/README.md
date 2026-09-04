# Claude Legion Kit

Portable CENTURION integration for Claude Code CLI.

Current kit version: `0.4.1`.

This kit installs a Claude Code plugin with one CENTURION entry skill, 37 Legionary subagents, the shared `open-design-producer` capability, and a `CLAUDE_ORDER v1` guard for bounded implementation work.

The namespaced `CLAUDE_RESULT.json` uses canonical `AGENT_RESULT_JSON_V1` by default and is checked by the kit-local standalone validator. The guard owns snapshot, changed-file, and forbidden-pattern enforcement; no sibling kit is required at runtime.

## Observed Local Baseline

- Sanitized baseline date: 2026-07-09. Raw Claude settings, OAuth state, credentials, project history, permission allowlists, and machine identifiers are intentionally not copied into this repository.
- Claude CLI: `2.1.204 (Claude Code)`.
- Default model baseline: `claude-opus-5`.
- Local model access uses the proxy default `http://127.0.0.1:8317`; non-interactive shells may not inherit this from `~/.bashrc` because that file returns early when not interactive.
- Native control surfaces confirmed by `claude --help`: `--agent`, `--agents`, `--allowedTools`, `--disallowedTools`, `--tools`, `--permission-mode`, `--mcp-config`, `--strict-mcp-config`, `--plugin-dir`, `--settings`, `--system-prompt`, `--json-schema`, `--safe-mode`, and `--bare`.
- Claude Code supports plugin scaffolding and validation via `claude plugin init` and `claude plugin validate`.
- Installed `~/.claude/skills` entries include `centurion-legion` plus all 37 Legionaries from the Cohors Secunda repository surface.
- MCP servers observed in sanitized settings include solanaMcp, brave-search, context7, playwright, sequential-thinking, memoria, github, and serena where present in host-level Claude JSON.
- `~/.claude/plugins` exists with installed plugin metadata; raw registry details are not copied.
- No `~/.claude/agents` directory was present in the sanitized baseline.
- Non-interactive proxy defaults remain `ANTHROPIC_BASE_URL=http://127.0.0.1:8317`, placeholder `ANTHROPIC_API_KEY`, default opus `claude-opus-5`, default sonnet `claude-sonnet-5`, default haiku `claude-haiku-4-5-20251001`, and `NO_PROXY=127.0.0.1,localhost`.

Secrets were not copied into this kit. The installer does not edit `~/.claude/settings.json`, `~/.claude/settings.local.json`, or `~/.claude.json`.

The installer writes `~/.claude/centurion/open-design-bridge.json` with the
absolute repository bridge path. Plugin and skill trees are staged and validated
before atomic replacement; a failed validation leaves the previous trees intact.
The skill wrapper uses that file without changing Claude permissions.

## What It Installs

- `plugin/.claude-plugin/plugin.json`: Claude Code plugin manifest.
- `plugin/SKILL.md`: CENTURION entrypoint skill for routing and proof discipline.
- `plugin/agents/*.md`: 37 Claude Code subagents, one per Legionary owner.
- `skills/open-design-producer`: shared JSON-driven Open Design production with verified HTML and Chrome screenshot paths; no additional owner is created.
- `plugin/skills/claude-order/SKILL.md`: `CLAUDE_ORDER v1` protocol.
- `plugin/output-styles/centurion-legion.md`: proof-first output style for plugin sessions.
- `scripts/claude-order-guard.mjs`: snapshot and verify guard for bounded Claude execution.
- `scripts/external-skill-scan.mjs`: GUARDIAN scanner for external skill/plugin candidates.
- `scripts/frontend-sweep-plan.mjs`: TESTER-owned frontend acceptance sweep planner.
- `plugin/references/opus-5-profile.md`: compact Opus 5 operating profile for controller prompts.
- `installer/install.mjs`: installs the plugin and optionally syncs canonical repository skills to `~/.claude/skills`.

## Quick Start

```bash
cd integrations/claude-legion-kit
node ./scripts/smoke.mjs
node ./scripts/claude-surface-audit.mjs
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

Use `CLAUDE_ORDER v1` when Claude Code is delegated a bounded implementation slice. Its default result contract is canonical `AGENT_RESULT_JSON_V1` with `executor="claude"` and the exact controller `orderId`.

```bash
node integrations/claude-legion-kit/scripts/claude-order-guard.mjs snapshot \
  --workspace <dir> \
  --order-id <orderId>
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

Include `Write` whenever the order requires `<workspace>/.centurion/agents_results/<orderId>/CLAUDE_RESULT.json` or any newly created file. If the tool surface omits `Write`, Claude may edit existing files but fail to produce the required result artifact.

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
  --order-id <orderId> \
  --allowed <paths> \
  --forbidden <patterns>
```

By default the guard reads and writes only `<workspace>/.centurion/agents_results/<orderId>/CLAUDE_SNAPSHOT.json` and `<workspace>/.centurion/agents_results/<orderId>/CLAUDE_RESULT.json`. Use `--before`, `--out`, or `--result` only for another file below that exact namespace; product files stay in their declared paths.

Canonical `filesChanged` entries are `{ "path": "...", "action": "..." }` objects and list only actual product-file changes; snapshot and result control artifacts are excluded from that comparison. The previous `CLAUDE_ORDER_V1` result shape is compatibility-only and is accepted only when verify is invoked with `--allow-legacy`.

Never accept Claude stdout, narration, or confidence alone. Accept only after guard verification, owner proof, and direct diff or artifact inspection.

Live proxy testing showed that short bounded orders can pass end to end, while longer print-mode orders may edit files and then hit the controller timeout before clean stdout. Treat timeout, missing result files, canonical `proof[].status` values other than `pass`, or partial artifacts as rejection conditions. Retry with a smaller order instead of accepting partial work.

## Surface Audit

Run the Claude surface audit after changing Legion skills, plugin agents, installer behavior, or routing rules:

```bash
npm run audit:surface
```

The audit verifies 37 Legionary owners and agents separately from the shared Open Design capability, checks every agent's canonical source, enforces one-owner and handoff guardrails, covers all 37 Legionaries in routing evals, checks installed skill/config drift, and validates the loaded plugin.

For repository-only validation, use:

```bash
node ./scripts/claude-surface-audit.mjs --repo-only
```

## Opus 5 Workflow Guards

Opus 5 is treated as a stronger executor, not a reason to change the Legion shape. Keep one owner per task and load references on demand.

- CURATOR builds a compact dossier from `skills/context-optimizer/references/opus-dossier.md`; large context is reserve capacity, not the default prompt style.
- TESTER owns frontend acceptance and can plan a browser sweep with `npm run plan:frontend-sweep -- --workspace <dir> --base-url <url>`; implementation fixes go to PICTOR, UX ambiguity to AEDILIS, copy issues to NOMENCLATOR, SEO issues to INDAGATOR, and security findings to GUARDIAN.
- SKILL-QUARTERMASTER may discover external candidates, but GUARDIAN must scan local clones before install or adaptation with `npm run scan:external-skill -- <candidate-dir>`.
- REVIEWER accepts completion only after checking the diff, proof commands, changed files, integration points, and missing states against `skills/reviewer/references/completion-verification.md`.

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
node --check scripts/claude-surface-audit.mjs
node --check scripts/external-skill-scan.mjs
node --check scripts/frontend-sweep-plan.mjs
claude plugin validate ./plugin --strict
npm run audit:surface
npm run smoke
```

The smoke check validates the plugin manifest, root skill, `claude-order` skill, output style, 37 generated subagents, 38 canonical skills including the shared Open Design capability, installer config, canonical-default and explicit legacy guard behavior, installed standalone guard bytes/execution, external skill scanner behavior, and frontend sweep planner ownership.
