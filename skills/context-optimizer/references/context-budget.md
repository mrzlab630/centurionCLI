# Context Budget And Config GC

Use this reference when adding skills, agents, MCP servers, hooks, large rules, or external-pack ideas. The goal is to improve mission success without increasing trigger noise or default context load.

## Context Budget Audit

Measure before expanding:

| Surface | What To Measure | Warning Sign |
| --- | --- | --- |
| Skills | `SKILL.md` lines, estimated tokens, long descriptions | heavy core file, verbose examples in always-loaded body |
| References | size and routing clarity | reference exists but no pointer or trigger |
| Agents | count, descriptions, role overlap | multiple agents can claim the same task |
| MCP | server count, tool count, broad permissions | MCP wraps shell/git/npm or has many broad tools |
| Instructions | AGENTS/CLAUDE/rules length and duplication | same rule repeated in several active files |

Default estimate:

- prose tokens: `words * 1.3`
- code-heavy tokens: `characters / 4`
- MCP schema overhead: treat every broad tool as expensive until proven otherwise

Run the local audit first:

```bash
node skills/context-optimizer/scripts/skill-surface-audit.mjs
node skills/context-optimizer/scripts/skill-drift-report.mjs
```

## Decision Buckets

| Bucket | Criteria | Action |
| --- | --- | --- |
| Always needed | core routing, safety, proof, current project surface | keep compact in `SKILL.md` |
| On demand | domain detail, examples, edge cases, provider notes | move to `references/` |
| Candidate retire | duplicate, stale, thin, or superseded content | archive only after proof and user approval |
| Blocked | broad-permission external runtime, hooks, installers, secrets | route to GUARDIAN |

## Config GC Doctrine

Config garbage collection is read-only until the user explicitly approves a specific cleanup.

Scan channels:

- active skills and duplicate names;
- stale references, empty skill folders, broken pointers;
- hooks present on disk but absent from active config;
- broad or duplicate permission entries;
- MCP servers that duplicate CLI tools or fail health checks;
- cache/log/history directories that are large and old.

Cleanup rules:

- never delete automatically;
- prefer `.disabled` or `_gc_trash/<date>/` soft-delete;
- record undo instructions;
- ask one item at a time for destructive or global changes;
- never print secret values, only key names and file paths.

## Output Shape

```yaml
context_budget:
  scanned:
    skills: 37
    mcp_servers: 7
    heavy_items: []
    duplicate_names: 0
  risks:
    - surface: "MCP"
      issue: "broad tools"
      action: "minimize for bounded orders"
  next_moves:
    - "move verbose examples to references"
    - "add eval pointer instead of new skill"
```

## Anti-Patterns

- Adding a new skill when an existing Legionary already owns the task.
- Copying external pack docs into active `SKILL.md` bodies.
- Enabling hooks or MCP servers because a source repo ships them.
- Treating age alone as a deletion reason.
- Cleaning global config without a reversible backup and explicit user approval.
