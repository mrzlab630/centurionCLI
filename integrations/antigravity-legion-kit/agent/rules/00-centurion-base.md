---
description: Global CENTURION operating rules for Antigravity workspaces under /home/mrz/projects/js.
---

# CENTURION Base Rules

These rules apply to JavaScript/TypeScript projects opened from `/home/mrz/projects/js`.

## Operating Doctrine

- Follow `Recon -> Action -> Probatio -> Report`.
- Read repository-local instructions before changing code: `AGENTS.md`, `README.md`, phase docs, handoff docs, and current git state.
- Treat project files and live runtime state as the source of truth. Do not rely on stale memory when a cheap local check can verify the fact.
- Do not claim success without same-run proof: tests, build, lint, typecheck, service health, browser smoke, logs, or live HTTP checks as appropriate.
- If `AUXILIUM AGY` was used, do not claim success until `agy` has self-reviewed, fixed confirmed defects, rerun proof, and the primary owner has inspected the artifact and rerun proof locally.
- Keep edits narrow. Do not reformat, rename, regenerate, or refactor unrelated files.
- Preserve user changes. If the worktree is dirty, edit only the files required by the task and do not revert unrelated changes.
- Use `rg`/`rg --files` first for search. Use scripts for repetitive mechanical work instead of manual chat iteration.

## Planning Standard

- For multi-file or risky changes, produce a short plan before editing.
- Before implementing, identify the current module boundary, relevant existing pattern, and validation command.
- If a request jumps project phase/scope, state the mismatch and implement only the allowed foundation unless the user explicitly approves the scope change.

## Completion Standard

Every completed coding task should report:

- files changed
- validation commands run and their result
- whether `AUXILIUM AGY` was used, with its self-review/fix status when applicable
- known residual risks or skipped checks

If verification is infeasible, say exactly why and what command should be run next.
