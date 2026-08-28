# Antigravity Legion Kit

Portable CENTURION rules, workflows, skill briefs, and a small MCP bridge for Google Antigravity.

Current kit version: `0.2.1`.

## What It Installs

- `agent/rules`: global Antigravity rules for disciplined coding behavior.
- `agent/rules/05-single-owner-routing.md`: routing contract that keeps one task under one Legionary owner with conditional handoffs.
- `agent/workflows`: reusable workflows such as WAR ROOM, quality gate, build fix, browser QA, and release readiness.
- `agent/workflows/frontend-landing-igaming.md`: frontend route for interfaces, motion, landing pages, and iGaming pages.
- `agent/workflows/frontend-reference-search.md`: reference-search route for finding implemented pages, blocks, templates, and product flows before UI build work.
- `agent/workflows/content-copy-system.md`: product-language route for naming, CTA, UX copy, hints, descriptions, states, and conversion copy.
- `agent/workflows/agy-delegation.md`: AUXILIUM AGY delegation protocol for bounded CLI execution with self-review and owner acceptance gates.
- `agent/workflows/external-skill-audit.md`: safety review before importing outside Antigravity assets.
- `agent/workflows/skill-migrator.md`: migration path from external `SKILL.md` files into local rules/workflows.
- `agent/skills`: Antigravity-facing skill briefs copied from the current local pack.
- `agent/skills/product-language-copy.md`: compact brief for product language, UX-writing, naming, and claim-safe copy.
- `agy-plugin`: Antigravity CLI plugin for `agy`, with one compact Legion routing skill, the local Legion MCP server entry, and Serena for symbol-aware code navigation/editing.
- `mcp-server`: local stdio MCP server exposing Legion routing and proof tools.
- `installer`: local installer that copies the pack and updates `mcp_config.json`.
- `docs/EXTERNAL_CATALOG.md`: curated GitHub sources and safety decisions.
- `docs/external-catalog.json`: machine-readable catalog with intake actions and blockers for MCP use.
- `docs/FRONTEND_CATALOG.md`: curated frontend, landing, motion, and iGaming source catalog.
- `docs/frontend-catalog.json`: machine-readable frontend source catalog for MCP intake.
- `docs/FRONTEND_REFERENCE_INDEX.md`: searchable reference index for implemented frontend pages, blocks, templates, visual galleries, and product flows.
- `docs/frontend-reference-index.json`: machine-readable reference index used by `frontend_reference_search`.
- `docs/CONTENT_COPY_CATALOG.md`: curated content design, UX-writing, product-language, and copywriting source catalog.
- `docs/content-copy-catalog.json`: machine-readable content/copy source catalog for MCP intake.

The canonical Legion skill source remains `/home/mrz/.agents/skills`; this kit does not duplicate that root.

## Sanitized Local Baseline

- Sanitized baseline date: 2026-07-09. Raw `~/.gemini` configs, account data, machine identifiers, credentials, and installed runtime dumps are intentionally not copied into this repository.
- `agy` CLI version: `1.1.0`.
- Installed Antigravity IDE agent root exists at `~/.gemini/antigravity/agent` with rules, skills, and workflows.
- Installed Antigravity CLI plugins include `centurion-legion` and `google-genmedia-extension`.
- Repository plugin MCP config points `centurion-legion` to `integrations/antigravity-legion-kit/mcp-server/index.mjs` and sets `CENTURION_AGENT_ROOT` to `integrations/antigravity-legion-kit/agent`.
- Installed-config drift warning: live `~/.gemini/antigravity/mcp_config.json` currently points `centurion-legion` at `/home/mrz/tmp/antigravity-legion-kit/mcp-server/index.mjs` with `CENTURION_AGENT_ROOT=/home/mrz/tmp/antigravity-legion-kit/agent`.
- Reinstalling from this repository should refresh the installed MCP paths. This kit refresh does not edit home config.

## Quick Start

```bash
cd integrations/antigravity-legion-kit
node ./scripts/smoke.mjs
npm run legion:eval
node ./scripts/refresh-external-catalog.mjs --check
node ./scripts/refresh-frontend-catalog.mjs --check
node ./scripts/refresh-frontend-reference-index.mjs --check
node ./scripts/refresh-content-catalog.mjs --check
node ./installer/install.mjs --dry-run
node ./installer/install.mjs
agy plugin validate /home/mrz/.gemini/antigravity-cli/plugins/centurion-legion
agy plugin list
```

To install the rules into a specific workspace:

```bash
node ./installer/install.mjs --workspace-agent /path/to/project/.agent
```

