---
description: Audit external Antigravity skill/rule/workflow/MCP repositories before importing or adapting them.
---

# External Skill Audit Workflow

Use this workflow when evaluating GitHub repositories or packages for Antigravity skills, rules, workflows, MCP servers, or agent packs.

## Owner

GUARDIAN owns the safety decision. Other Legionaries are handoffs only.

## Handoff Triggers

- Call ARMARIUS only when local skills are insufficient and more external discovery is needed.
- Call ARTIFEX only after a candidate is accepted or adapt-only and must become a local skill, workflow, rule, or MCP surface.
- Call CENSOR only when the safety decision, risk acceptance, or assumptions need adversarial verification.
- Call OPTIO only when the candidate would change Legion routing or task ownership.

## Step 1: Identify Candidate

Record:

- repository URL
- stated purpose
- license
- last update and activity signals
- asset paths, especially `.agent/`, `skills/`, `workflows/`, `rules/`, `mcp_config.json`, `package.json`, and installer scripts

## Step 2: Classify Asset

Choose one:

- `native-agent-pack`: contains `.agent/rules`, `.agent/workflows`, or `.agent/skills`
- `skill-library`: contains many `SKILL.md` folders but no Antigravity `.agent` wrapper
- `mcp-or-sdk`: provides MCP or programmatic agent integration
- `installer-pack`: primarily an install/sync tool
- `reference-only`: useful docs or examples, not installable as-is

## Step 3: Safety Gate

Check:

- install commands and scripts
- dependency manifests
- hardcoded secrets or credential prompts
- write targets such as `.gemini`, `.claude`, `.agent`, shell profiles, global npm/pip paths
- destructive commands and overwrite behavior
- MCP tools with shell, filesystem, browser, wallet, cloud, database, or production-data access

Decision:

- `accept`: safe to copy specific non-executable assets
- `adapt-only`: use ideas, do not copy/run code
- `blocked`: do not use
- `needs-approval`: user must explicitly approve due to broad permissions or global install

## Step 4: Fit Against Legion Kit

Ask:

- Does it fill a real owner-level gap in `agent/rules`, `agent/workflows`, `agent/skills`, or `mcp-server`?
- Can it be represented as a small local workflow instead of a large imported pack?
- Does it duplicate an existing Legionary skill?
- Does it increase token load at session start?

## Step 5: Import Plan

If accepted, define exact local changes:

- files to create or modify
- source attribution in docs
- deterministic proof command
- rollback path

Do not bulk install external repositories during this workflow.

## Output

```markdown
## External Skill Audit

- Candidate: <repo/url>
- Asset type: <classification>
- Safety decision: accept | adapt-only | blocked | needs-approval
- Useful assets: <paths>
- Risks: <specific risks>
- Local action: <what to change locally, if anything>
- Proof: <command/result required>
```
