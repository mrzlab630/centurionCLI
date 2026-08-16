---
name: aquila-harness-audit
description: Audit Hermes/Aquila harness health across SOUL, skills, bundles, plugins, MCP, Kanban, executor contracts, context budget, and security guardrails before adding or changing agent capabilities. Use when checking agent-surface drift, unsafe plugins/MCP, overlapping skills, broken bundles, or missing delegation gates.
version: 1.0.0
author: Aquila/CENTURION
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [aquila, audit, harness, skills, bundles, plugins, mcp, context, security]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, requesting-code-review, systematic-debugging]
---

# Aquila Harness Audit

Use this skill when checking or improving Hermes as a Team Lead surface. It adapts ECC harness-audit ideas to Hermes-native primitives and must not install external code by itself.

## Activation

Load this when:
- adding or changing Hermes skills, bundles, plugins, MCP servers, hooks, or executor contracts;
- checking if Aquila has overlapping instructions or bloated context;
- investigating agent drift, missing artifacts, unsafe plugins, or MCP overreach;
- preparing a periodic Hermes surface review.

## Audit Scope

| Area | Checks |
| --- | --- |
| SOUL | Team Lead boundary, direct-work override rule, executor hierarchy, result contract, retry policy, runtime model precedence rule. |
| Skills | Trigger clarity, overlap, local/builtin count, missing frontmatter, overly broad skills, stale external imports, `SKILL.md` size over 100,000 chars. |
| Bundles | Recurring workflows encoded as compact slash commands, no skill slug collisions, missing skills skipped intentionally. |
| Plugins/hooks | Opt-in status, arbitrary code risk, env requirements, lifecycle hook blast radius. |
| MCP | Enabled/disabled servers, include/exclude filters, broad filesystem/browser/cloud access, enabled `npx -y` MCP even when version-pinned. |
| Kanban | Durable board use for multi-agent work, available profiles, stuck ready/running/blocked tasks. |
| Contracts | AGENT_ORDER_JSON_V1 and AGENT_RESULT_JSON_V1 schemas, exact artifact paths, proof commands, stop conditions. |
| Context | Heavy always-loaded instructions, duplicate surfaces, verbose skills that should become references. |
| Security | Secrets, credential exfiltration patterns, remote shell installs, destructive commands, broad home access, npm/Python dependency findings. |

## Minimum Command Set

Use read-only commands first:

```bash
hermes --version
hermes skills list
hermes bundles list
hermes plugins list
hermes mcp list
hermes profile list
hermes prompt-size --json
hermes doctor
hermes security audit
rg -n "curl .*\|.*sh|wget .*\|.*sh|base64 -d|eval\(|API_KEY|PASSWORD|SECRET|TOKEN" ~/.hermes ~/.config 2>/dev/null
```

For deterministic local surface checks from this kit:

```bash
node integrations/hermes-legion-kit/scripts/harness-audit.mjs --json
```

That script is read-only. It reports:
- stale or ambiguous model summaries from `config.yaml`, `hermes profile list`, and `hermes prompt-size`;
- missing SOUL rule: runtime model evidence overrides stale profile summaries for the current session;
- enabled `npx -y` MCP servers with owner/risk/proof;
- oversized `SKILL.md` files that should be split into `references/`;
- proof paths for each warning.

Runtime model rule: if `config.yaml`, `hermes profile list`, or `hermes prompt-size` reports one model while active session logs or turn context show an explicit runtime switch or live API calls with another model, classify it as `warn`, not identity conflict. Current-session runtime evidence wins for the current session; persistent config still needs cleanup if it will confuse future preflight/reporting.

MCP supply-chain rule: a package version in `npx -y package@version` reduces drift but does not remove registry execution, cache integrity, or availability risk. Prefer local/pinned binaries for high-trust surfaces; otherwise record owner, package, version, enabled status, and exact config line.

Dependency rule: keep `hermes doctor` npm advisories separate from `hermes security audit` Python findings. Build-tool npm advisories may be warnings; high Python runtime dependencies may be blockers depending on exposure and exploit path.

For contract presence:

```bash
test -f ~/.hermes/contracts/agent-order.schema.json
test -f ~/.hermes/contracts/agent-result.schema.json
test -f ~/.hermes/contracts/examples/agent-order.example.json
test -f ~/.hermes/contracts/examples/agent-result.example.json
```

## Scorecard

Rate each category `pass`, `warn`, or `blocker`:

1. Tool coverage: required executors and MCPs are available.
2. Context efficiency: guidance is in on-demand skills/bundles, not only SOUL.
3. Quality gates: every implementation path has proof commands and independent review when needed.
4. Memory/state: long work uses Kanban or explicit artifacts.
5. Eval coverage: executor routing has repeatable tests or sample tasks.
6. Security guardrails: no unsafe external imports, broad hooks, or secret leakage.
7. Cost/model routing: expensive models reserved for high-value reasoning, fallback policy respected.
8. Git/repo hygiene: dirty trees are inspected and protected before delegation.
9. Runtime model clarity: stale config/profile summaries cannot override live turn-context evidence, and mismatches are reported with proof.
10. Supply-chain posture: enabled remote-execution MCP paths are explicitly owned, versioned, and justified.

## Decision Rules

- Do not bulk-import third-party skills, plugins, hooks, or MCP configs.
- Prefer skill/bundle updates before writing plugins.
- Prefer allowlists over broad MCP tool exposure.
- Keep `SOUL.md` invariant and compact; move optional workflows to skills/bundles.
- If a plugin is proposed, require a separate source review and opt-in enablement.
- If overlap appears, choose one owner and make other skills call or defer to it.

## Output Standard

Return:

```yaml
harness_audit:
  verdict: pass|warn|blocker
  checked:
    skills: true
    bundles: true
    plugins: true
    mcp: true
    contracts: true
    kanban: true
    model_runtime: true
    dependencies: true
  blockers: []
  warnings: []
  top_fixes:
    - owner: aquila|codex|claude|agy|boss
      action: "concrete next step"
      proof: "command or artifact"
```

Never end with a vague "looks good". Every pass needs evidence; every warning needs an owner.
