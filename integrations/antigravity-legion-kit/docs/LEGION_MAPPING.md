# Legion Mapping

| Legionary | Antigravity Surface | Primary Use |
| --- | --- | --- |
| OPTIO | `mission_prep`, rules | Plan, route, sequence, define proof |
| LIBRARIUS | `select_legionary`, rules | TODOs, milestones, backlog, durable worklog |
| EXPLORATOR | `frontend_reference_search`, workflows | Codebase, documentation, web, and reference research |
| PRAEMONITOR | `war_room` | Premortem, failure forecasts, tripwires |
| ARMARIUS | `external_skill_sources`, `external_skill_intake` | External skill and source discovery before safety review |
| CODER | workflows, skill brief | Implement focused code changes |
| DEBUGGER | `select_legionary`, workflows | Runtime failures, logs, stack traces, crashes, reproduction |
| TESTER | `quality_gate`, workflows | Tests, evals, smoke checks |
| REVIEWER | workflows | Regression and diff review |
| GUARDIAN | rules, `quality_gate` | Security, secrets, MCP safety |
| PONTIFEX | ops workflows | Runtime, DB, CI/CD, service health |
| LUDIFEX | `select_legionary`, workflows | Telegram Mini App game concepts, screens, loops, rewards |
| AEDILIS | design workflows | UX structure, screen architecture, component systems, accessibility |
| NOMENCLATOR | `content-copy-system` | Product language, naming, CTA, UX copy, microcopy, glossary |
| GLOSSATOR | `content-copy-system` | Localization readiness, placeholders, plural rules, text expansion |
| PRAECO | `select_legionary`, workflows | Telegram Bot API, Mini Apps SDK, grammY, keyboards, payments |
| ALEATOR | `frontend-landing-igaming` | Ethical gamification, responsible-gaming, dark-pattern review |
| MERCATOR | `frontend-landing-igaming` | Positioning, funnel, conversion hypothesis, CTA strategy |
| PICTOR | frontend workflows | UI implementation, responsive layout, motion, browser proof |
| ORATOR | `select_legionary`, workflows | Social posts, threads, captions, replies, hashtags, calendars |
| INDAGATOR | `frontend-landing-igaming` | Landing SEO, schema, Core Web Vitals, AI-search readability |
| ARCHITECTUS | `mission_prep` | Boundaries, ADRs, system design |
| FABER | `select_legionary`, workflows | Behavior-preserving refactoring and technical-debt cleanup |
| SCRIBA | docs workflow | README, API docs, project documentation |
| INTERPRES | `select_legionary`, workflows | Prompt specs, EARS requirements, acceptance criteria, domain framing |
| CURATOR | `select_legionary`, workflows | Context optimization, token load, skill-surface audit, drift checks |
| ARTIFEX | `external_skill_intake`, workflows | Skill creation, migration, and packaging |
| SIGNIFER | `select_legionary`, workflows | Git operations, commits, branches, conflicts, PRs |
| CENSOR | `war_room` | Adversarial verification |
| VELITES | `select_legionary`, workflows | Active reconnaissance, ports, HTTP headers, attack surface |
| HARUSPEX | `select_legionary`, workflows | Static vulnerability analysis, dangerous patterns, SAST candidates |
| SICARIUS | `select_legionary`, workflows | Exploit verification, browser automation, PoC evidence |
| AUGUR | `select_legionary`, workflows | Phantom1225, ScamNet, pump/dump, sniper timing, pool intelligence |
| QUAESTOR | `select_legionary`, workflows | Crypto/on-chain, DEX/token/pool, wallet, trading-risk analysis |
| EVOCATUS | `select_legionary`, workflows | External-model delegation in tmux and result collection |
| TABULARIUS | `select_legionary`, workflows | Reports, charts, tables, HTML publishing handoffs |
| CAPABILITIES | `select_legionary`, docs | Capability and command reference |

The MCP bridge returns compact routing output. Full skill instructions remain in `/home/mrz/.agents/skills` and should be loaded only when needed.

## Auxiliary Executor

| Auxiliary | Surface | Primary Use |
| --- | --- | --- |
| AUXILIUM AGY | `agy_delegation_brief`, `agent/workflows/agy-delegation.md` | Bounded delegated execution after a Legionary owner defines scope, non-goals, proof, and acceptance criteria. |

`AUXILIUM AGY` is deliberately outside the owner matrix. It may execute a slice for OPTIO, PICTOR, EXPLORATOR, NOMENCLATOR, ORATOR, SCRIBA, TESTER, DEBUGGER, or another owner, but it never becomes the owner of the task.

## Antigravity IDE and CLI Surface

