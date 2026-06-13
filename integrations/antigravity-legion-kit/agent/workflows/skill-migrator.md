---
description: Convert a Claude/Codex/Gemini skill or external SKILL.md into an Antigravity-compatible local workflow or rule.
---

# Skill Migrator Workflow

Use this workflow when turning an external `SKILL.md`, prompt pack, rule file, or command into this kit's Antigravity format.

## Owner

ARTIFEX owns migration and packaging. OPTIO is a handoff only when migration changes global routing, ownership, or task decomposition.

## Migration Rule

Migration is not a blind format conversion. Preserve the useful capability, remove unsafe execution paths, and fit the result into the smallest Antigravity surface.

## Step 1: Read Source

Read the source skill and list:

- trigger/description
- required resources: scripts, references, assets, examples
- tools or commands it expects
- safety-sensitive behavior
- output contract

## Step 2: Choose Target Surface

Use this decision table:

| Source behavior | Target |
| --- | --- |
| Always-on coding discipline | `.agent/rules/<name>.md` |
| Multi-step user-invoked procedure | `.agent/workflows/<name>.md` |
| Large reference knowledge | `.agent/resources/<name>/references/` plus compact workflow |
| Deterministic helper script | keep only after audit; prefer local script with narrow inputs |
| Runtime/tool integration | MCP tool or future SDK integration |

When uncertain, choose a workflow. Workflows are explicit and easier to verify.

## Step 3: Reduce Token Load

- Put only trigger, core instructions, and proof contract in the workflow body.
- Move long background material into references.
- Avoid installing broad catalogs globally.
- Do not duplicate canonical Legion skills from `/home/mrz/.agents/skills`.

## Step 4: Rewrite Paths

External relative paths must become explicit local paths:

- workflows: `.agent/workflows/<name>.md`
- rules: `.agent/rules/<name>.md`
- resources: `.agent/resources/<name>/{scripts,references,assets}`
- canonical Legion skills: `/home/mrz/.agents/skills/<skill>/SKILL.md`

## Step 5: Verification

Before accepting the migration:

- confirm every referenced file exists
- scan for external install commands and secrets
- run this kit's smoke check if the kit changed
- document source URL and safety decision in `docs/EXTERNAL_CATALOG.md`

## Output

```markdown
## Migration Result

- Source: <url/path>
- Target surface: rule | workflow | resource | MCP | blocked
- Files created/changed: <paths>
- Removed unsafe behavior: <items>
- Proof: <command/result>
```
