# Legion JSON Contracts

CENTURION uses JSON contracts only for bounded delegation points where the controller can validate the executor output mechanically.

These contracts do not replace normal Markdown discussion, WAR ROOM reasoning, research notes, user-facing summaries, or Legionary skill instructions. They are acceptance artifacts for delegated work.

## Contract Boundary

Use structured JSON when all of these are true:

- one controller owns acceptance;
- one executor receives a bounded order;
- allowed paths, non-goals, proof commands, and result file are explicit;
- a guard can validate the result shape, proof status, and scope;
- the output is consumed by another agent or script.

Do not use JSON for open-ended exploration, broad architecture debate, chain-of-thought capture, or regular user conversation.

## Versions

- `LEGION_ORDER_V1`: order format validated by the shared `validate-order` command.
- `AGENT_ORDER_JSON_V1`: Hermes/Aquila order format validated by its separate agent-contract-runner.
- `AGENT_RESULT_JSON_V1`: canonical executor result validated by the shared `validate-agent-result` command, with changed files, proof, self-review, scope deviations, forbidden-pattern hits, and remaining risks.
- `LEGION_RESULT_V1`: older neutral result format validated by `validate-result` without `--canonical`.
- `LEGION_REVIEW_V1`: reviewer-to-controller verdict for accepting or rejecting an executor result.

Hermes linked orders may add an opt-in `lineage` object. Its product-file manifest,
anchor, Gateway proof receipt, and final controller acceptance are validated by
the Hermes runner, not by the shared `LEGION_ORDER_V1` validator. Gateway
start/closure receipts prove launcher custody; final controller acceptance is a
separate semantic decision.

Surface-specific legacy protocols remain valid only for explicit compatibility:

- Antigravity and `agy` may opt into `AGY_ORDER_V1` plus `AGY_RESULT.json` for legacy compatibility.
- Claude Code may opt into `CLAUDE_ORDER_V1` plus `CLAUDE_RESULT.json` for legacy compatibility.

For new executor orders, controller-owned result/candidate/receipt/stream/event
and evidence files belong under
`<repo>/.centurion/agents_results/<orderId>/`, derived from the resolved
workspace repository and a fresh safe `orderId`. Explicit product/application
artifacts stay in their declared paths. Existing root files are not relocated;
cleanup is a separate operation.

Pre-execution snapshots for AGY and Claude are separate controller-custody inputs: guards require an absolute path outside the workspace plus a detached digest. A detached digest catches ordinary tampering; it is not independent authentication against a same-UID writer that can rewrite both custody files, so an external controller account or OS boundary is still required for that threat.

## JSON Response Contract

`AGENT_ORDER_JSON_V1` and `AGENT_RESULT_JSON_V1` remain the wire contracts.
New controller orders declare this optional V1-compatible response binding:

```json
{
  "acceptedTransports": ["raw_json", "json_fence"],
  "handoff": {
    "version": "AGENT_HANDOFF_V1",
    "schemaId": "AGENT_RESULT_JSON_V1",
    "inReplyTo": "implementation-001",
    "senderRole": "CODER",
    "recipientRole": "Aquila",
    "objectiveId": "delivery-001"
  }
}
```

These fields belong to `outputContract`, alongside its existing required fields.
`inReplyTo` equals `orderId`; roles equal `roleForTask` and `controller`;
`objectiveId`, when supplied, equals `AQUILA_ROUTING_JSON_V1.objectiveId`.
The executor echoes the exact object as `result.handoff`. Existing artifact
references require `mediaType` and lowercase `sha256` when handoff is enabled.
The controller checks live file bytes; executor hashes are declarations, not proof.

At response ingress only, a single lowercase `json` fence with whitespace outside
is removed deterministically. Raw JSON bytes are otherwise preserved exactly.
Raw evidence and normalized candidate are separate create-only files. The builder
adds `responseEnvelope` (`AGENT_RESPONSE_ENVELOPE_V1`) with transport, absolute
paths, SHA-256, and byte counts; executors cannot supply this metadata themselves.
Canonical reads remain strict JSON. Consumers verify the hashes, normalization,
and candidate-to-result binding before accepting controller metadata.

