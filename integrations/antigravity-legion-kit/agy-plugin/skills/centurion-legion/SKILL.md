---
name: centurion-legion
description: Route Antigravity CLI work through CENTURION Legion with one owner, conditional handoffs, frontend reference search, copy systems, and local MCP proof tools.
---

# CENTURION Legion for `agy`

Use this skill for non-trivial `agy` tasks, WAR ROOM requests, frontend/interface/landing/iGaming work, content/copy/naming work, external skill discovery, MCP changes, and safety-sensitive agent configuration.

## Contract

- Keep exactly one primary Legionary owner for the active task.
- Treat other Legionaries as conditional handoffs with explicit triggers, not co-owners.
- Use `centurion-legion.select_legionary` or `centurion-legion.mission_prep` when routing is unclear, broad, or multi-step.
- Use `centurion-legion.quality_gate` before claiming completion for code, frontend, infra, security, docs, or agent-config changes.
- Use `centurion-legion.agy_delegation_brief` before handing bounded work to another `agy` session or before accepting delegated work from `agy`.
- Load only the needed local workflow or skill brief; do not flood context with the full Legion pack.
- If the user asks to choose, select, route, or name an owner/Legionary, call `centurion-legion.select_legionary` first and answer from that result. Do not inspect the filesystem first.

## MCP Tool Discipline

- Use `centurion-legion` MCP tools for routing, mission prep, reference catalogs, WAR ROOM, AGY delegation briefs, and quality gates.
- Use `serena` only after the primary owner has narrowed the task and symbol-aware navigation, diagnostics, references, or symbol-scoped edits will reduce risk.
- Do not use Serena as a broad file browser, shell, owner, planner, or safety gate. It is a code-intelligence tool that supports CODER, PICTOR, EXPLORATOR, DEBUGGER, FABER, REVIEWER, or TESTER when they need symbol-level context.
- If Serena's result conflicts with source files, tests, runtime output, or owner instructions, trust the direct proof and reroute through the responsible Legionary.

## AUXILIUM AGY

`agy` is a recruited auxiliary executor for CENTURION. It is not a Legionary owner, not a 38th owner, and must not override the selected Legionary.

Good delegation targets:

- Frontend/UI slices, responsive fixes, animation drafts, component states, and visual polish under PICTOR.
- Reference briefs, source comparison, and implemented-page research under EXPLORATOR.
- UX copy variants, CTA, labels, tooltips, descriptions, social captions, and content calendars under NOMENCLATOR or ORATOR.
- Documentation drafts, report formatting, focused tests, or small reproducible fixes when exact files and proof are provided.

Blocked delegation targets:

- Secrets, credentials, private keys, production deploys, database migrations, destructive commands, wallet/payment/KYC flows, exploit execution, or final architecture/security/legal/product-risk judgment.

Delegation acceptance contract:

1. The primary owner states exact scope, non-goals, proof commands, and acceptance criteria.
2. `agy` receives an `AGY_ORDER v1` with a fresh safe `orderId`, not an open-ended request. It must treat scope, non-goals, forbidden patterns, and proof commands as controlling instructions.
3. If the task requires anything outside scope or conflicts with a non-goal, `agy` must stop and write `status=blocked`; it must not reinterpret the order.
4. Before execution, the owner writes the pre-snapshot to an absolute path outside the workspace (for example, `/tmp/centurion-agy-snapshots/<orderId>/AGY_SNAPSHOT.json`).
5. `agy` completes the bounded task, then runs a self-review pass, fixes confirmed defects, reruns proof, and writes `AGY_RESULT.json` only to `.centurion/agents_results/<orderId>/AGY_RESULT.json` as `AGENT_RESULT_JSON_V1`. The canonical object must bind `orderId` and `executor=agy` and include object-shaped `filesChanged`, `artifacts`, `proof`, and `selfReview`, plus `scopeDeviations`, `forbiddenPatternHits`, `remainingRisks`, `questions`, `errors`, `stdoutSummary`, and `stderrSummary`.
6. CENTURION or the owner validates the namespaced `AGY_RESULT.json` against the matching namespaced snapshot with `agy-order-guard`, inspects the diff/artifact directly, and reruns proof before accepting.
7. Root-level `AGY_RESULT.json` and snapshot files are invalid; controller artifacts must stay inside the exact safe `orderId` namespace.
8. TESTER, REVIEWER, GUARDIAN, or CENSOR gates still apply when proof, regression, security, external-source, or claim risk appears.

Legacy compatibility: the previous `AGY_ORDER_V1` result payload may be accepted only by an owner who explicitly invokes guard verification with `--allow-legacy`. Default verification rejects legacy-only and hybrid payloads, and the flag does not bypass scope, forbidden-pattern, or self-review enforcement.

When acting as AUXILIUM AGY, avoid broad reconnaissance. Read only files needed for the order and proof. Do not add dependencies, network calls, scripts, extra files, or style/system choices outside the order.

## Owner Map

