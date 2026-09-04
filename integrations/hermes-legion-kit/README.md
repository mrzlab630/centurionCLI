# Hermes Legion Kit

CENTURION/Aquila Team Lead skills and lean skill bundles for Hermes Agent (kit version 0.7.2).

This kit versions the local Hermes additions that were first installed under `~/.hermes`: six Aquila skills, the SOLARIUS `solana-program-engineering` skill, one shared Open Design capability, its local stdio MCP, four slash-command bundles, and a packaged delegation monitor. SOLARIUS remains Aquila-routed and never self-approves implementation, audit findings, or release readiness. It does not import ECC runtime code, enable plugins, alter unrelated MCP servers, or edit `SOUL.md`.

The reviewed adaptive routing policy is available as the manual note
`overrides/ADAPTIVE_MODEL_ROUTING_POLICY.md`. It is reference-only: the
installer remains non-applying for SOUL, Codex, Claude, config, plugins, hooks,
and MCP policy files.

## What It Installs

- `skills/autonomous-ai-agents/aquila-team-orchestration`: Team Lead routing for codex, claude, agy, Hermes `delegate_task`, and Kanban with one owner per task.
- `skills/autonomous-ai-agents/aquila-execution-state`: opt-in, read-only `AQUILA_EXECUTION_STATE_V1` projection with strict scope, revision, provenance, and bounded evidence references.
- `skills/autonomous-ai-agents/agent-contract-runner`: portable AGENT_ORDER_JSON_V1 validation, shared strict JSON decoding, fail-closed V0-V3 routing, append-only attempt ledger, gateway-owned canonical result building, and offline regressions.
- `skills/autonomous-ai-agents/agent-contract-runner/scripts/strict_json.py`: shared packaged decoder for authoritative Python JSON reads, including duplicate-key and non-finite rejection.
- `skills/autonomous-ai-agents/agent-contract-runner/scripts/result_gateway.py`: controller-owned Codex/Claude launch closure and canonical result finalization.
- `skills/autonomous-ai-agents/agent-contract-runner/scripts/regression_result_gateway.py`: focused offline regression coverage for gateway custody and terminal closure.
- `skills/autonomous-ai-agents/agent-contract-runner/scripts/regression_execution_state.py`: focused offline regression coverage for the default-off execution-state projection.
- `skills/autonomous-ai-agents/aquila-harness-audit`: Hermes surface audit for SOUL, skills, bundles, plugins, MCP, contracts, context, and security gates.
- `skills/autonomous-ai-agents/aquila-executor-eval`: repeatable executor evals for codex, claude, agy, and `delegate_task` using deterministic proof.
- `skills/autonomous-ai-agents/aquila-self-debug`: contained recovery workflow for executor failures, adapter noise, missing artifacts, and loops.
- `skills/autonomous-ai-agents/open-design-producer`: shared JSON-driven Open Design production used by AEDILIS and PICTOR; it returns verified HTML and Chrome screenshot paths.
- `skills/software-development/solana-program-engineering`: SOLARIUS guidance for Solana program engineering, testing, release, and security auditing; it remains under Aquila scope and independent-review gates.
- `skill-bundles/aquila-delivery.yaml`: lean `/aquila-delivery` entrypoint.
- `skill-bundles/aquila-harness-audit.yaml`: lean `/aquila-harness-audit` entrypoint.
- `skill-bundles/aquila-executor-eval.yaml`: lean `/aquila-executor-eval` entrypoint.
- `skill-bundles/aquila-design-production.yaml`: lean `/aquila-design-production` entrypoint.
- `centurion/open-design-bridge.json`: absolute path to the repository bridge; no MCP or plugin changes.
- `runtime/bin/monitor-delegation.sh`: strict terminal-closure monitor installed as `$HERMES_HOME/bin/monitor-delegation.sh`.

