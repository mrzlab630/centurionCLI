# Codex Legion Kit

CENTURION surface audit and synchronization guards for Codex CLI.

This kit keeps Codex aligned with the current Legion structure without adding more Legionaries. It audits the repository skill source, the active `~/.agents/skills` surface, and the host-local Codex configuration.

## Local Baseline

- Codex CLI observed on this workstation: `codex-cli 0.139.0`.
- Current Codex model baseline: `gpt-5.5` with `model_reasoning_effort = "xhigh"`.
- Active Legion skill root: `~/.agents/skills`.
- Canonical repository skill root: `skills/` in this repository.
- Current Codex plugin validation is not used by this kit because this CLI version does not expose a dedicated `codex plugin validate` subcommand.

## What It Provides

- `scripts/codex-surface-audit.mjs`: read-only audit for Codex model/config, active skill drift, protocol pointers, hooks, custom agents, plugins, and MCP risk warnings.
- `scripts/sync-agents.mjs`: dry-run-first synchronization from repository `skills/` to active `~/.agents/skills`; writes only with `--write`.
- `scripts/smoke.mjs`: regression proof for audit, sync behavior, shared Legion result-contract validation, and Legion routing evals.
- `scripts/lib/surface-config.mjs`: the shared canonical skill list and generated-artifact ignore rules used by audit, sync, and smoke checks.

Codex uses `../legion-contracts` for neutral `LEGION_ORDER_V1`, `LEGION_RESULT_V1`, and `LEGION_REVIEW_V1` validation when a bounded delegation artifact needs machine checking. Normal discussion, research notes, and WAR ROOM reasoning stay in Markdown.

It does not install external GitHub skill packs, rewrite `~/.codex/config.toml`, or create new Legionary owners.

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

## Guard Philosophy

- One task still has one primary Legionary owner.
- Codex `gpt-5.5` is treated as a stronger executor, not permission to broaden roles.
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
- Codex model: `gpt-5.5`;
- Codex custom agents: low or zero unless intentionally configured;
- warnings may appear for inline secret-like config values or broad MCP servers; these are security visibility signals, not automatic blockers unless `--strict-secrets` is used.
