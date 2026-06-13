---
name: supply-chain-guard
description: Guard dependency installs, lockfile changes, MCP/tool configs, external skills, generated scripts, and agent harness surfaces.
---

# Supply Chain Guard

Use when adding/updating dependencies, running external install commands, changing MCP/agent config, importing third-party skills, or reviewing lockfile/script changes.

## Blockers

- `curl | sh`, `wget | sh`, base64 decode piped to shell, or remote shell execution
- obfuscated code or hidden telemetry
- unpinned `npx -y`/remote package execution in release paths
- dependency with suspicious install/postinstall script
- broad filesystem/browser/cloud/wallet/trading access without explicit approval
- secrets in agent config, MCP config, docs, screenshots, or examples

## Review Flow

1. Identify why the dependency/tool is needed and whether existing tooling covers it.
2. Inspect manifest, lockfile diff, install scripts, and permissions.
3. Run the repository's dependency audit command where available.
4. Report risk, recommendation, and safer alternative if blocked.

