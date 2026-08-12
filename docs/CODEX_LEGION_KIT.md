# Codex Legion Kit

`integrations/codex-legion-kit` is the CENTURION maintenance pack for Codex CLI itself.

It exists to prevent the failure mode where repository Legion skills are updated but the active Codex surface in `~/.agents/skills` stays stale.

## Source Of Truth

- Repository skills: `skills/`
- Active Codex Legion skills: `~/.agents/skills`
- Codex user config: `~/.codex/config.toml`
- Codex memories: `~/.codex/memories/`
- Codex custom agents: `~/.codex/agents/*.toml`
- Codex hooks: `~/.codex/hooks.json` or hooks configured in active config layers

Required team rules still belong in `AGENTS.md`, checked-in docs, and skills. Memories are a recall layer, not the source of mandatory behavior.

`open-design-producer` is a shared capability outside the 37 Legionary owners.
The installer places it under `~/.agents/skills`, writes
`$CODEX_HOME/centurion/open-design-bridge.json`, and registers the local
`centurion-open-design` stdio MCP through `codex mcp add`.

## Current Host Baseline

This 2026-07-09 baseline is sanitized from read-only local checks. Do not copy
`~/.codex/config.toml`, raw memories, provider credentials, permissions state,
or trusted project lists into this repository.

- `codex --version` reported `codex-cli 0.146.0`.
- Default model: `gpt-5.6-sol`.
- Model provider: `cliproxyapi`.
- Reasoning effort: `xhigh`.
- Personality: `pragmatic`.
- Local provider endpoint: `http://127.0.0.1:8317/v1` using the Responses wire API.
- `features.memories = true` is enabled; memories remain a recall layer and are not copied into the repo.
- `features.multi_agent_v2.enabled = true` is enabled with spawn-agent metadata hidden.
- No `~/.codex/agents` directory was present in the sanitized baseline.
- No `~/.codex/hooks.json` was present in the sanitized baseline.
- Installed `~/.codex/skills` entries observed: `.system`, `camofox-browser`, and `migrate-to-codex`.
- Optional Camofox skill is installed under `~/.codex/skills/camofox-browser` with implicit invocation disabled. It uses the local REST server at `http://127.0.0.1:9377` only when explicitly invoked.

## Maintenance Commands

```bash
cd integrations/codex-legion-kit
node --check scripts/lib/surface-config.mjs
node --check scripts/codex-surface-audit.mjs
node --check scripts/sync-agents.mjs
node --check scripts/smoke.mjs
npm run audit:surface
npm run smoke
npm run install:open-design:dry-run
npm run install:open-design
```

Optional Camofox proof:

```bash
node /home/mrz/.codex/skills/camofox-browser/scripts/camofox-smoke.mjs --health --json
node /home/mrz/.codex/skills/camofox-browser/scripts/camofox-smoke.mjs --screenshot /tmp/camofox-example.png https://example.com/
```

Run Camofox checks sequentially. On this host, parallel tab creation can time out even when the server remains healthy.

`npm run audit:surface` checks:

- canonical repository skill count and required guard pointers;
- active `~/.agents/skills` count and drift from repository `skills/`;
- Codex model and reasoning baseline;
- memory feature baseline;
- custom agents, hooks, personal plugin marketplace presence;
- broad MCP and inline secret-like config warnings.

The drift check compares the durable skill surface: `SKILL.md`, references,
scripts, package manifests, and other checked-in skill files. It intentionally
ignores generated local artifacts such as `node_modules`, build output,
coverage output, virtual environments, vendored dependency trees, and runtime
`reports/` written by helper scripts.

Audit and sync keep 37 owners canonical while checking the shared Open Design
capability separately. Smoke installs the capability into temporary Codex and
Agents homes and verifies its MCP entry. Audit, sync, and smoke share the canonical skill list and generated-artifact
ignore rules from `scripts/lib/surface-config.mjs`. Skill content still lives in
`skills/`; when adding or removing a Legion skill, update that shared config in
the same change.

Codex uses the shared Legion JSON contract layer for bounded delegation artifacts where a result must be machine-validated. See [LEGION_CONTRACTS.md](LEGION_CONTRACTS.md). This does not create Codex-specific Legionary owners; it only standardizes `LEGION_ORDER_V1`, `LEGION_RESULT_V1`, and `LEGION_REVIEW_V1` validation for handoffs that already have one primary owner.

To repair active skill drift after reviewing the audit:

```bash
npm run sync:agents -- --write
npm run audit:surface
```

## GitHub Research Intake

GitHub skill/plugin repositories are idea sources until they pass GUARDIAN review. Do not bulk-install large packs.

High-value patterns found during research:

- `openai/skills`: official skill catalog and curated/system layout.
- `openai/role-specific-plugins`: Codex-native role plugin structure with `.codex-plugin`, skills, references, scripts, templates, assets, and marketplace metadata.
- `openai/codex-action`: PR and CI review integration pattern.
- `openai/codex-plugin-cc`: delegation bridge pattern.
- `vercel-labs/agent-skills`: frontend, React, web-design, and writing guard references.
- `obra/superpowers`: verification-before-completion, TDD, subagent-driven development, and trigger-test patterns.
- `agentskills/agentskills`: Agent Skills specification baseline.

Adoption rule: extract small protocols or deterministic checks into existing Legionaries. Do not add new owners unless a capability gap remains after local routing and the user approves it.

## Planned Next Layer

The next useful layer is optional and should stay small:

- repo-local or user-local Codex custom agents only for bounded read-heavy lanes;
- warning-only hooks for Stop/PostToolUse checks, trusted after review;
- a Codex plugin wrapper only after the current CLI exposes a reliable local validation/install flow for the target shape.

## Open Design workflow

Use MCP `search_design_references`, select reference IDs, then call
`start_design`. Poll `get_design` every 30-60 seconds. Inspect the returned HTML,
screenshot, proof, and accepted reference manifest. For a revision, pass
the durable `resultPath` from `.results` as `project.previousResultPath`; set `orchestrator.client="codex"`
and keep the responsible Legionary under `orchestrator.owner`.

## Optional Camofox Browser

`integrations/codex-legion-kit/skills/camofox-browser` versions the local opt-in Camofox skill. It is not a global MCP server and does not replace `playwright` or `chrome-devtools` MCP.

Use it only for public web pages where normal browser tools are blocked or fingerprinted, or when independent Camofox screenshot/snapshot proof is useful. Do not use it for authenticated sites, cookie import, secrets, or arbitrary page JavaScript without explicit approval.
