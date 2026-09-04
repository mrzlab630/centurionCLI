---
description: Delegate bounded work to AUXILIUM AGY while preserving CENTURION single-owner control and proof gates.
---

# AUXILIUM AGY Delegation

`agy` is a recruited auxiliary executor, not a Legionary owner. Use it to speed up bounded work while the primary Legionary keeps responsibility for scope, proof, and final judgment.

## When To Delegate

Delegate to `AUXILIUM AGY` when all conditions are true:

- One primary Legionary owner is already selected.
- The owner can state exact files, target behavior, non-goals, and proof commands.
- The work is isolated enough for a separate CLI session.
- The expected output is reviewable: patch, draft copy, reference brief, UI slice, test, report, or command output.
- No production secret, credential, destructive operation, payment flow, wallet flow, KYC flow, or exploit execution is required.

Best fits:

- Frontend implementation slices, UI polish, responsive fixes, component states, and animation drafts under PICTOR.
- Reference search, page/block comparison, and source summaries under EXPLORATOR.
- UX copy, CTA, labels, tooltips, descriptions, and content variants under NOMENCLATOR or ORATOR.
- Documentation drafts, README sections, and structured reports under SCRIBA or TABULARIUS.
- Focused tests, smoke scripts, or reproduction scaffolds under TESTER or DEBUGGER when the owner defines proof.

## Do Not Delegate

Keep work local to the owner when it involves:

- Secrets, credentials, private keys, signing, wallet custody, payment credentials, or production auth.
- Production deploys, database migrations, irreversible filesystem changes, or broad `sudo`/system changes.
- Final architecture, security, legal, compliance, product-risk, iGaming-claims, or exploit decisions.
- Ambiguous scope where `agy` would need to choose the owner, rewrite the strategy, or browse unrelated files.

## Delegation Prompt

Use `centurion-legion.agy_delegation_brief` first when the delegation is non-trivial. Supply a fresh safe `orderId`; all controller artifacts belong to that exact order namespace. For implementation work, create a pre-snapshot before calling `agy`:

```bash
AGY_SNAPSHOT="/tmp/centurion-agy-snapshots/<orderId>/AGY_SNAPSHOT.json"
node integrations/antigravity-legion-kit/scripts/agy-order-guard.mjs snapshot \
  --workspace <path> \
  --order-id <orderId> \
  --out "$AGY_SNAPSHOT"
```

Then send `agy` a bounded `AGY_ORDER v1` shaped like this:

```text
You are AUXILIUM AGY working for <OWNER>.
Controller: CENTURION. Authority: obey this AGY_ORDER exactly.
Task: <bounded task>.
Workspace: <path>.
Order ID: <orderId>.
Scope: <files/directories allowed>.
Non-goals: <explicit exclusions>.
Forbidden content patterns: <regex/text patterns that must not appear>.
Proof commands: <commands to run or explain why unavailable>.

Hard-stop rules:
- If a needed action is outside Scope, stop and report blocked. Do not improvise.
- If a Non-goal conflicts with the task, stop and report blocked. Do not reinterpret the order.
- Do not add dependencies, network calls, scripts, broad discovery, or extra files unless explicitly listed in Scope.
- Read only files needed to satisfy the order and proof. Do not browse unrelated workspace files.

First complete the task. Then run a self-review pass:
1. Inspect your own diff/artifact for defects, missed requirements, unsafe assumptions, and incomplete proof.
2. Fix every confirmed defect you find.
3. Rerun proof.

Write `.centurion/agents_results/<orderId>/AGY_RESULT.json` as JSON:
{
  "resultVersion": "AGENT_RESULT_JSON_V1",
  "orderId": "<orderId>",
  "executor": "agy",
  "status": "done|blocked|failed",
  "summary": "...",
  "filesChanged": [{"path":"relative/path","action":"added|modified|deleted|renamed|none"}],
  "artifacts": [{"path":"relative/path","exists":true,"type":"...","note":"..."}],
  "proof": [{"command":"...","cwd":"<path>","status":"pass|fail|not_run","exitCode":0,"summary":"..."}],
  "selfReview": {"performed":true,"findings":[],"fixesApplied":[]},
  "scopeDeviations": [],
  "forbiddenPatternHits": [],
  "remainingRisks": [],
  "questions": [],
  "errors": [],
  "stdoutSummary": "",
  "stderrSummary": ""
}

Final stdout must contain only:
AGY_RESULT_FILE=.centurion/agents_results/<orderId>/AGY_RESULT.json
STATUS=<done|blocked|failed>
SELF_REVIEW_PERFORMED=<true|false>
```

### `--allow-legacy` Compatibility

The previous `AGY_ORDER_V1` result payload is accepted only when the owner adds `--allow-legacy` to the `verify` command. Without that flag, legacy-only and hybrid results are rejected. Compatibility mode keeps the existing legacy self-review, reported-scope, forbidden-pattern, snapshot, and allowed-path checks; use it only for an executor that has not migrated to `AGENT_RESULT_JSON_V1`.

## Acceptance Gate

The owner must not accept `agy` output from prose alone.

Required owner checks:

- Inspect changed files, diff, generated artifact, or cited evidence directly.
- Validate the namespaced `AGY_RESULT.json` shape and changed-file scope with `agy-order-guard` before reading the prose result. Root-level result and snapshot paths are invalid.
- Confirm canonical `selfReview.performed=true` for a done result.
- Rerun the smallest relevant proof locally.
- Call TESTER for failing, flaky, or missing proof.
- Call REVIEWER for risky diffs or behavior-preserving claims.
- Call GUARDIAN for secrets, external code, MCP, dependency, browser/cloud, wallet, payment, or iGaming risk.
- Call CENSOR for unsupported claims, legal/compliance wording, conversion claims, or WAR ROOM decisions.

Final reports must state: primary owner, whether AUXILIUM AGY was used, `agy` proof, owner proof, and residual risk.

Example scope verification:

```bash
node integrations/antigravity-legion-kit/scripts/agy-order-guard.mjs verify \
  --workspace <path> \
  --order-id <orderId> \
  --before "$AGY_SNAPSHOT" \
  --allowed index.html \
  --result .centurion/agents_results/<orderId>/AGY_RESULT.json \
  --forbidden 'fonts\\.googleapis,font-size\\s*:[^;]*vw,letter-spacing\\s*:'
```
