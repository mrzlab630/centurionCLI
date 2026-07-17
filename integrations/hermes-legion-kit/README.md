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
npm run audit:local
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

To also apply reviewed optional overrides such as the compact `research-paper-writing` entrypoint:

```bash
node ./installer/install.mjs --include-overrides
```

`--include-overrides` still does not edit `SOUL.md` or `config.yaml`. The reviewed SOUL notes are `overrides/SOUL_RUNTIME_MODEL_RULE.md` and `overrides/SOUL_CLAUDE_ROLE_RULE.md`; both remain manual and reviewable, and neither is applied automatically by the installer.

## Design Rules

- Keep `SOUL.md` compact. Optional Team Lead workflows live in skills and bundles.
- Keep bundles lean. Heavy skills such as `claude-code`, `codex`, `requesting-code-review`, `test-driven-development`, `kanban-orchestrator`, and `hermes-agent` are loaded on demand only.
- Do not bulk-import ECC. ECC is an idea source; this kit contains manually adapted Hermes-native procedures only.
- Do not enable Hermes plugins or hooks from this kit. Plugins execute code and require a separate GUARDIAN review.
- Do not widen MCP access from this kit. MCP changes belong to a separate harness audit and explicit operator decision.
- Treat runtime model evidence as current-session truth. If `config.yaml`, `hermes profile list`, or `hermes prompt-size` reports a stale model while turn context/logs show a runtime switch, classify it as a warning with proof, not an identity conflict.
- Treat enabled `npx -y` MCP servers as explicit supply-chain warnings even when the package is version-pinned.
- Keep optional overrides explicit. Builtin skill overrides are installed only with `--include-overrides`; SOUL/config changes stay manual and reviewable.

## Local Baseline

- Sanitized baseline date: 2026-07-09. Raw `~/.hermes/config.yaml`, API keys, credentials, and private permission state are intentionally not copied into this repository.
- Hermes observed on this workstation: `Hermes Agent v0.18.2 (2026.7.7.2)`.
- Local Hermes home: `/home/mrz/.hermes`.
- Install directory: `/home/mrz/.hermes/hermes-agent`; upstream revision `8e734810`, local revision `08058889` with one carried commit.
- Runtime stack: Python `3.11.15`, OpenAI SDK `2.24.0`.
- Main model: `gpt-5.5` through `custom:cliproxyapi` at `http://127.0.0.1:8317/v1`, `api_mode = codex_responses`, context length `256000`.
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
```

The smoke check verifies all four skills, all three lean bundles, trigger-bearing descriptions, absence of direct ECC clone references, no remote-shell install pattern, JavaScript syntax, deterministic audit script syntax, and installer dry-run behavior.

`npm run audit:local` is read-only. It checks the local Hermes home for stale model/profile ambiguity, missing runtime-model SOUL rule, enabled `npx -y` MCP servers, and oversized `SKILL.md` files that should be split into `references/`.

The smoke check also verifies that optional overrides stay below the Hermes `SKILL.md` size limit, remain reference-routed, and include the reviewed runtime-model and Claude-role SOUL notes.

After installing on a live Hermes home, verify through Hermes itself:

```bash
hermes skills list | rg aquila
hermes bundles reload
hermes bundles show aquila-delivery
hermes bundles show aquila-harness-audit
hermes bundles show aquila-executor-eval
hermes doctor
hermes security audit
```

`hermes skills inspect aquila-*` was observed to hang on this host during the first local rollout. Treat `skills list`, `bundles show`, the offline smoke check, and direct file validation as the reliable proof path until that Hermes CLI behavior is fixed upstream.