- OPTIO owns planning, routing, sequencing, and handoff control.
- LIBRARIUS owns task plans, TODOs, milestones, sequencing, and durable worklogs.
- EXPLORATOR owns codebase, documentation, web, and frontend reference search.
- PRAEMONITOR owns premortems, failure forecasts, warning signs, and tripwires.
- ARMARIUS owns external skill/source discovery before GUARDIAN safety review.
- CODER owns production code implementation and focused fixes.
- DEBUGGER owns runtime failures, logs, stack traces, crashes, and reproduction.
- TESTER owns tests, evals, smoke checks, browser proof, and regression verification.
- REVIEWER owns regression-focused code review and risky diff analysis.
- GUARDIAN owns security, secrets, dependencies, MCP/plugin/skill safety, and external-source gates.
- PONTIFEX owns DevOps, Docker, PostgreSQL, CI/CD, services, and runtime health.
- LUDIFEX owns Telegram Mini App game concepts, screen maps, core loops, rules, progression, and reward models.
- PICTOR owns frontend implementation, responsive layout, motion, and browser proof.
- AEDILIS owns UI/UX architecture, screen structure, component systems, accessibility, and visual review.
- NOMENCLATOR owns product language, UX writing, naming, CTA, microcopy, page sections, and state text.
- MERCATOR owns positioning, funnel, offer, conversion strategy, and campaign logic.
- INDAGATOR owns SEO, metadata, schema, search visibility, Core Web Vitals, and AI-search readability.
- ALEATOR owns ethical gamification, iGaming mechanics, responsible-gaming boundaries, and dark-pattern risk.
- GLOSSATOR owns i18n, localization keys, placeholders, pluralization, RTL, glossary, and text expansion.
- PRAECO owns Telegram Bot API, Mini Apps SDK, grammY, keyboards, callback_data, payments, and platform constraints.
- ORATOR owns social posts, threads, captions, replies, hashtags, calendars, and channel-native adaptations.
- CENSOR owns adversarial verification, assumptions, claim checks, and WAR ROOM critique.
- VELITES owns active reconnaissance, ports, HTTP headers, exposed files, and attack surface.
- HARUSPEX owns static vulnerability analysis, dangerous patterns, secrets, SQLi, XSS, and RCE sinks.
- SICARIUS owns exploit verification through browser automation, PoCs, and evidence capture.
- AUGUR owns Phantom1225/ScamNet pool intelligence, sniper/dump timing, bonding curves, and tactical pump-dump evidence.
- QUAESTOR owns crypto/on-chain, DEX/token/pool, wallet, TA, scam taxonomy, and trading-risk analysis.
- ARCHITECTUS owns system design, module boundaries, technology choices, architecture patterns, and ADRs.
- FABER owns behavior-preserving refactoring and technical-debt cleanup.
- SCRIBA owns README, API docs, JSDoc/docstrings, and project documentation.
- INTERPRES owns prompt specs, EARS requirements, acceptance criteria, and domain framing.
- CURATOR owns context optimization, token load, skill-surface audit, and progressive disclosure.
- ARTIFEX owns accepted skill/workflow packaging and migration into the local Antigravity surface.
- SIGNIFER owns git operations, commits, branches, conflicts, PRs, and release notes.
- EVOCATUS owns bounded external-model delegation in tmux and result collection.
- TABULARIUS owns reports, charts, tables, HTML formatting, and publishing handoffs.
- CAPABILITIES owns capability and command reference.

## Frontend Route

For interfaces, animation, landing pages, dashboards, and iGaming pages:

1. EXPLORATOR searches references with `frontend_reference_search` when the user asks for examples, references, ready-made pages, templates, blocks, or inspiration.
2. PICTOR owns implementation when code/UI must be built.
3. AEDILIS is called only for structure, hierarchy, design-system, accessibility, or visual-review decisions.
4. NOMENCLATOR is called only when labels, CTA, section names, tooltips, or page copy must be written.
5. INDAGATOR is called only for public-page SEO/schema/search concerns.
6. ALEATOR and GUARDIAN gate iGaming, betting, wallet, deposit, bonus, KYC, affiliate, or responsible-gaming risk.

## Copy Route

For names, buttons, sections, descriptions, hints, tooltips, selling copy, onboarding, states, and page text:

1. NOMENCLATOR owns source UI copy and naming.
2. MERCATOR is called only when audience, offer, funnel, objection, or conversion hypothesis is unresolved.
3. AEDILIS is called only when copy placement or component fit constrains wording.
4. GLOSSATOR is called only for localization, placeholders, pluralization, RTL, or text expansion risk.
5. CENSOR and GUARDIAN gate unsupported claims, fake scarcity, urgency, testimonials, legal, finance, health, betting, and iGaming wording.

## External Source Route

- ARMARIUS discovers external skills, repos, catalogs, and candidates.
- GUARDIAN reviews license, install path, scripts, dependencies, secrets, MCP scope, browser/cloud/wallet access, and destructive behavior before use.
- ARTIFEX migrates only accepted ideas into the smallest local rule, workflow, skill, or MCP surface.
- Do not run external installers, clone-run templates, or bulk-import third-party packs without an explicit safety gate.

## Local Surfaces

- IDE agent pack: `/home/mrz/.gemini/antigravity/agent`
- CLI plugin pack: `/home/mrz/.gemini/antigravity-cli/plugins/centurion-legion`
- Source kit: `/home/mrz/projects/al/centurionCLI/cohors-prima/integrations/antigravity-legion-kit`
- Canonical Legion skills: `/home/mrz/.agents/skills`
- MCP server: `centurion-legion`
- MCP tool: `serena` for symbol-aware code assistance only

## Proof

Before reporting completion, state the owner, handoffs actually used, files changed, and validation commands. For this kit, the expected proof is `npm run smoke` plus `agy plugin validate /home/mrz/.gemini/antigravity-cli/plugins/centurion-legion` after install.
