# Codex Legion Kit

CENTURION surface audit and synchronization guards for Codex CLI.

This kit keeps Codex aligned with the current Legion structure without adding more Legionaries. It audits the repository skill source, the active `~/.agents/skills` surface, and the host-local Codex configuration.

## Local Baseline

- Sanitized baseline date: 2026-07-09. Raw `~/.codex/config.toml`, provider credentials, memories, permission state, and trusted project lists are intentionally not copied into this repository.
- Codex CLI observed on this workstation: `codex-cli 0.146.0`.
- Current Codex model baseline: `gpt-5.6-sol` with provider `cliproxyapi`, `model_reasoning_effort = "xhigh"`, and `personality = "pragmatic"`.
- Local provider endpoint: `http://127.0.0.1:8317/v1` using the Responses wire API.
- `features.memories = true` is enabled; memories remain a recall layer and are not copied into the repo.
- `features.multi_agent_v2.enabled = true` is enabled with spawn-agent metadata hidden.
- Active Legion skill root: `~/.agents/skills`.
- Canonical repository skill root: `skills/` in this repository.
- No `~/.codex/agents` directory or `~/.codex/hooks.json` file was present in the sanitized baseline.
- Installed `~/.codex/skills` entries observed: `.system`, `camofox-browser`, and `migrate-to-codex`.
- Current Codex plugin validation is not used by this kit because this CLI version does not expose a dedicated `codex plugin validate` subcommand.

## What It Provides

- `scripts/codex-surface-audit.mjs`: read-only audit for Codex model/config, active skill drift, protocol pointers, hooks, custom agents, plugins, and MCP risk warnings.
- `scripts/sync-agents.mjs`: dry-run-first synchronization from repository `skills/` to active `~/.agents/skills`; writes only with `--write`.
- `scripts/smoke.mjs`: regression proof for audit, sync behavior, shared Legion result-contract validation, and Legion routing evals.
- `scripts/lib/surface-config.mjs`: the shared canonical skill list and generated-artifact ignore rules used by audit, sync, and smoke checks.
- `skills/camofox-browser`: optional explicit Codex skill for bounded Camofox/Camoufox browser snapshots and screenshots when normal browser tooling is blocked.

Codex uses `../legion-contracts` for neutral `LEGION_ORDER_V1`, `LEGION_RESULT_V1`, and `LEGION_REVIEW_V1` validation when a bounded delegation artifact needs machine checking. Normal discussion, research notes, and WAR ROOM reasoning stay in Markdown.

It does not install external GitHub skill packs, rewrite `~/.codex/config.toml`, or create new Legionary owners.

The Camofox skill is intentionally not an MCP server and has `allow_implicit_invocation: false`; use it explicitly only for public web pages where Playwright or Chrome DevTools are insufficient.

## Quick Start

```bash
cd integrations/codex-legion-kit
npm run audit:surface
npm run smoke
npm run sync:agents -- --json
```

If `audit:surface` reports active skill drift, inspect the report first. To sync all canonical skills intentionally:

```bash
npm run sync:agents -- --write
npm run audit:surface
```

The drift comparator ignores generated local directories such as `node_modules`, build output, coverage output, virtual environments, vendored dependency trees, and runtime `reports/`. It still compares durable skill instructions, references, scripts, and manifests.

To sync one owner:

```bash
npm run sync:agents -- --skill tester --write
```

Optional live Camofox proof, when the local PM2 server is online:

```bash
node /home/mrz/.codex/skills/camofox-browser/scripts/camofox-smoke.mjs --health --json
node /home/mrz/.codex/skills/camofox-browser/scripts/camofox-smoke.mjs --screenshot /tmp/camofox-example.png https://example.com/
```

Run those commands sequentially. Parallel Camofox tab creation can time out on this host.

## Guard Philosophy

- One task still has one primary Legionary owner.
- Codex `gpt-5.6-sol` is treated as a stronger executor, not permission to broaden roles.
- Large context is reserve capacity; CURATOR keeps dossiers compact.
- Subagents are for bounded read-heavy work and review lanes, not uncontrolled write fan-out.
- Hooks and plugins are power tools. They must be audited before being trusted in broad workflows.
- External GitHub skills are discovery inputs. ARMARIUS discovers, GUARDIAN gates, ARTIFEX adapts only selected ideas.

## Validation

```bash
node --check scripts/lib/surface-config.mjs
node --check scripts/codex-surface-audit.mjs
node --check scripts/sync-agents.mjs
node --check scripts/smoke.mjs
npm run audit:surface
npm run smoke
```

Expected green audit on this host:

- repository canonical skills: `37`;
- active `~/.agents/skills`: `37`;
- active skill drift dirs: `0`;
- Codex model: `gpt-5.6-sol`;
- Codex custom agents: low or zero unless intentionally configured;
- warnings may appear for inline secret-like config values or broad MCP servers; these are security visibility signals, not automatic blockers unless `--strict-secrets` is used.