- `overrides/ADAPTIVE_MODEL_ROUTING_POLICY.md`: concise reviewed model/effort routing invariants; manual and not automatically installed.
- `overrides/AQUILA_SOUL_OVERRIDES.md`: manual V0-V3 SOUL policy note; never installed or patched into `SOUL.md`.

The execution-state projection keeps legacy terminal compatibility explicit:
`execution_state.py project --legacy-terminal-compat` accepts only an implicit
terminal result as a read-only `verify` snapshot, rejects parent chaining, and
records `read-only-derived-legacy-terminal`. Result summaries over 512 UTF-8
bytes are represented by the bounded `execution.summaryOmitted` marker while
the canonical result digest remains exact.

## Quick Start

```bash
cd integrations/hermes-legion-kit
npm run smoke
npm run audit:local
npm run install:dry-run
npm run install
hermes skills list | rg aquila
hermes skills list | rg open-design-producer
hermes skills list | rg solana-program-engineering
hermes bundles reload
hermes bundles list
```

To install into a temporary Hermes home:

```bash
node ./installer/install.mjs --hermes-home /tmp/hermes-home-test
```

To also apply reviewed optional overrides such as the compact `research-paper-writing` entrypoint:

```bash
node ./installer/install.mjs --include-overrides
```

`--include-overrides` still does not edit `SOUL.md`. The installer changes only the named `centurion-open-design` MCP entry in `config.yaml`; other config and MCP entries remain intact. The reviewed SOUL notes are `overrides/SOUL_RUNTIME_MODEL_RULE.md` and `overrides/SOUL_CLAUDE_ROLE_RULE.md`; both remain manual and reviewable, and neither is applied automatically by the installer.

Owned skill, bundle, runtime, bridge-config, and optional override targets are
staged before replacement. If Hermes MCP registration fails, the installer
restores those targets and the previous `config.yaml` bytes and modes.

## Design Rules

- Keep `SOUL.md` compact. Optional Team Lead workflows live in skills and bundles.
- Keep bundles lean. Heavy skills such as `claude-code`, `codex`, `requesting-code-review`, `test-driven-development`, `kanban-orchestrator`, and `hermes-agent` are loaded on demand only.
- Do not bulk-import ECC. ECC is an idea source; this kit contains manually adapted Hermes-native procedures only.
- Do not enable Hermes plugins or hooks from this kit. Plugins execute code and require a separate GUARDIAN review.
- Do not widen MCP access from this kit. MCP changes belong to a separate harness audit and explicit operator decision.
- Treat runtime model evidence as current-session truth. If `config.yaml`, `hermes profile list`, or `hermes prompt-size` reports a stale model while turn context/logs show a runtime switch, classify it as a warning with proof, not an identity conflict.
- Treat enabled `npx -y` MCP servers as explicit supply-chain warnings even when the package is version-pinned.
- Keep optional overrides explicit. Builtin skill overrides are installed only with `--include-overrides`; SOUL/config changes stay manual and reviewable.
- Route every external Codex or Claude candidate through `result_gateway.py`. The gateway must complete full canonical order validation, including ledger-aware routing, before creating receipts or launching the child; `agent_result_builder.py` remains an internal canonicalization stage.
- Treat `strict_json.py` semantics as the package boundary for Python control-plane input. Duplicate keys, `NaN`, `Infinity`, `-Infinity`, and overflowed literals such as `1e999` fail closed; the installed monitor enforces equivalent parsing and exact `routingSha256` receipt binding.
- Keep new executor control artifacts under `<repo>/.centurion/agents_results/<orderId>/`, derived from the resolved repository and a fresh safe `orderId`. Product/application artifacts remain in their declared paths; root-artifact cleanup is a separate migration operation.

## Local Baseline

