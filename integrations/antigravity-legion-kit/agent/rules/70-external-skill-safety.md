---
description: Safety gate for importing external Antigravity skills, workflows, rules, MCP servers, and agent packs.
---

# External Skill Safety

Apply this rule before using, installing, copying, or adapting any external Antigravity asset.

## Default Position

- Treat GitHub stars, npm downloads, and README claims as discovery signals only.
- Do not execute installer scripts, `npx` commands, shell scripts, Python scripts, or MCP servers from a repository before review.
- Prefer adapting ideas into local rules/workflows over bulk installing large third-party packs.
- Keep canonical Legion skills in `/home/mrz/.agents/skills`; do not duplicate that root into this kit.

## Required Review

For every candidate, capture:

- repository URL and license
- asset type: `.agent/rules`, `.agent/workflows`, `.agent/skills`, MCP, SDK, or installer
- install method and whether it writes global config
- scripts/dependencies present
- secrets, tokens, credential setup, browser/cloud/wallet/database access
- whether the asset can be used as documentation only

## Blockers

Do not install or run candidates with:

- `curl | sh`, `wget | sh`, encoded install payloads, or opaque remote execution
- hidden telemetry, obfuscated code, credential collection, or broad filesystem/cloud/browser access
- destructive commands without dry-run/confirmation/rollback
- no inspectable source or unclear license for copied content
- installer behavior that overwrites existing `.agent`, `.gemini`, `.claude`, shell profile, or MCP config without explicit approval

## Allowed Safe Uses

- Add a repository to the external catalog with warnings.
- Adapt a non-executable workflow pattern into local wording with attribution in docs.
- Read a `SKILL.md` for ideas, then implement a local workflow that follows this kit's proof contract.
- Run local smoke checks only for this kit, not for third-party code.

## Completion Proof

Before saying an external asset was accepted, provide:

- exact files read
- safety decision: accept, adapt-only, blocked, or needs user approval
- reason for the decision
- any local files changed
- `node ./scripts/smoke.mjs` result if this kit changed
