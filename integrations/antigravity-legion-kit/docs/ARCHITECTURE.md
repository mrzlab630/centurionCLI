# Architecture

## Decision

Use Antigravity's documented extension surfaces before touching IDE internals:

1. Rules and workflows under `.agent` / `.agents` paths.
2. MCP server definitions in `mcp_config.json`.
3. Antigravity CLI plugins under `~/.gemini/antigravity-cli/plugins` for `agy`.
4. Optional VSIX only if rules/workflows/MCP/CLI plugin surfaces are insufficient.

## Rationale

The local Antigravity install exposes custom editors for `.agent/rules/**/*.md` and `.agent/workflows/**/*.md`, plus JSON validation for `mcp_config.json`. That gives a stable integration path that survives IDE updates better than patching `/opt/antigravity`.

## Components

- `agent/`: portable prompt and workflow assets for Antigravity.
- `mcp-server/`: dependency-free stdio JSON-RPC bridge for Legion routing.
- `agy-plugin/`: compact Antigravity CLI plugin for `agy`; it exposes one routing skill and a plugin-local `mcp_config.json` for `centurion-legion`.
- `installer/`: copies IDE assets, writes IDE MCP config, installs the `agy` CLI plugin, and registers it through `agy plugin install`.
- `scripts/smoke.mjs`: deterministic proof that the package is internally usable.
- `docs/EXTERNAL_CATALOG.md`: vetted discovery notes for external Antigravity-native skills and packs.
- `docs/external-catalog.json`: structured external-candidate metadata used by MCP intake recommendations.
- `docs/FRONTEND_CATALOG.md`: vetted discovery notes for frontend skills, landing templates, motion catalogs, component catalogs, and iGaming references.
- `docs/frontend-catalog.json`: structured frontend-candidate metadata used by MCP intake recommendations.
- `docs/FRONTEND_REFERENCE_INDEX.md`: local searchable index of implemented pages, blocks, templates, visual galleries, and product-flow references.
- `docs/frontend-reference-index.json`: structured reference metadata used by the `frontend_reference_search` MCP tool.
- `docs/CONTENT_COPY_CATALOG.md`: vetted discovery notes for content design, UX writing, product language, copywriting, prompt, and experimentation references.
- `docs/content-copy-catalog.json`: structured content/copy candidate metadata used by MCP intake recommendations.
- `agent/workflows/agy-delegation.md`: AUXILIUM AGY delegation protocol for bounded external execution with owner-side acceptance gates.

## Non-Goals

- No patching bundled Antigravity extension files.
- No replacement of Antigravity's model picker.
- No remote code execution MCP tools.
- No duplication of canonical Legion skills from `/home/mrz/.agents/skills`.
- No bulk installation of external skill packs without a separate safety audit.
- No treating the external catalog as a trusted source or install allowlist.
- No treating frontend templates, component catalogs, or iGaming repositories as install allowlists.
- No copying visual-gallery pages pixel-for-pixel or treating screenshots as reusable product assets.
- No use of paid templates or private libraries without confirmed license access.
- No importing full starters into existing apps without architecture review and explicit user approval.
- No reuse of gambling, wallet, deposit, withdrawal, bonus, affiliate, or KYC flows without GUARDIAN review.
- No treating content style guides, sales-copy examples, prompt catalogs, or swipe files as trusted final product copy.
- No copying testimonials, review counts, scarcity, urgency, guarantees, pricing, legal, finance, health, betting, or iGaming claims without CENSOR/GUARDIAN review.
- No multi-owner execution model. Each task has one owner; other Legionaries are conditional handoffs or gates.
- No treating `agy` as a task owner. It is an auxiliary executor only and cannot accept secrets, production deploys, destructive commands, wallet/payment/KYC flows, exploit execution, or final risk judgment.

## Routing Direction

The kit uses a single-owner routing model. `mission_prep` and `select_legionary` return one `owner` plus `handoffs` with explicit triggers. Workflows describe owner selection and handoff triggers rather than shared ownership. This matches Antigravity's agent workflow better than committee-style routing because one agent keeps task state while calling specialists only when a capability is missing.

