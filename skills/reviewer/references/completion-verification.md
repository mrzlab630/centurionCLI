# Completion Verification

Use this reference when a task is claimed complete, especially after an external model or Claude subagent returns `done`.

## Ownership

- Primary owner: REVIEWER.
- Proof owner: TESTER.
- Security gate: GUARDIAN.
- Requirement rewrite: INTERPRES.
- Implementation fix: CODER or PICTOR depending on surface.

REVIEWER does not broaden into test writing or implementation. REVIEWER decides whether the completion claim is credible and routes missing proof.

## Verification Checklist

1. Find the stated requirement or task contract.
2. Compare claimed files with actual diff.
3. Search for stubs, TODO/FIXME, placeholder data, mock-only integrations, and no-op handlers.
4. Verify core happy path and at least one realistic failure path.
5. Check required config, migrations, env docs, build scripts, and routes are present.
6. Inspect tests: they must exercise real implementation paths, not only mocks.
7. Reject `done` if proof commands were not run, failed, or are irrelevant.

## Common False Completion Patterns

- UI exists but no backend/API integration.
- Test passes because it tests a mock or old behavior.
- Error path catches and hides failures.
- Feature works only for hardcoded sample values.
- Migration/config/env variables missing.
- External agent changed allowed files but skipped result/proof artifact.

## Verdict Shape

```yaml
completion_verdict:
  status: "accepted|rejected|blocked"
  claim: "what was claimed complete"
  evidence:
    - "file:line or command output summary"
  missing_proof: []
  required_handoffs:
    - owner: "TESTER|CODER|PICTOR|GUARDIAN|INTERPRES"
      reason: "why this owner is needed"
  acceptance_gate:
    - "command or browser check required before acceptance"
```
