# External Antigravity Skill Sources

Generated: 2026-06-12T20:39:58.712Z

This catalog records GitHub repositories found during the Antigravity skill search. It is a discovery aid, not an install allowlist.

## Safety Policy

- Do not run external installers or `npx` commands from this catalog without a separate audit.
- Prefer `adapt-only` unless a repository contains a small, inspectable, license-compatible asset that fills a specific gap.
- Large skill packs can increase token load and accidental activation. Install narrowly.
- MCP servers, SDKs, and helper scripts require extra review for filesystem, shell, browser, cloud, wallet, database, and credential access.

## Candidates

| Repository | Type | License Signal | Useful Assets | Safety Decision | Notes |
| --- | --- | --- | --- | --- | --- |
| `rmyndharis/antigravity-skills` | skill-library | MIT | `catalog.json`, `bundles.json`, 300+ `skills/*/SKILL.md` | adapt-only | Strong discovery catalog and token-efficiency warning; do not install all skills. Stars: 834; pushed: 2026-05-02T03:24:46Z. |
| `rominirani/antigravity-skills` | skill-library | no GitHub license signal observed | `skills_tutorial/*/SKILL.md` | adapt-only | Good examples for basic routing, assets, few-shot examples, deterministic scripts. Stars: 263; pushed: 2026-06-12T06:28:08Z. |
| `google-antigravity/antigravity-sdk-python` | mcp-or-sdk | Apache-2.0 | `skills/google-antigravity-sdk/SKILL.md`, SDK references/examples | reference-only | Future path for programmatic agents; PyPI package install needs separate approval. Stars: 1666; pushed: 2026-06-11T20:15:49Z. |
| `bonnguyenitc/antigravity-superpowers` | native-agent-pack | MIT | `.agent/rules`, `.agent/workflows`, focused planning/review/verification skills | adapt-only | Useful development loop patterns; contains scripts and npm init path, so do not run installer blindly. Stars: 16; pushed: 2026-05-08T05:08:36Z. |
| `anhtester/antigravity-testing-kit` | native-agent-pack | MIT | QA rules, flaky-test workflow, automation/testing skills | adapt-only | Strong QA patterns; scripts include Jira/Google Sheets integrations requiring credentials. Stars: 110; pushed: 2026-05-20T20:05:22Z. |
| `tknvstp/antigravity-skills` | native-agent-pack | NOASSERTION | `.agent/workflows/skill-creator.md`, `.agent/workflows/skill-migrator.md` | adapt-only | Useful Antigravity migration decision trees; language is Chinese. Stars: 54; pushed: 2025-12-29T07:57:18Z. |
| `WilkoMarketing/antigravity-n8n-skills` | skill-library | no GitHub license signal observed | seven `SKILL.md` files for n8n | needs-approval | Domain-specific; likely useful only for n8n projects with MCP/tooling. Stars: 87; pushed: 2026-06-01T16:19:03Z. |
| `sabahattink/antigravity-fullstack-hq` | skill-library | MIT | skills/workflows/agents | needs-approval | Installer writes global `.gemini` and `.claude`; overlaps with local Legion. Stars: 27; pushed: 2026-05-15T09:18:52Z. |
| `krishnakanthb13/everything-antigravity` | native-agent-pack | NOASSERTION | `.agent/workflows`, `skills`, rules docs | needs-approval | Installer writes global directories and includes many workflows; sample selectively only. Stars: 80; pushed: 2026-02-09T05:45:37Z. |
| `adamreger/ecc-antigravity` | mcp-or-sdk | MIT | workflows, skills, rules, MCP configs | adapt-only | Marked pre-production; uses `.antigravity` paths that do not match this host's observed `.agent` selectors. Stars: 2; pushed: 2026-02-27T01:07:23Z. |

## Patterns Worth Adapting

- Evidence before claims: always run fresh proof before completion claims.
- Skill creator/migrator: classify rule vs workflow vs resource vs MCP before adding assets.
- Selective catalogs: use catalogs to discover one skill, not bulk install hundreds.
- QA routing: split manual test design, automation generation, locator healing, and flaky-test analysis.
- Programmatic agents: evaluate official `google-antigravity` SDK separately for future multi-agent orchestration.

## Blocked Defaults

- Bulk `install --all` for large skill packs.
- Running external update scripts from `.agent/.shared` or installer scripts without review.
- Copying helper scripts that require credentials or write to third-party systems.
- Adopting `.antigravity` directory layouts until verified against the current Antigravity version on this host.