To ask Antigravity to register the MCP server directly:

```bash
node ./installer/install.mjs --register-mcp
```

To skip the Antigravity CLI plugin during install:

```bash
node ./installer/install.mjs --no-cli-plugin
```

To copy plugin files without registering them through `agy plugin install`:

```bash
node ./installer/install.mjs --skip-agy-install
```

The default install updates two local surfaces and registers the CLI plugin through `agy plugin install`:

- IDE: `/home/mrz/.gemini/antigravity/agent` and `/home/mrz/.gemini/antigravity/mcp_config.json`, including `centurion-legion` and `serena` MCP entries.
- CLI: `/home/mrz/.gemini/antigravity-cli/plugins/centurion-legion`, registered in the active `agy` plugin registry and verified with `agy plugin list`.

## MCP Tools

- `mission_prep`: returns Recon -> Action -> Probatio -> Report plan.
- `select_legionary`: maps a task to one owner plus conditional handoffs.
- `load_skill_brief`: reads a short brief from `/home/mrz/.agents/skills/<skill>/SKILL.md`.
- `war_room`: emits an adversarial Prosecutor / Advocate / Judge plan.
- `quality_gate`: returns proof checks by change type.
- `external_skill_sources`: returns the curated external source catalog from this kit.
- `external_skill_intake`: returns a safe action, blockers, and next workflow for one curated GitHub candidate.
- `frontend_sources`: returns the curated frontend, landing, motion, and iGaming source catalog.
- `frontend_source_intake`: returns a safe action, blockers, Legion route, and next workflow for one frontend candidate.
- `frontend_reference_search`: searches implemented page, block, template, visual-gallery, and product-flow references for a user UI request.
- `content_sources`: returns the curated content design, UX-writing, product-language, and copywriting source catalog.
- `content_source_intake`: returns a safe action, blockers, Legion route, and next workflow for one content/copy candidate.
- `agy_delegation_brief`: returns a safe delegation brief for using `agy` as AUXILIUM AGY without changing the primary Legionary owner.
- `serena`: external MCP tool available to Antigravity IDE and `agy` for project symbol navigation, diagnostics, and symbol-scoped edits. It is installed with `--context codex` to avoid overlapping shell and broad file tools.

## AUXILIUM AGY

`agy` is a recruited auxiliary executor, not a Legionary owner. Use it only after the primary owner has narrowed the task to exact files, non-goals, proof commands, and acceptance criteria.

Best fits are frontend/UI slices, reference summaries, UX copy variants, documentation drafts, focused tests, and small reproducible fixes. Do not delegate secrets, credentials, production deploys, destructive commands, wallet/payment/KYC flows, exploit execution, or final architecture/security/legal/product-risk judgment.

Acceptance rule: require `agy` to self-review, fix confirmed defects, rerun proof, and report canonical `selfReview.performed=true` for a done result. Then inspect the diff or artifact directly and rerun owner proof before claiming completion.

For implementation tasks, use `AGY_ORDER v1` with a fresh safe `orderId`: take a controller-custody snapshot with `scripts/agy-order-guard.mjs` at an explicit absolute path outside the workspace, pass `agy` exact allowed paths, non-goals, forbidden patterns, and proof commands, require the namespaced `AGY_RESULT.json`, then verify scope and result shape with the guard before accepting. In-workspace snapshots are rejected. The detached digest catches ordinary tampering but does not authenticate against a same-UID writer that can rewrite both custody files; that requires an external controller/OS boundary. This is model-agnostic and does not depend on a specific Gemini version being perfectly obedient.

By default, `AGY_RESULT.json` must be canonical `AGENT_RESULT_JSON_V1` with the matching `orderId`, `executor=agy`, and object-shaped result fields. The bundled shared contract lives in `legion-contracts/`; `agy-order-guard.mjs` still owns snapshot, allowed-path, reported-scope, and forbidden-pattern enforcement. Every controller artifact is derived under `<workspace>/.centurion/agents_results/<orderId>/`; root-level result or snapshot paths are rejected before reading or writing.

```json
{
  "resultVersion": "AGENT_RESULT_JSON_V1",
  "orderId": "<orderId>",
  "executor": "agy",
  "status": "done",
  "summary": "...",
  "filesChanged": [{ "path": "relative/path", "action": "modified" }],
  "artifacts": [{ "path": "relative/path", "exists": true, "type": "...", "note": "..." }],
  "proof": [{ "command": "...", "cwd": "<workspace>", "status": "pass", "exitCode": 0, "summary": "..." }],
  "selfReview": { "performed": true, "findings": [], "fixesApplied": [] },
  "scopeDeviations": [],
  "forbiddenPatternHits": [],
  "remainingRisks": [],
  "questions": [],
  "errors": [],
  "stdoutSummary": "",
  "stderrSummary": ""
}
```

