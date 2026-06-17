# Hermes Legion Kit

CENTURION/Aquila Team Lead skills and lean skill bundles for Hermes Agent.

This kit versions the local Hermes additions that were first installed under `~/.hermes`: four Aquila skills and three slash-command bundles. It does not import ECC runtime code, enable plugins, change MCP servers, or edit `SOUL.md`.

## What It Installs

- `skills/autonomous-ai-agents/aquila-team-orchestration`: Team Lead routing for codex, claude, agy, Hermes `delegate_task`, and Kanban with one owner per task.
- `skills/autonomous-ai-agents/aquila-harness-audit`: Hermes surface audit for SOUL, skills, bundles, plugins, MCP, contracts, context, and security gates.
- `skills/autonomous-ai-agents/aquila-executor-eval`: repeatable executor evals for codex, claude, agy, and `delegate_task` using deterministic proof.
- `skills/autonomous-ai-agents/aquila-self-debug`: contained recovery workflow for executor failures, adapter noise, missing artifacts, and loops.
- `skill-bundles/aquila-delivery.yaml`: lean `/aquila-delivery` entrypoint.
- `skill-bundles/aquila-harness-audit.yaml`: lean `/aquila-harness-audit` entrypoint.
- `skill-bundles/aquila-executor-eval.yaml`: lean `/aquila-executor-eval` entrypoint.

## Quick Start

```bash
cd integrations/hermes-legion-kit
npm run smoke
npm run install:dry-run
npm run install
hermes skills list | rg aquila
hermes bundles reload
hermes bundles list
```

To install into a temporary Hermes home:

```bash
node ./installer/install.mjs --hermes-home /tmp/hermes-home-test
```

## Design Rules

- Keep `SOUL.md` compact. Optional Team Lead workflows live in skills and bundles.
- Keep bundles lean. Heavy skills such as `claude-code`, `codex`, `requesting-code-review`, `test-driven-development`, `kanban-orchestrator`, and `hermes-agent` are loaded on demand only.
- Do not bulk-import ECC. ECC is an idea source; this kit contains manually adapted Hermes-native procedures only.
- Do not enable Hermes plugins or hooks from this kit. Plugins execute code and require a separate GUARDIAN review.
- Do not widen MCP access from this kit. MCP changes belong to a separate harness audit and explicit operator decision.

## Local Baseline

- Hermes observed on this workstation: `Hermes Agent v0.16.0 (2026.6.5)`.
- Local Hermes home: `/home/mrz/.hermes`.
- Aquila Team Lead identity lives in `/home/mrz/.hermes/SOUL.md` and remains the primary role contract.
- Live `hermes -z` smoke may depend on current provider health; the repository smoke is intentionally offline and deterministic.

## Validation

```bash
node --check installer/install.mjs
node --check scripts/smoke.mjs
node ./scripts/smoke.mjs
node ./installer/install.mjs --dry-run
```

The smoke check verifies all four skills, all three lean bundles, trigger-bearing descriptions, absence of direct ECC clone references, no remote-shell install pattern, JavaScript syntax, and installer dry-run behavior.

After installing on a live Hermes home, verify through Hermes itself:

```bash
hermes skills list | rg aquila
hermes bundles reload
hermes bundles show aquila-delivery
hermes bundles show aquila-harness-audit
hermes bundles show aquila-executor-eval
hermes doctor
```

`hermes skills inspect aquila-*` was observed to hang on this host during the first local rollout. Treat `skills list`, `bundles show`, the offline smoke check, and direct file validation as the reliable proof path until that Hermes CLI behavior is fixed upstream.
