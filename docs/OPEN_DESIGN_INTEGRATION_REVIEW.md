# Open Design Integration Review

Review date: 2026-08-12

Scope: the CENTURION Open Design bridge, reference search, lifecycle controls,
MCP facade, and Hermes, Claude Code, and Codex installers introduced for Cohors
Secunda v2.4.

## Review provenance

Claude CLI was asked to perform the initial external review. The direct route
returned HTTP 401, while the local proxy route emitted an unexecuted
`<tool_call>` block. Neither response is accepted as a Claude review or as proof.

The implementation was then reviewed adversarially by an independent REVIEWER
agent. Its findings were reproduced and fixed before live installation. The
final review was performed against the resulting diff and test suite.

## Findings resolved

1. Descriptor-bound filesystem operations replaced validation followed by
   path-based syscalls, closing inode-level TOCTOU windows.
2. Artifact publication now uses atomic no-replace promotion and fails when a
   destination appears immediately before rename.
3. MCP processes claim a `jobId` atomically, so concurrent servers cannot start
   duplicate jobs with the same receipt.
4. TTL cleanup preserves an expired `running` receipt while its recorded PID and
   Linux process start time still identify a live owner.

Regression coverage includes parent replacement, symlink escape, concurrent
publication, cross-process job claims, live-owner TTL handling, immutable
accepted bundles, explicit project deletion consent, reference integrity, and
Hermes to Claude to Codex continuation.

## Final proof

- Open Design bridge tests: 54 passed, 0 failed.
- Bridge, Hermes, Claude, and Codex smoke checks: passed.
- Hermes live MCP connection: passed; four tools discovered.
- Claude skills-dir plugin validation: passed; one Open Design MCP discovered.
- Codex MCP registration: passed with the repository-local stdio entrypoint.
- Bridge and Codex dependency audits: 0 vulnerabilities.
- JSON schema parsing, Node syntax checks, and `git diff --check`: passed.
- Installed Open Design skill files match the canonical repository skill.

Root `pnpm guard` and `pnpm typecheck` were not run because this repository has
no root `package.json` and does not define those commands.

## Verdict

No blocking or Major findings remain.

VERDICT: APPROVED
