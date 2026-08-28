# Review routing ladder and cost control

This is the operational source for Aquila verification routing after the atomic cutover at `2026-08-03T11:00:42Z`. Route from consequence, proof strength, ambiguity, and active task-class promotions. The implementation model identity alone never selects the reviewer.

## Required order metadata

Every order created at or after the cutover contains exactly one compact `notesForExecutor` entry:

```text
AQUILA_ROUTING_JSON_V1:{"objectiveId":"stable-id","attempt":1,"taskClass":"routine_implementation","complexity":"medium","risk":"low","ambiguity":"low","reversibility":"high","evidenceNeed":"high","executor":"codex","model":"gpt-5.6-terra","reasoningEffort":"medium","executionProfile":"implementation","verificationProfile":"V1","reviewer":"gpt-5.6-sol","confidence":"high","reasons":["deterministic proof is incomplete"]}
```

The runner rejects missing, duplicate, malformed, non-compact, unknown, or semantically incompatible metadata before dispatch. Orders created before the cutover retain their original contract and do not require this entry.

New order control artifacts use the deterministic namespace
`<repo>/.centurion/agents_results/<orderId>/`, where `repo` is the resolved
`workspace.repoPath` and `orderId` is a fresh safe single path component.
Canonical results, candidates, receipts, streams, events, and evidence must be
under that directory. Declared product/application artifacts remain in their
own allowed paths; root-noise cleanup is a separate operation.

V0 additionally carries all canonical `trustPredicates` as exact `true` booleans. V3 additionally carries `specialistGate:{"required":true,"approved":true,"approver":"..."}`. A terminal reviewer order uses `executionProfile:"terminal_review"`, `terminalGate:true`, and `reviewer:"none"`; it cannot appoint another reviewer.

## V0-V3 matrix

| Profile | Terminal route | Required conditions |
|---|---|---|
| V0 | Deterministic controller proof only; no reviewer process | Low risk; local/narrow blast radius; cheap reversal; exact visible failure oracle; no security, data, schema, dependency, deploy/runtime, public, or external side effect; all required artifacts/proofs pass; no uncertainty, scope deviation, forbidden hit, or unverified assumption |
| V1 | `gpt-5.6-sol` | Recoverable work where deterministic proof leaves a meaningful behavior gap |
| V2 | `claude-opus-5` | Medium consequence, material ambiguity, shared contract, architecture, difficult diagnosis, cross-service decision, or material hidden failure mode |
| V3 | `claude-opus-5` plus specialist/Boss gate | Security, auth, secrets, money, payments, wallets, KYC, data loss, migration, production, dependency/supply-chain, public endpoint, or infrastructure change |

Evaluate V3 triggers first. V2 and V3 are hard floors and can never route to `none` or Sol. V0 is legal only when every trust predicate is true. Sol implementation may still qualify for V0 because executor complexity and verification consequence are separate decisions.

Contract-only result normalization with unchanged product hashes may use V0 deterministic closure. A normalizer must preserve original bytes and identity history and cannot invent proof, change semantic status, or author a success summary.

## Terminal-gate rule

- V0 controller proof is terminal.
- V1 Sol review is terminal unless a deterministic escalation trigger raises the profile.
- V2/V3 Claude review is the terminal model gate.
- A reviewer result is evidence about the frozen implementation candidate, not a new implementation candidate.
- After the terminal model gate, Aquila performs deterministic schema, identity, hash, path, artifact, and proof checks only.

## Escalation and correction

Escalate V1 to Claude when risk becomes high; security/auth/secrets/payments/dependency/migration/public/infra/production enters scope; architecture/data/API/cross-service judgment is required; required proof fails or cannot run; scope or forbidden-path drift occurs; Sol reports uncertainty, incomplete context, a medium/high finding, or `REQUEST_CHANGES`; or two attempts fail with the same failure class.

Task-class trust revocation is deterministic:

1. One medium/high escaped V0 defect promotes that task class to V2.
2. Two low escaped V0 defects within ten completed objectives promote the class one level for the next five objectives.
3. One high Sol miss or two consecutive medium Sol misses promotes that task class to Claude.
4. Record the defect or miss, severity, correction order, and promotion in the append-only attempt ledger.
5. Re-evaluate the affected routing rule on demand; do not launch retrospective reviews for unrelated clean objectives.

## Evidence bundle

Provide a reviewer only the evidence that can change the verdict:

- objective and acceptance criteria;
- frozen diff or exact artifact hashes;
- candidate result;
- allowed and forbidden paths/actions;
- exact proof outputs;
- minimal necessary source context.

Exclude executor confidence, persuasive narration, repeated methodology, whole-session history, and unrelated repository context.

## Attempt ledger and operating metrics

Append one immutable JSONL row per attempt with `objectiveId`, `orderId`, `attempt`, `taskClass`, `executor`, `model`, `reviewer`, `risk`, `status`, `failureClass`, `resultPath`, `durationSeconds`, `uncachedInput`, `cachedInput`, `output`, `costUsd`, and `telemetryStatus`. Missing usage is `unmeasured`, never numeric zero. Keep Codex uncached/cache-subset semantics separate from Claude cache-read semantics before aggregation.

Observe these metrics without delaying or conditioning the cutover: tokens and review cost per completed objective, V0 eligibility and avoided-review rate by task class, escaped-defect count/correction cost, V1 Sol escalation rate, first-write schema validity, missing/unparseable artifact rate, review latency, safe fail-closed count, and scope violations.

## Cost arithmetic

```text
cost = uncached_input * uncached_rate
     + cache_read * cache_read_rate
     + output * output_rate
```

Use current provider pricing and live usage semantics. Per-run averages do not prove system savings when extra attempts increase total uncached input.

## Pitfalls

- Adding Sol on top of the required Claude gate instead of selecting one terminal route.
- Sending V0 work to a reviewer after complete deterministic proof.
- Letting Sol replace Claude for a V2/V3 floor because it is cheaper.
- Creating review-of-review recursion.
- Using an LLM to repair enum, path, or result-object shape defects.
- Counting safe fail-closed stops as implementation errors.
- Recording absent usage as zero.
