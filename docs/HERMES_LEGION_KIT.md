# Hermes Legion Kit

`integrations/hermes-legion-kit` (version 0.5.0) is the versioned source for the local Hermes/Aquila Team Lead pack.

## Purpose

Hermes already has the Team Lead identity in `/home/mrz/.hermes/SOUL.md`. This kit keeps the reusable operating procedures outside the always-loaded soul and exposes them through on-demand Hermes skills and lean bundles.

The pack is designed for Aquila managing `codex`, `claude`, `agy`, Hermes `delegate_task`, and Hermes Kanban without losing the one-owner-per-task rule.

## Installed Surface

- `aquila-team-orchestration`: routing, one owner per task, merge gates, result artifacts, proof acceptance.
- `agent-contract-runner`: portable contract validation, shared strict JSON semantics, V0-V3 review routing, append-only attempt-ledger handling, controller-owned Result Gateway, internal canonical result builder, and offline regressions.
- `agent-contract-runner/scripts/strict_json.py`: duplicate-key and non-finite rejection for packaged Python orders, results, schemas, ledger rows, loop state, and routing metadata.
- `agent-contract-runner/scripts/result_gateway.py`: mandatory direct Codex/Claude launch and candidate-finalization boundary.
- `$HERMES_HOME/bin/monitor-delegation.sh`: installed strict terminal monitor for route-bound start and closure receipts.
- `aquila-harness-audit`: Hermes surface audit for SOUL, skills, bundles, plugins, MCP, contracts, context, and security.
- `scripts/harness-audit.mjs`: read-only deterministic local audit for runtime model ambiguity, `npx -y` MCP supply-chain warnings, oversized `SKILL.md` files, and the SOUL runtime-model rule.
- `overrides/skills/research/research-paper-writing/SKILL.md`: compact optional override that keeps the research-paper skill under the Hermes size limit while routing detail to `references/`.
- `overrides/SOUL_RUNTIME_MODEL_RULE.md`: reviewed SOUL rule text for runtime-model precedence; not applied by the default installer.
- `overrides/SOUL_CLAUDE_ROLE_RULE.md`: reviewed SOUL rule text for Claude/Codex routing, independent review, and Aquila final judgment; not applied by the default installer.
- `overrides/ADAPTIVE_MODEL_ROUTING_POLICY.md`: reviewed adaptive model/effort policy; manual reference only and not automatically installed.
- `overrides/AQUILA_SOUL_OVERRIDES.md`: manual V0-V3 cutover note; the installer never patches `SOUL.md`.
- `aquila-executor-eval`: repeatable executor benchmarks with pass@1/pass@3, scope, proof, time, and correction metrics.
- `aquila-self-debug`: recovery loop for executor failures, adapter noise, missing artifacts, and repeated retry loops.
- `open-design-producer`: shared Open Design production capability. AEDILIS owns UX briefs and visual acceptance; PICTOR owns create/revise HTML/UI work.
- `/aquila-delivery`: lean delivery bundle.
- `/aquila-harness-audit`: lean harness-audit bundle.
- `/aquila-executor-eval`: lean executor-eval bundle.
- `/aquila-design-production`: lean design-production bundle.
- `$HERMES_HOME/centurion/open-design-bridge.json`: absolute bridge discovery config written by the installer.

## Safety Boundary

This kit intentionally does not:

- edit `SOUL.md`;
- edit `~/.hermes/config.yaml`;
- enable Hermes plugins or hooks;
- modify MCP server configuration;
- import ECC runtime files;
- add external dependencies.

ECC remains a pattern source only. Any future plugin, hook, MCP server, or third-party skill import requires a separate GUARDIAN safety gate.

## Runtime Model Rule

Hermes can report different model names through persistent config/profile surfaces and active runtime evidence. For the current session, active turn context and live API-call logs are stronger evidence than stale `config.yaml`, `hermes profile list`, or `hermes prompt-size` summaries.

Mismatch handling:

- classify as `warn`, not identity conflict;
- report both values and the proof path;
- continue only if the active provider is otherwise healthy;
- clean persistent config separately when stale summaries will confuse future preflight or reports.

## Sanitized Local Baseline

The current sanitized workstation baseline was refreshed on 2026-07-09 from
read-only checks and recorded without copying `~/.hermes/config.yaml` or any
secret-bearing home config into this repository.