`agy` receives the Legion through one plugin: `/home/mrz/.gemini/antigravity-cli/plugins/centurion-legion`.
The IDE receives the Legion through `/home/mrz/.gemini/antigravity/agent` and `/home/mrz/.gemini/antigravity/mcp_config.json`.

| Plugin Component | Purpose |
| --- | --- |
| `skills/centurion-legion/SKILL.md` | Compact single-owner routing and handoff rules for CLI sessions. |
| `mcp_config.json` | Registers the local `centurion-legion` MCP server for routing, catalogs, reference search, WAR ROOM, and quality gates, plus Serena for symbol-aware code assistance in IDE and CLI surfaces. |
| `plugin.json` | Enables the plugin under the Antigravity CLI plugin manager. |

The CLI plugin is intentionally compact. It does not duplicate every workflow as a separate command because that would create overlapping entry points; the owner selects the needed workflow through MCP or the installed IDE agent pack.

Serena is a tool surface, not an owner. Use it only after the owner has narrowed the task and symbol-level navigation, diagnostics, or symbol-scoped edits would reduce risk. It must not be used to bypass GUARDIAN/TESTER/REVIEWER gates or to perform broad shell/file operations.

## Routing Contract

Every task has exactly one owner. Handoffs are conditional, bounded, and return control to the owner. Gate owners such as GUARDIAN, CENSOR, TESTER, and REVIEWER may block completion, but they do not become implementation owners unless the task changes.

Delegating to `AUXILIUM AGY` does not change ownership. The owner must give `agy` exact scope and proof, require self-review/fix/rerun, then inspect the artifact and rerun proof before acceptance.

## AGY Delegation Gate

| Step | Required Action |
| --- | --- |
| Fit check | Use `agy_delegation_brief` for non-trivial delegation; avoid secrets, production deploys, destructive commands, wallet/payment/KYC flows, exploit execution, and final risk judgment. |
| Delegation | Prompt `agy` with owner, workspace, allowed paths, non-goals, proof commands, and expected output. |
| Self-review | Require `agy` to inspect its own diff/artifact, fix confirmed defects, rerun proof, and report `SELF_REVIEW_FIXED=<yes/no>`. |
| Acceptance | Primary owner inspects files/artifacts directly, reruns proof, and calls TESTER/REVIEWER/GUARDIAN/CENSOR when their gate is triggered. |

## External Skill Intake

| Workflow | Owner | Purpose |
| --- | --- | --- |
| `external-skill-audit` | GUARDIAN | Decide whether an external Antigravity asset is safe to accept, adapt, block, or escalate. |
| `skill-migrator` | ARTIFEX | Convert a source `SKILL.md` or prompt pack into the smallest local Antigravity surface. |

External assets should go through audit before they affect `agent/rules`, `agent/workflows`, `agent/skills`, or MCP config.

## Frontend Source Intake

| Workflow | Owner | Purpose |
| --- | --- | --- |
| `frontend-landing-igaming` | PICTOR by default | Implement frontend UI, animation, landing pages, and approved iGaming UI in the existing stack. |
| `frontend_source_intake` | GUARDIAN | Decide how to use one cataloged frontend source: adapt-only, reference-only, needs-approval, or blocked. |

Frontend and iGaming sources should go through `frontend_source_intake` before they influence UI code, animation systems, landing sections, casino pages, wallet/deposit flows, or responsible-gaming claims.

## Frontend Reference Search

| Workflow | Owner | Purpose |
| --- | --- | --- |
| `frontend-reference-search` | EXPLORATOR | Find 3-5 implemented references, assign each a role, and produce the reference brief before design or build work. |
| `frontend_reference_search` | EXPLORATOR | Search the local reference index by request, page type, stack, and style. |

Reference search should run before new frontend pages, dashboards, landing pages, animated sections, onboarding flows, checkout flows, auth screens, settings pages, product pages, mobile flows, or iGaming UI. Code/block references still need `frontend_source_intake` or GUARDIAN review before copying code; visual galleries and flow galleries are direction only.

## Content Source Intake

| Workflow | Owner | Purpose |
| --- | --- | --- |
| `content-copy-system` | NOMENCLATOR by default | Create naming, CTA, UX copy, product descriptions, hints, states, and conversion copy. |
| `content_source_intake` | CENSOR | Decide how to use one cataloged copy/content source: adapt-only, reference-only, needs-approval, or blocked. |

Content and copywriting sources should go through `content_source_intake` before they influence names, CTA, section titles, tooltips, state copy, sales pages, pricing claims, testimonials, scarcity, urgency, or high-risk legal/payment/iGaming wording.
