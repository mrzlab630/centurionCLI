# Local Tooling Baseline

This document records the sanitized local tooling baseline refreshed on
2026-07-09 for the Cohors Secunda v2.2 repository release. It is a maintainer
aid, not a raw workstation backup.

The source checks were read-only and secret-bearing home configs were not copied
into the repository. Do not commit API keys, tokens, OAuth state, cookies,
authorization headers, project history, machine or user identifiers, raw
permission allowlists, trusted project lists, memory contents, or full home
config dumps. Use concise summaries and placeholders such as `[REDACTED]` only
when a field must be shown.

The machine-readable sanitized snapshot is
[`settings-snapshots/local-tooling-baseline-2026-07-09.json`](settings-snapshots/local-tooling-baseline-2026-07-09.json).

## Hermes / Aquila

- Version: `Hermes Agent v0.18.2 (2026.7.7.2)`.
- Install directory: `/home/mrz/.hermes/hermes-agent`.
- Revision summary: upstream `8e734810`, local `08058889`, with one carried commit.
- Runtime stack: Python `3.11.15`, OpenAI SDK `2.24.0`.
- Default model: `gpt-5.5`.
- Provider: `custom:cliproxyapi`.
- Local proxy: `http://127.0.0.1:8317/v1`.
- API mode: `codex_responses`.
- Context length: `256000`.
- Auxiliary routes for vision, web extract, compression, skills hub, approval, MCP, title generation, TTS audio tags, triage specifier, kanban decomposer, profile describer, curator, and monitor follow the same sanitized `gpt-5.5` local proxy pattern where configured.
- Browser baseline: Camofox `auto_start = true`, `managed_persistence = false`, `adopt_existing_tab = false`, `rewrite_loopback_urls = false`, loopback host alias `host.docker.internal`.
- Web baseline: `web.backend = brave-free`, `web.extract_backend = native`.
- Enabled plugins: `image_gen/cliproxy`, `video_gen/cliproxy`.
- Enabled built-in toolsets observed: web, browser, terminal, file, code execution, vision, image generation, video generation, TTS, skills, todo, memory, session search, clarify, delegation, cronjob.
- Disabled built-ins observed: video analysis, x_search, context engine, homeassistant, spotify, yuanbao, computer use.
- Enabled MCP servers in sanitized config summary: brave-search, github, playwright, context7, perplexity, memory, markitdown, pal.
- Config-disabled MCP servers: sequential-thinking, deepwiki.

This repository does not edit `~/.hermes/SOUL.md`, `~/.hermes/config.yaml`,
plugins, hooks, or MCP server config as part of this baseline refresh.

## Codex CLI

- Version: `codex-cli 0.142.5`.
- Default model: `gpt-5.5`.
- Model provider: `cliproxyapi`.
- Reasoning effort: `xhigh`.
- Personality: `pragmatic`.
- Local provider endpoint: `http://127.0.0.1:8317/v1`.
- Wire API: Responses.
- `features.memories = true`; memories remain a recall layer and are not copied into the repo.
- `features.multi_agent_v2.enabled = true` with spawn-agent metadata hidden.
- `~/.codex/agents` absent in the sanitized baseline.
- `~/.codex/hooks.json` absent in the sanitized baseline.
- `~/.codex/skills` entries observed: `.system`, `camofox-browser`, `migrate-to-codex`.

Do not commit raw `~/.codex/config.toml`, provider credentials, memories,
permissions state, trusted projects, or other private config state.

## Claude Code

- Version: `2.1.204 (Claude Code)`.
- Default model baseline: `claude-opus-4-8`.
- Settings summary: effort level and dangerous-mode prompt controls are present; raw settings are not copied.
- MCP servers observed in sanitized settings: solanaMcp, brave-search, context7, playwright, sequential-thinking, memoria, github, and serena where present in host-level Claude JSON.
- Installed `~/.claude/skills` entries include `centurion-legion` plus 37 Legionaries: aedilis, aleator, architect, artifex, augur, capabilities, censor, coder, context-optimizer, documenter, error-handler, evocate-ad-opus, git-master, glossator, haruspex, indagator, ludifex, mercator, nomenclator, orator, orchestrator, pictor, planner, pontifex, praeco, praemonitor, prompt-engineer, quaestor, refactorer, researcher, reviewer, security, sicarius, skill-quartermaster, tabularius, tester, velites.
- `~/.claude/plugins` exists with installed plugin metadata.
- `~/.claude/agents` absent in the sanitized baseline.
- Non-interactive proxy defaults: `ANTHROPIC_BASE_URL=http://127.0.0.1:8317`, placeholder `ANTHROPIC_API_KEY`, default opus `claude-opus-4-8`, default sonnet `claude-sonnet-4-6`, default haiku `claude-haiku-4-5-20251001`, `NO_PROXY=127.0.0.1,localhost`.

Do not commit raw Claude settings, OAuth state, permission allowlists, project
history, credentials, or machine identifiers.

## Antigravity / agy

- `agy` CLI version: `1.1.0`.
- Installed Antigravity IDE agent root exists at `~/.gemini/antigravity/agent` with rules, skills, and workflows.
- Installed Antigravity CLI plugins include `centurion-legion` and `google-genmedia-extension`.
- Repository plugin MCP config points `centurion-legion` to `/home/mrz/projects/al/centurionCLI/cohors-prima/integrations/antigravity-legion-kit/mcp-server/index.mjs` and sets `CENTURION_AGENT_ROOT` to `/home/mrz/projects/al/centurionCLI/cohors-prima/integrations/antigravity-legion-kit/agent`.
- Installed-config drift warning: live `~/.gemini/antigravity/mcp_config.json` currently points `centurion-legion` to `/home/mrz/tmp/antigravity-legion-kit/mcp-server/index.mjs` and `CENTURION_AGENT_ROOT` to `/home/mrz/tmp/antigravity-legion-kit/agent`.
- Reinstalling from this repository should refresh the installed MCP paths.

This baseline records the drift only. It does not edit `~/.gemini`, installed
Antigravity IDE files, Antigravity CLI plugin registries, or live MCP config.

## Host Toolchain

- Node.js: `v26.2.0`.
- npm: `11.13.0`.
- Python: `3.13.7`.
- ripgrep: `14.1.1`.
- pm2: `6.0.13`.
