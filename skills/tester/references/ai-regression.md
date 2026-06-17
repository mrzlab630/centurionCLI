# AI Regression Testing

Use this reference when an AI agent changed behavior and the same model, or a similar model, is about to review the result. The purpose is to catch model blind spots with deterministic proof.

## Core Risk

AI-written fixes often miss paths that share the same assumption as the original patch. Common failures:

- production path fixed, sandbox/mock path forgotten;
- API response shape changed in one branch but not another;
- frontend state updated but empty/loading/error states regress;
- generated tests assert the mock instead of behavior;
- review repeats the implementation hypothesis instead of challenging it.

## Regression Drill

1. Name the bug or behavior risk in one sentence.
2. Identify every path that should share the same contract: production, sandbox, mock, feature flag, locale, mobile/desktop, authenticated/anonymous.
3. Add or run a deterministic check before model judgment.
4. Prefer contract assertions over implementation assertions.
5. Record whether proof is first-try (`pass@1`) or recovered after fixes (`pass@3`).

## Contract Assertions

For API or data contracts, assert required fields directly:

```typescript
const REQUIRED_FIELDS = ['id', 'email', 'role', 'notification_settings'];
for (const field of REQUIRED_FIELDS) {
  expect(response.data).toHaveProperty(field);
}
```

For UI contracts, assert visible states instead of component internals:

- loaded data state;
- empty state;
- loading state;
- error state;
- narrow viewport state;
- permission-denied or blocked state.

## Sandbox / Production Parity

When a codebase has a sandbox, demo, mock, or local fallback mode, check parity explicitly:

```yaml
parity_check:
  production_path: "route/service/component used with real data"
  sandbox_path: "route/service/component used with mock data"
  shared_contract:
    - "same required fields"
    - "same status semantics"
    - "same empty/error states"
```

## Reviewer Handoff

Give REVIEWER evidence, not confidence:

```yaml
ai_regression_report:
  risk: "production path fixed but sandbox path may drift"
  deterministic_checks:
    - command: "npm test -- profile-route"
      result: "passed"
  paths_checked:
    - "production"
    - "sandbox"
  remaining_risks: []
```

## Reject Conditions

- No assertion or only `toBeTruthy()` style checks for a contract change.
- Tests depend on live external services without explicit integration-test scope.
- `status=done` from a delegated agent but proof is missing, pending, or not rerun after fixes.
- A model-only review accepts a behavior change without a deterministic grader.
