# External Skill Security Gate

Use this reference before installing or adapting GitHub/registry skills, agents, hooks, MCP servers, or plugin bundles.

## Ownership

- Discovery owner: SKILL-QUARTERMASTER.
- Security gate: GUARDIAN.
- Skill packaging: ARTIFEX only after GUARDIAN passes the source.
- Runtime acceptance: REVIEWER and TESTER.

Do not install external packs because they are popular. Popularity is search signal, not trust.

## Static Scan

Run the local scanner before any install or copy:

```bash
node integrations/claude-legion-kit/scripts/external-skill-scan.mjs <candidate-dir>
```

Blockers include remote shell execution, encoded payload execution, private-key material, destructive broad deletes, SSH credential access, and possible secret exfiltration. Warnings include lifecycle scripts, `sudo`, dynamic eval, broad private-directory access, and secret-like tokens.

## Manual Review

1. Read `SKILL.md`, plugin manifests, install scripts, package manifests, hooks, MCP config, and README.
2. Reject `curl | sh`, `wget | sh`, `base64 -d | bash`, hidden telemetry, credential prompts unrelated to purpose, global shell/profile edits, and broad filesystem/cloud/browser access.
3. Prefer extracting ideas or small protocol snippets over installing full packs.
4. Preserve source URL, commit/tag, license, scanner result, and manual decision if anything is adapted.

## Decision Shape

```yaml
external_skill_gate:
  candidate: "owner/repo/path"
  source_commit: "sha-or-unknown"
  scanner: "passed|blocked|warnings"
  manual_review: "passed|blocked|needs-user-decision"
  install: "skipped|project-local|rejected"
  reason: "short decision basis"
```