Legacy compatibility is explicit: add `--allow-legacy` to `verify` only for the previous `AGY_ORDER_V1` result payload. Default verification rejects legacy-only and hybrid payloads. The compatibility flag does not bypass self-review, reported-scope, forbidden-pattern, or snapshot checks.

When this kit is maintained inside `centurionCLI`, use the repo path as the source of truth:

```bash
node integrations/antigravity-legion-kit/scripts/agy-order-guard.mjs snapshot --workspace <path> --order-id <orderId> --out /controller/custody/<orderId>/AGY_SNAPSHOT.json
node integrations/antigravity-legion-kit/scripts/agy-order-guard.mjs verify --workspace <path> --order-id <orderId> --before /controller/custody/<orderId>/AGY_SNAPSHOT.json --allowed <paths> --result .centurion/agents_results/<orderId>/AGY_RESULT.json --forbidden <patterns>
```

## Security Notes

- The MCP bridge is local-only and exposes no shell execution tool.
- Serena is an MCP tool, not a Legionary. It should be used only when symbol-aware code navigation or symbol-scoped edits reduce risk; it must not replace the single-owner routing model.
- The installer updates JSON on disk and can optionally call `antigravity-ide --add-mcp`.
- Existing third-party MCP servers in user config are not modified.
- Inline secrets in existing MCP configs should be moved to environment variables before sharing the config.
- External GitHub skills are cataloged as discovery sources only. Do not run external installers or bulk-import skill packs without a separate audit.
- Frontend reference-search sources are discovery inputs only. Do not copy visual galleries pixel-for-pixel, use paid templates without license access, or import full starters into existing apps without architecture review.
- Frontend templates and iGaming projects are cataloged as references only. Do not reuse gambling, wallet, deposit, bonus, or KYC flows without GUARDIAN review and responsible-gaming checks.
- Content and copywriting sources are cataloged as discovery references only. Do not copy sales text, testimonials, scarcity, urgency, guarantees, pricing, legal, finance, health, betting, or iGaming claims without CENSOR/GUARDIAN review.

## Validation

```bash
node ./scripts/smoke.mjs
npm run catalog:check
npm run frontend-catalog:check
npm run frontend-reference:check
npm run content-catalog:check
agy plugin validate ./agy-plugin
```

The smoke check verifies required rules/workflows/skills, the `agy` CLI plugin shape, Antigravity's local MCP schema, package bins, external/frontend/reference/content catalog JSON, a stdio MCP initialize/tools/call round trip, full 37-owner Legion routing coverage, AUXILIUM AGY delegation guards, `AGY_ORDER` scope verification, shared Legion result-contract compatibility, and a temporary installer run for both IDE and CLI targets. `npm run legion:eval` prints the routing matrix and should report all cases passing with `37/37 owners covered`; the case count may exceed 37 because high-risk regression guards are included without adding owners.

## External Catalog Refresh

```bash
npm run catalog:refresh
```

This command reads GitHub repository metadata and tree paths for the fixed candidate list, then rewrites `docs/EXTERNAL_CATALOG.md` and `docs/external-catalog.json`. It does not clone repositories, run installers, install packages, or execute third-party code.

## Frontend Catalog Refresh

```bash
npm run frontend-catalog:refresh
```

This command reads GitHub repository metadata and tree paths for the fixed frontend candidate list, then rewrites `docs/FRONTEND_CATALOG.md` and `docs/frontend-catalog.json`. If GitHub rate-limits unauthenticated API calls, the catalog is still written with explicit metadata-inspection blockers instead of treating the source as verified.

## Frontend Reference Index Refresh

```bash
npm run frontend-reference:refresh
```

This command rewrites `docs/FRONTEND_REFERENCE_INDEX.md` and `docs/frontend-reference-index.json` from a fixed curated source list. It keeps reference search local and deterministic; it does not clone repositories, scrape galleries, install packages, or execute third-party code.

## Content Catalog Refresh

```bash
npm run content-catalog:refresh
```

This command reads GitHub repository metadata and tree paths for the fixed content/copy candidate list, then rewrites `docs/CONTENT_COPY_CATALOG.md` and `docs/content-copy-catalog.json`. If GitHub rate-limits unauthenticated API calls, the catalog is still written with explicit metadata-inspection blockers and claim-safety guidance.
