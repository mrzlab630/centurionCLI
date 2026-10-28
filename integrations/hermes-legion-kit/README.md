# Hermes Legion Kit 1.0.0 — CENTURION 3.0.0-rc.5

This native instruction adapter uses the [single functional contract](../../skills/orchestrator/SKILL.md)
and [load map](../codex-legion-kit/scripts/lib/surface-config.mjs).
The kit version changes for the breaking explicit-selection installer API; it is
separate from product acceptance and does not introduce a new order schema.

Install only to an explicitly authorized isolated home:

```bash
node integrations/hermes-legion-kit/installer/install.mjs --profile domain --skill coder --hermes-home /tmp/centurion-fixture/hermes
```

Choose `core`, `domain` or `maintenance`; domain and maintenance require explicit
`--skill` values from the map. There is no automatic full-library installation.
Use `--dry-run` to inspect selection and target paths. Unknown settings/instructions
or a modified owned file are reported as conflicts without changing them. Prior
owned manifests enable transactional upgrade, retirement and rollback. Existing
legacy homes without ownership evidence need a separate reviewed migration.

Read `<native-home>/centurion/installed-chain.json` for every source/installed
hash, selected instruction and adapter evidence. Missing or changed binary/config/
route/adapter capability binding excludes that adapter. Installation runs no live
client CLI, update, dependency sync, external model or automatic MCP registration.
New dispatch remains Gateway-only; native agents are bounded projections. No
copied upstream delegation skills or alternate queues are part of the bundle.

Open Design is archived and excluded from active selection, installation and
runtime routing. General UI/UX and web-development skills remain available through
explicit domain selection; media generation uses the consumer's available tools.
Camofox and document conversion require their
own requested task and proven adapter; they are not automatic MCP installs.
See the [root README](../../README.md) for proof commands and N5/N6 limitations.