## Antigravity CLI Direction

`agy` uses `~/.gemini/antigravity-cli` as its config root. The installed Legion plugin lives at `~/.gemini/antigravity-cli/plugins/centurion-legion` and the active CLI registry is verified with `agy plugin list`. A local `import_manifest.json` fallback is written only when installation is run with `--skip-agy-install`.

The CLI plugin deliberately exposes one compact `centurion-legion` skill instead of one command per Legionary. That keeps routing centralized: the active task still has one owner, and the MCP server supplies reference search, content catalogs, external-source intake, routing, WAR ROOM, and quality-gate tools on demand.

## AUXILIUM AGY Direction

`agy` is integrated as `AUXILIUM AGY`, a recruited auxiliary executor. It is useful for bounded frontend/UI slices, reference summaries, UX copy variants, documentation drafts, focused tests, and small reproducible fixes where the primary owner can define exact scope and proof.

The primary owner remains accountable for the task. Before delegation, the owner should call `agy_delegation_brief` or follow `agent/workflows/agy-delegation.md` to define files, non-goals, proof commands, and acceptance criteria. `agy` must run a self-review/fix/rerun pass and return `SELF_REVIEW_FIXED=<yes/no>`. The owner then inspects the diff or artifact and reruns proof locally before reporting success.

This intentionally avoids a recursive agent hierarchy where `agy` becomes another planner with unclear authority. It is a tool for parallel execution and second-pass critique, not an owner, approver, or security gate.

For stronger obedience across Gemini model versions, implementation delegation uses `AGY_ORDER v1`: a bounded order with allowed paths, non-goals, forbidden patterns, proof commands, and required `AGY_RESULT.json`. The owner verifies the result with `scripts/agy-order-guard.mjs`, so acceptance depends on observed filesystem changes and structured proof rather than model self-reporting alone.

## Frontend Direction

Frontend, landing-page, motion, and iGaming work enters through `agent/workflows/frontend-landing-igaming.md`. PICTOR owns implementation by default. AEDILIS, INDAGATOR, MERCATOR, ALEATOR, GUARDIAN, and TESTER are conditional handoffs when their specific capability is needed.

The frontend catalog is a discovery layer for source ideas. It records GitHub metadata when available, but if GitHub rate-limits inspection the generated JSON keeps explicit metadata blockers instead of presenting the source as verified.

## Reference Search Direction

Frontend reference search sits before UI implementation. `frontend_reference_search` reads `docs/frontend-reference-index.json` and ranks curated sources by request, page type, stack, and style. Antigravity should use it to collect 3-5 distinct references: structural page reference, code/block/component reference, visual direction reference, and product-flow reference when relevant.

The index is deliberately local and deterministic. It does not live-scrape galleries, clone repositories, run template installers, or grant permission to copy external work. EXPLORATOR owns search; AEDILIS, PICTOR, NOMENCLATOR, INDAGATOR, GUARDIAN, and TESTER are called only when the reference brief needs their capability.

## Content Direction

Content, UX-writing, naming, CTA, microcopy, state text, and conversion-copy work enters through `agent/workflows/content-copy-system.md`. NOMENCLATOR owns product language by default. MERCATOR, AEDILIS, GLOSSATOR, INDAGATOR, CENSOR, and PICTOR are conditional handoffs when their specific capability is needed.

The content catalog is a discovery layer for writing systems and copy patterns. It does not make external copy trustworthy. Generated intake keeps license, hidden-source, metadata, high-risk surface, and claim-safety blockers visible before any source influences product text.

## Future Integration Path

The official `google-antigravity/antigravity-sdk-python` repository exposes a skill for building programmatic Antigravity SDK agents. That is a separate integration track from this kit's current `.agent` and MCP bridge. Treat it as future work requiring dependency, credential, and runtime review before use.

## Proof Contract

A change to this kit is not complete until `node ./scripts/smoke.mjs` passes. For installed CLI state, also validate `agy plugin validate /home/mrz/.gemini/antigravity-cli/plugins/centurion-legion`.