Error codes are `RESPONSE_FORMAT_ERROR`, `RESPONSE_SCHEMA_ERROR`,
`RESPONSE_IDENTITY_ERROR`, `RESPONSE_REFUSED`, and `RESPONSE_INCOMPLETE`.
Prose, multiple blocks/documents, duplicate keys, non-finite numbers, invalid UTF-8,
unpaired Unicode surrogates, and truncation fail closed with original evidence.
No automatic product retry or heuristic JSON repair occurs. Final controller
acceptance stays separate from the executor's `done|blocked|failed` statement.

| Surface | Supported response ingress | Native structured output |
| --- | --- | --- |
| Codex through Gateway | Separate candidate file, raw or clean fence; controller builder | Use only if active CLI/model support is confirmed; no new native guarantee inferred here |
| Claude through Gateway | Candidate file or canonical stdout; existing validated event object/array/JSONL, including raw/fenced inner result | Runtime terminal/model/permission checks remain mandatory |
| Claude/AGY guards | Shared ingress normalizer, optional `--handoff <expected.json>`; finalized envelope verification | Guard is a file adapter, not a provider guarantee |
| Direct AGY/Hermes and ordinary Codex/Claude | Opt-in `launch.candidateJsonPath`; distinct canonical result finalized by builder | Legacy direct orders still read strict canonical JSON |

`normalize-response` in `integrations/legion-contracts/scripts/legion-contract.mjs`
provides the shared JS ingress. Guard evidence lives beside its snapshot in a
`.responses` directory; it is excluded from product-write accounting through its
controller custody location, not a general path exemption. Existing V1 fixtures
without handoff remain valid. Python and JS retain exact evidence bytes; for
cross-language numeric identity, represent integers above `2^53-1` as strings,
because JS Number cannot preserve their exact numeric value.

### Accepted Predecessor Inputs

Use optional `order.inputResults` for accepted control artifacts such as Astra
advice. An entry has exactly `orderId`, `resultPath`, `resultSha256`,
`acceptancePath`, `acceptanceSha256`, `closurePath`, and `artifacts`, each with
`path`, `sha256`, and `mediaType`. Controller-provided digests are the trust pins.
All selected files and the predecessor order live inside the predecessor control
namespace. Receipt/identity/hash chains, passed proof/acceptance, and actual
artifact bytes are verified before launch and after proof; Gateway rechecks before
terminal acceptance. Nested inputs are bounded and reject cycles and duplicates.
These are read-only inputs and grant no product-write capability. Product-file
lineage remains separate; same-UID race and authorship limits still apply.

## Custody Tiers

Two custody tiers exist, and they are not equivalent. Choose deliberately.

`agent_contract_runner.py --mode run` writes direct receipts through
`direct_custody.py`: a start receipt before the executor launches, a closure
receipt after controller proof, and a terminal acceptance binding all three by
SHA-256. Proof commands still execute inside the runner process.

`result_gateway.py` runs proof in a separate controller process and emits
create-only `controller-proof.json` plus a final `controller-acceptance.json`
whose `passed` status is the only authority a successor order may rely on.
Receipt existence is not acceptance: a consumer that reads `result.status` or a
start/closure receipt without the Gateway acceptance is reading evidence, not a
verdict.

Linked lineage orders and Astra advisory orders already require the Gateway,
since direct receipts carry no product-file manifest or anchor.

## Known Lineage Limitations

Artifact lineage verifies integrity and custody of declared product files but
has bounded guarantees in same-UID and shared environments:

- **Race window:** Between `preflight_lineage` (verifying predecessor files
  before launch) and `finalize_lineage` (reading successor files after proof),
  a concurrent same-UID process can alter files. The manifest records what
  existed at finalization, not what the executor wrote.
- **Authorship not proven:** A file appearing in `lineage.artifactPaths` proves
  the controller saw that file with that hash at finalization. It does not prove
  the executor created it or that no other process wrote it.
- **Same-UID boundary:** Controller-owned manifest, trusted predecessor anchor
  digest, create-only receipts, and frozen predecessor verification protect
  against ordinary tampering and drift. They do NOT protect against a malicious
  same-UID process that can rewrite both product files and controller custody
  artifacts.

