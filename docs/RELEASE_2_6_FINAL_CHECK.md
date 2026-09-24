# CENTURION 2.6: final release check

## Release

- CENTURION: 2.6.
- Hermes Legion Kit: 0.9.1.
- Claude Legion Kit and plugin: 0.5.0.
- Antigravity Legion Kit and shared Legion contracts: 0.3.0.
- Base commit: `3ee00134800dd8bdbbcdb2fc11a82ae25ba00e5e`.

The user authorized final verification, commit, merge to main, push, and then
local rollout. The earlier project-only installation restriction is superseded
for this release. JEV remains deferred and is not installed or enabled.

## Final verification

All commands below passed on the release working tree:

| Check | Result |
| --- | --- |
| `git diff --check`, `bash -n install.sh`, changed JS syntax checks | PASS |
| `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'` | 23/23 |
| `node --test tests/install-owned-files.test.mjs` | 4/4, including rollback and negative TLS proof in a temporary installation |
| `node integrations/legion-contracts/scripts/smoke.mjs` | PASS |
| `node integrations/codex-legion-kit/scripts/smoke.mjs` | PASS |
| `node integrations/claude-legion-kit/scripts/smoke.mjs` | PASS |
| `node integrations/antigravity-legion-kit/scripts/smoke.mjs --contract-only` | PASS |
| Full Antigravity smoke with isolated HOME/TMPDIR | PASS; real local `agy` used only for `plugin validate` |
| `node integrations/hermes-legion-kit/scripts/smoke.mjs` | PASS; all ten packaged Python regressions and isolated installation |
| Response envelope, accepted inputs, accepted-inputs Gateway regressions | PASS; 14/14 accepted-input tests, fake Astra/Sol/Opus chain, input drift rejection and no replay |
| `node skills/tester/scripts/legion-skill-eval.mjs` | 9/9 |
| `node integrations/claude-legion-kit/scripts/claude-surface-audit.mjs --repo-only` | 38 skills, 37 agents, 37 routing evaluations, zero high-overlap pairs |

The original Opus reports and disagreements remain available as audit history.
This release decision uses the current source and the final checks above.
The old direct-candidate symlink finding is already fixed before path resolution
and covered by the response-envelope regression. The predecessor Gateway test
is included in the installed package and smoke suite.

## Proof boundary

- Real model execution and provider-native structured output are not certified
  by these offline tests. Plugin validation does not invoke a model.
- A completed Hermes smoke does not establish the cause of the prior 120-second
  timeout; that timeout is not claimed fixed.
- Lineage proves local byte integrity, not executor authorship or protection
  against a same-UID adversary. Concurrent modification windows remain.
- Absolute allowed paths and loop state paths retain their documented policy.
- `deterministicFailureOracle` is a legacy semantic claim; controller proof and
  acceptance remain mandatory. V3 stays blocked without trusted approval.
- The owned-files installer helper supports staged verification and rollback;
  the complete bootstrap `install.sh` is not one atomic transaction.
- Local rollout, installed byte/mode verification and live negative TLS proof
  must be recorded after the merge has been pushed. This document does not
  predeclare their success.

No further implementation loop or JEV evaluation is required for this bounded
release. Runtime artifacts, installation backups and local receipts belong
under the ignored `.centurion/` directory, outside the release commit.

## Local rollout correction

The first Hermes rollout exposed an installer prompt bug: a hard-coded `n`
cancelled tool selection after a successful MCP connection. Version 0.9.1 sends
the default prompt response and requires a saved entry with enabled tools.
A zero-exit disabled entry is rejected with rollback. Regression coverage checks
both the prompt response and rollback. The deployment checkout also requires
`npm ci --omit=dev --ignore-scripts` in `integrations/open-design-bridge`, using
the existing lockfile, before MCP registration.
