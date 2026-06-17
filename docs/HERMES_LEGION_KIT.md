# Hermes Legion Kit

`integrations/hermes-legion-kit` is the versioned source for the local Hermes/Aquila Team Lead pack.

## Purpose

Hermes already has the Team Lead identity in `/home/mrz/.hermes/SOUL.md`. This kit keeps the reusable operating procedures outside the always-loaded soul and exposes them through on-demand Hermes skills and lean bundles.

The pack is designed for Aquila managing `codex`, `claude`, `agy`, Hermes `delegate_task`, and Hermes Kanban without losing the one-owner-per-task rule.

## Installed Surface

- `aquila-team-orchestration`: routing, one owner per task, merge gates, result artifacts, proof acceptance.
- `aquila-harness-audit`: Hermes surface audit for SOUL, skills, bundles, plugins, MCP, contracts, context, and security.
- `aquila-executor-eval`: repeatable executor benchmarks with pass@1/pass@3, scope, proof, time, and correction metrics.
- `aquila-self-debug`: recovery loop for executor failures, adapter noise, missing artifacts, and repeated retry loops.
- `/aquila-delivery`: lean delivery bundle.
- `/aquila-harness-audit`: lean harness-audit bundle.
- `/aquila-executor-eval`: lean executor-eval bundle.

## Safety Boundary

This kit intentionally does not:

- edit `SOUL.md`;
- edit `~/.hermes/config.yaml`;
- enable Hermes plugins or hooks;
- modify MCP server configuration;
- import ECC runtime files;
- add external dependencies.

ECC remains a pattern source only. Any future plugin, hook, MCP server, or third-party skill import requires a separate GUARDIAN safety gate.

## Install

Dry-run first:

```bash
cd integrations/hermes-legion-kit
npm run install:dry-run
```

Install into the default Hermes home:

```bash
npm run install
```

Install into a test home:

```bash
node ./installer/install.mjs --hermes-home /tmp/hermes-home-test
```

## Verify

Repository-only proof:

```bash
node --check installer/install.mjs
node --check scripts/smoke.mjs
npm run smoke
```

Live Hermes proof after install:

```bash
hermes skills list | rg aquila
hermes bundles reload
hermes bundles show aquila-delivery
hermes bundles show aquila-harness-audit
hermes bundles show aquila-executor-eval
hermes doctor
```

`hermes skills inspect aquila-*` was observed to hang during the first local rollout. Until that Hermes CLI behavior is fixed, use `skills list`, `bundles show`, repository smoke, and direct file validation as the reliable proof path.

## Context Policy

Bundles stay lean by design. They preload only the skills needed to select and control a workflow. Heavy references such as `claude-code`, `codex`, `kanban-orchestrator`, `requesting-code-review`, `test-driven-development`, and `hermes-agent` are loaded only when the current task needs those details.

This prevents the delivery bundle from turning a small Team Lead prompt into a 100k+ token request.