For production or shared environments where multiple actors have write access,
immutable snapshots (container layers, btrfs/zfs snapshots, separate filesystem
namespaces) or external controller account isolation are required for stronger
authorship and tamper resistance.

For same-UID local development, the existing lineage mechanism is a reasonable
trade-off: it catches drift and ordinary mistakes without requiring OS-level
isolation.

## Known Path Policy Risks

`PathPolicy.resolve_under_repo` accepts absolute paths outside `workspace.repoPath`.
An order may set `allowedPaths` to external directories, permitting the controller
to read or write beyond the declared workspace. No separate external-path policy
or regression exists.

`loopContract.statePath` is validated only against allowed/forbidden patterns and
may lie outside `workspace.repoPath`. No explicit controller state root boundary
is enforced.

External path access is useful for controlled delegation but requires explicit
review of each order's `allowedPaths` and loop state location before acceptance.

The shared validator accepts those legacy result payloads only when a surface guard explicitly opts in with `acceptedOrderVersions`.

## Ownership Rule

The JSON contract does not create a new Legionary owner. The primary owner remains responsible for:

- choosing whether to delegate;
- narrowing allowed files and non-goals;
- defining proof commands;
- inspecting the diff or artifact after execution;
- rejecting partial, unproved, or out-of-scope results.

If another specialty is needed, the owner calls that Legionary as a conditional handoff. Ownership does not become shared.

Boss authorizes the objective; Aquila/CENTURION controls dispatch and acceptance;
OPTIO sequences the mission; the assigned specialist owns its bounded work.
Models are executor/advisor/reviewer routes and do not introduce command levels.
Carry source/receiving roles, objective/order IDs, input artifacts, allowed
paths, proof, acceptance criteria, and blockers in existing context or notes.
Review findings return to the controller for a fresh implementation order.

Hermes Loop V1 stores the accepted candidate JSON digest and assigned review
contract in controller state. Review cannot substitute another objective or
task class, downgrade the gate, or close over changed candidate JSON. Older
routed states without a binding need controller recovery from accepted
execution evidence. Terminal review results report no product edits or fixes.
Product immutability requires separate snapshot/guard proof; this result
binding does not remove the same-UID and lineage limitations described above.

## Standard Flow

1. Select one primary Legionary owner.
2. If external execution is useful, create a bounded order for the executor.
3. Require a result JSON file from the executor.
4. Run the surface guard or shared validator.
5. Inspect the real diff or artifact.
6. Run owner proof.
7. Accept, reject, or request fixes.

For reviewer handoffs, the reviewer may return `LEGION_REVIEW_V1` with a verdict, reviewed proof, findings, required fixes, and residual risks.

## Validation

Shared contract package:

```bash
cd integrations/legion-contracts
npm run smoke
node ./scripts/legion-contract.mjs validate-order --file /path/to/LEGION_ORDER.json
node ./scripts/legion-contract.mjs validate-agent-result --file /path/to/AGENT_RESULT.json
node ./scripts/legion-contract.mjs validate-result --file /path/to/LEGION_RESULT.json
node ./scripts/legion-contract.mjs validate-review --file /path/to/LEGION_REVIEW.json
```

Legacy result validation examples (compatibility-only; canonical results need no opt-in):

```bash
CONTROL_DIR="$PWD/.centurion/agents_results/<orderId>"
node integrations/legion-contracts/scripts/legion-contract.mjs validate-result \
  --file "$CONTROL_DIR/AGY_RESULT.json" \
  --accept-order-version AGY_ORDER_V1

node integrations/legion-contracts/scripts/legion-contract.mjs validate-result \
  --file "$CONTROL_DIR/CLAUDE_RESULT.json" \
  --accept-order-version CLAUDE_ORDER_V1
```

Surface-specific guards remain the acceptance gates for scope and filesystem proof:

- `integrations/antigravity-legion-kit/scripts/agy-order-guard.mjs`
- `integrations/claude-legion-kit/scripts/claude-order-guard.mjs`

The shared validator owns result shape. Surface guards own workspace snapshots, changed-file policy, forbidden-pattern checks, and executor-specific strictness.
