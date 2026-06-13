# Antigravity Legion Kit

`integrations/antigravity-legion-kit` is the permanent CENTURION integration pack for Google Antigravity IDE and the `agy` Antigravity CLI.

The pack was moved into this repository so Antigravity rules, workflows, MCP tools, frontend/content catalogs, and the `AUXILIUM AGY` delegation protocol are versioned together with the canonical Legion surface.

## Source Of Truth

- Repository path: `integrations/antigravity-legion-kit`
- Installed IDE target: `~/.gemini/antigravity/agent`
- Installed CLI plugin target: `~/.gemini/antigravity-cli/plugins/centurion-legion`
- Canonical Legion skills: `~/.agents/skills`

The kit does not duplicate the canonical Legion skill root. It ships Antigravity-facing rules, workflows, compact skill briefs, catalogs, an MCP bridge, an installer, and proof scripts.

## Contents

| Path | Purpose |
| :--- | :--- |
| `agent/rules/` | Global Antigravity behavior rules, including single-owner routing and external-skill safety. |
| `agent/workflows/` | Reusable workflows for WAR ROOM, quality gates, frontend/iGaming work, reference search, content copy, and `agy` delegation. |
| `agent/skills/` | Compact Antigravity-facing skill briefs. |
| `agy-plugin/` | Antigravity CLI plugin exposing the compact `centurion-legion` skill and MCP config. |
| `mcp-server/` | Dependency-free stdio MCP bridge for routing, quality gates, catalogs, reference search, and delegation briefs. |
| `installer/` | Local installer for IDE rules, MCP config, and the `agy` CLI plugin. |
| `scripts/` | Smoke, catalog refresh, and `AGY_ORDER v1` guard scripts. |
| `docs/` | Architecture notes plus external, frontend, reference, and content/copy catalogs. |

## Install

Run from the repository root:

```bash
cd integrations/antigravity-legion-kit
node ./installer/install.mjs --dry-run
node ./installer/install.mjs
agy plugin validate /home/mrz/.gemini/antigravity-cli/plugins/centurion-legion
```

To install the agent pack into a project-local `.agent` directory:

```bash
cd integrations/antigravity-legion-kit
node ./installer/install.mjs --workspace-agent /path/to/project/.agent
```

The installer writes MCP paths from the current `KIT_ROOT`, so installed Antigravity and `agy` configs should point back to this repository copy, not to a temporary working directory.

## Validation

Run these checks before committing changes to the integration:

```bash
cd integrations/antigravity-legion-kit
node --check mcp-server/index.mjs
node --check scripts/smoke.mjs
node --check scripts/agy-order-guard.mjs
npm run smoke
npm run legion:eval
agy plugin validate ./agy-plugin
```

`npm run smoke` verifies required rules, workflows, plugin shape, MCP round trips, catalog JSON, owner routing coverage, installer behavior, and `AGY_ORDER v1` guard behavior.

## AUXILIUM AGY Contract

`agy` is a recruited auxiliary executor, not a Legionary owner. Use it only for bounded slices where the owner can define exact files, non-goals, forbidden patterns, proof commands, and acceptance criteria.

For implementation delegation, always use `AGY_ORDER v1`:

```bash
node integrations/antigravity-legion-kit/scripts/agy-order-guard.mjs snapshot \
  --workspace <dir> \
  --out /tmp/agy-before.json

node integrations/antigravity-legion-kit/scripts/agy-order-guard.mjs verify \
  --workspace <dir> \
  --before /tmp/agy-before.json \
  --allowed <paths> \
  --result AGY_RESULT.json \
  --forbidden <patterns>
```

Never accept `agy` stdout, narration, or self-report alone. Accept only after guard verification, owner proof, and direct diff or artifact inspection.

Do not delegate secrets, credentials, production deploys, destructive commands, wallet/payment/KYC flows, exploit execution, or final architecture/security/legal/product-risk judgment to `agy`.

## Maintenance Rules

- Keep one owner per task. Handoffs are conditional gates, not shared ownership.
- Keep external catalogs as discovery references only. Do not turn them into install allowlists without GUARDIAN review.
- Keep frontend/iGaming references as inspiration and structural evidence, not copy-paste sources.
- Refresh catalogs with the package scripts and commit generated Markdown/JSON together.
- Re-run the validation stack after changing routing, workflows, MCP tools, installer behavior, or `agy` protocol text.