- Hermes version: `Hermes Agent v0.18.2 (2026.7.7.2)`.
- Install directory: `/home/mrz/.hermes/hermes-agent`.
- Upstream/local revisions: upstream `8e734810`, local `08058889` with one carried commit.
- Runtime stack: Python `3.11.15`, OpenAI SDK `2.24.0`.
- Main model: `gpt-5.6-sol` through provider `custom:cliproxyapi`.
- Local proxy: `http://127.0.0.1:8317/v1` with `codex_responses` API mode and `256000` context length.
- Auxiliary routes for vision, web extract, compression, skills hub, approvals, MCP, title generation, TTS audio tags, triage, kanban decomposition, profile description, curator, and monitor use the same sanitized `gpt-5.6-sol` local proxy pattern where configured.
- Browser baseline: Camofox `auto_start = true`, `managed_persistence = false`, `adopt_existing_tab = false`, `rewrite_loopback_urls = false`, and loopback host alias `host.docker.internal`.
- Web baseline: `web.backend = brave-free`, `web.extract_backend = native`.
- Enabled plugin families observed: `image_gen/cliproxy` and `video_gen/cliproxy`.
- Enabled built-in toolsets observed: web, browser, terminal, file, code execution, vision, image generation, video generation, TTS, skills, todo, memory, session search, clarify, delegation, cronjob.
- Disabled built-ins observed: video analysis, x_search, context engine, homeassistant, spotify, yuanbao, computer use.
- Enabled MCP servers in sanitized config summary: brave-search, github, playwright, context7, perplexity, memory, markitdown, pal.
- Config-disabled MCP servers: sequential-thinking and deepwiki.

Do not treat this kit as authority to edit live Hermes home config. Refresh live
settings separately and record only sanitized summaries in
`docs/settings-snapshots/`.

## MCP Supply-Chain Rule

Enabled `npx -y package@version` MCP servers are warnings even when version-pinned. Version pins reduce drift but still use registry execution and cache/integrity assumptions. High-trust MCP servers should prefer local checked binaries or pinned local installs after separate review.

The harness audit must record owner, server name, package/version, enabled status, config line, and mitigation decision.

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

Apply optional skill overrides explicitly:

```bash
node ./installer/install.mjs --include-overrides
```

The default installer writes Aquila content under `$HERMES_HOME/skills` and `$HERMES_HOME/skill-bundles`, copies the canonical Open Design skill to `$HERMES_HOME/skills/autonomous-ai-agents/open-design-producer`, writes its bridge discovery config under `$HERMES_HOME/centurion`, and writes the packaged monitor to `$HERMES_HOME/bin/monitor-delegation.sh`. It does not edit `SOUL.md`, `config.yaml`, plugins, hooks, or MCP servers. `--include-overrides` can additionally update reviewed builtin skill overrides. Before activating the kit in a live Hermes home, back up every existing destination, record its content hash and file mode, verify the installed hash and mode, and keep a tested rollback path. The reviewed `SOUL_RUNTIME_MODEL_RULE.md` and `SOUL_CLAUDE_ROLE_RULE.md` notes are manual and reviewable; neither is automatically applied by the installer.

The adaptive model/effort policy note is also manual and reviewable; no
installer mode applies it automatically.

## Delegation Result Boundary

All external Codex or Claude candidates go through `result_gateway.py`. Before any output preflight can create a receipt or the child can launch, the gateway runs full canonical `validate_order`, including attempt-ledger-aware routing validation. Missing, duplicate, malformed, below-floor, wrong-reviewer/model, or recursive terminal routing fails with no child or candidate/result/start/closure/stdout/stderr artifacts.

The packaged Python control plane uses `strict_json.py` for every authoritative JSON read. Duplicate object keys, `NaN`, `Infinity`, `-Infinity`, and float literals such as `1e999` that overflow to a non-finite value are rejected with input context. The separately installed monitor embeds equivalent parsing for order, result, schema, start-receipt, and closure JSON.

For valid post-cutover orders, the gateway stores the exact canonical routing metadata and deterministic `routingSha256` in both start and closure receipts. The monitor recomputes the binding from the strict order and requires exact order/start/closure equality before it reports `terminal-closure-verified`. `agent_result_builder.py` is internal canonicalization after this preflight and launcher closure; it is not an external bypass.

## Verify

Repository-only proof:

```bash
node --check installer/install.mjs
node --check scripts/smoke.mjs
node --check scripts/harness-audit.mjs
npm run smoke
npm run audit:local
cd skills/autonomous-ai-agents/agent-contract-runner/scripts
PYTHONDONTWRITEBYTECODE=1 python3 regression_review_ladder.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_contract_runner.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_result_builder.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_result_gateway.py
```

Live Hermes proof after install:

```bash
hermes skills list | rg aquila
hermes skills list | rg open-design-producer
hermes bundles reload
hermes bundles show aquila-delivery
hermes bundles show aquila-harness-audit
hermes bundles show aquila-executor-eval
hermes bundles show aquila-design-production
hermes doctor
hermes security audit
```

`hermes doctor` npm advisories and `hermes security audit` Python findings are separate gates. Build-tool npm advisories can be warnings when they do not affect runtime execution; Python runtime dependency findings need their own exposure analysis and may be blockers.

`hermes skills inspect aquila-*` was observed to hang during the first local rollout. Until that Hermes CLI behavior is fixed, use `skills list`, `bundles show`, repository smoke, and direct file validation as the reliable proof path.

## Context Policy

Bundles stay lean by design. They preload only the skills needed to select and control a workflow. Heavy references such as `claude-code`, `codex`, `kanban-orchestrator`, `requesting-code-review`, `test-driven-development`, and `hermes-agent` are loaded only when the current task needs those details.

This prevents the delivery bundle from turning a small Team Lead prompt into a 100k+ token request.