- Sanitized baseline date: 2026-07-09. Raw `~/.hermes/config.yaml`, API keys, credentials, and private permission state are intentionally not copied into this repository.
- Hermes observed on this workstation: `Hermes Agent v0.18.2 (2026.7.7.2)`.
- Local Hermes home: `/home/mrz/.hermes`.
- Install directory: `/home/mrz/.hermes/hermes-agent`; upstream revision `8e734810`, local revision `08058889` with one carried commit.
- Runtime stack: Python `3.11.15`, OpenAI SDK `2.24.0`.
- Main model: `gpt-5.6-sol` through `custom:cliproxyapi` at `http://127.0.0.1:8317/v1`, `api_mode = codex_responses`, context length `256000`.
- Web baseline: `web.backend = brave-free`, `web.extract_backend = native`.
- Browser baseline: Camofox `auto_start = true`, `managed_persistence = false`, `adopt_existing_tab = false`, `rewrite_loopback_urls = false`, loopback alias `host.docker.internal`.
- Enabled plugins observed: `image_gen/cliproxy` and `video_gen/cliproxy`.
- Enabled MCP servers in sanitized config summary: brave-search, github, playwright, context7, perplexity, memory, markitdown, pal. Config-disabled MCP servers: sequential-thinking and deepwiki.
- Aquila Team Lead identity lives in `/home/mrz/.hermes/SOUL.md` and remains the primary role contract.
- Live `hermes -z` smoke may depend on current provider health; the repository smoke is intentionally offline and deterministic.

## Validation

```bash
node --check installer/install.mjs
node --check scripts/smoke.mjs
node --check scripts/harness-audit.mjs
node ./scripts/smoke.mjs
node ./installer/install.mjs --dry-run
npm run audit:local
cd skills/autonomous-ai-agents/agent-contract-runner/scripts
PYTHONDONTWRITEBYTECODE=1 python3 regression_review_ladder.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_contract_runner.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_result_builder.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_result_gateway.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_execution_state.py
```

The smoke check verifies all six Aquila skills, SOLARIUS, the shared Open Design capability, all four lean bundles, trigger-bearing descriptions, absence of direct ECC clone references, no remote-shell install pattern, JavaScript syntax, deterministic audit script syntax, and installer dry-run behavior. It also installs into an isolated temporary HOME, checks the SOLARIUS `SKILL.md` plus all four references under `skills/software-development/solana-program-engineering`, the Open Design config and executable wrapper, `strict_json.py`, `result_gateway.py`, `regression_result_gateway.py`, `regression_execution_state.py`, `runtime/bin/monitor-delegation.sh`, the packaged routing reference and runner scripts, preserves the Opus 5 routing assertions, and runs all five packaged Python regressions without touching the live Hermes home.

The packaged contract-runner Python scripts require the existing Python `jsonschema` runtime. The kit does not install or declare that dependency in its JavaScript package manifests. Result-schema lookup uses an explicit `--schema`/library argument first, then `AQUILA_AGENT_RESULT_SCHEMA`, the packaged `references/agent-result.schema.json`, `HERMES_HOME/contracts/agent-result.schema.json`, and finally `~/.hermes/contracts/agent-result.schema.json`.

`npm run audit:local` is read-only. It checks the local Hermes home for stale model/profile ambiguity, missing runtime-model SOUL rule, enabled `npx -y` MCP servers, and oversized `SKILL.md` files that should be split into `references/`.

The smoke check also verifies that optional overrides stay below the Hermes `SKILL.md` size limit, remain reference-routed, and include the reviewed runtime-model and Claude-role SOUL notes.

After installing on a live Hermes home, verify through Hermes itself:

```bash
hermes skills list | rg aquila
hermes bundles reload
hermes bundles show aquila-delivery
hermes bundles show aquila-harness-audit
hermes bundles show aquila-executor-eval
hermes bundles show aquila-design-production
hermes doctor
hermes security audit
```

`hermes skills inspect aquila-*` was observed to hang on this host during the first local rollout. Treat `skills list`, `bundles show`, the offline smoke check, and direct file validation as the reliable proof path until that Hermes CLI behavior is fixed upstream.
