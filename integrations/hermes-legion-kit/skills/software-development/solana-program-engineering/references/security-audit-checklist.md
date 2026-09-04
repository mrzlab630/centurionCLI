# Solana Security Audit Checklist

Use this checklist for native Rust, Anchor, and Pinocchio-style programs. Apply it instruction by instruction and across multi-instruction/economic workflows. Static matches are leads; confirm exploitability from control flow, account constraints, state, and runtime behavior.

## Contents

- [Audit method](#audit-method)
- [Finding format](#finding-format)
- [Program and account inventory](#program-and-account-inventory)
- [Account validation and relationships](#account-validation-and-relationships)
- [PDAs and signed authority](#pdas-and-signed-authority)
- [CPI and confused deputy](#cpi-and-confused-deputy)
- [Remaining accounts and aliases](#remaining-accounts-and-aliases)
- [Serialization and type identity](#serialization-and-type-identity)
- [CPI freshness and state sequencing](#cpi-freshness-and-state-sequencing)
- [Initialization, realloc, close, and revival](#initialization-realloc-close-and-revival)
- [Arithmetic, precision, and accounting](#arithmetic-precision-and-accounting)
- [Oracles and economic security](#oracles-and-economic-security)
- [SPL Token and Token-2022](#spl-token-and-token-2022)
- [Compute, locks, and denial of service](#compute-locks-and-denial-of-service)
- [Upgrades, governance, and supply chain](#upgrades-governance-and-supply-chain)
- [Audit verification](#audit-verification)

## Audit Method

1. Freeze the reviewed revision and record the worktree state, build configuration, features, program IDs, framework/tool versions, IDL, and known deployed artifacts.
2. Map every instruction, account role, PDA, CPI edge, token flow, oracle, authority, state transition, and privileged maintenance path.
3. Mark user-controlled data and accounts. Trace each path through parsing, validation, arithmetic, mutation, CPI, token movement, and postconditions.
4. Compare code checks against documented invariants. Missing documentation is an ambiguity, not proof that behavior is safe.
5. Build an exploit hypothesis before assigning severity. State the attacker capability, preconditions, sequence, and resulting invariant violation.
6. Reproduce with the smallest safe test or harness when authorized. Never use real funds, keys, or clusters for exploit verification without explicit Boss approval.
7. Require a negative regression test for every confirmed fix.
8. Separate program defects from client-only weaknesses, deployment/governance risks, unavailable proof, and version uncertainty.

## Finding Format

Report each finding with this exact semantic structure:

- **ID and title:** stable identifier plus concise violated invariant.
- **Severity:** Critical, High, Medium, Low, or Informational, with impact and likelihood rationale.
- **Status:** Confirmed, Suspected, Not Reproduced, Fixed, Accepted Risk, or Out of Scope.
- **Evidence:** exact files/lines, instruction/account roles, constraints, runtime/test output, and reviewed revision.
- **Invariant:** the rule that should always hold.
- **Attack path:** ordered attacker actions and program behavior.
- **Preconditions:** signer/account control, state, timing, liquidity, oracle, upgrade, token extension, or cluster conditions required.
- **Impact:** stolen/frozen funds, unauthorized state, insolvency, denial of service, governance takeover, data corruption, or bounded consequence.
- **Remediation:** smallest concrete validation/design change; include compatibility or migration implications.
- **Regression test:** adversarial setup, expected failure/success, and invariant assertions.
- **Residual risk:** what remains unproved after remediation.

Do not inflate severity from pattern names. Arbitrary CPI, signer omission, or arithmetic behavior is Critical only when the demonstrated impact and reachable preconditions support it.

## Program And Account Inventory

- [ ] Enumerate all entrypoints/instructions, including admin, migration, repair, pause, close, reclaim, and upgrade-related paths.
- [ ] Enumerate every account role in declared order, optional accounts, and remaining-account schemas.
- [ ] Record expected public key/PDA, owner, signer, writable, executable, data length, discriminator/tag, version, and initialization state.
- [ ] Record all stored relationships: authority, parent, mint, vault, market, pool, position, oracle, fee recipient, token program, hook program, and governance state.
- [ ] Record every lamport and token flow, including fees, rent, close destinations, withheld fees, and refunds.
- [ ] Record every CPI target, PDA signer, forwarded privilege, and account that may be changed by the callee.
- [ ] Record state-machine transitions and terminal states.
- [ ] Record economic assumptions: solvency, conservation, price source, precision, slippage, deadline, ordering, liquidity, and MEV exposure.

## Account Validation And Relationships

### Signers and authority

- [ ] Every privileged action requires a signer or runtime-proven authority.
- [ ] The signer is bound to the exact stored authority, PDA domain, multisig/governance decision, or valid delegation.
- [ ] Delegation scope, nonce/replay behavior, expiry, and revocation are enforced.
- [ ] Fee payer status is not confused with protocol authority.
- [ ] PDA signing is not treated as proof that the user-selected action or target is allowed.

### Owners, addresses, writable, and executable flags

- [ ] Account owner is validated before typed deserialization or trusted data access.
- [ ] Fixed program/sysvar/mint/oracle/config addresses are checked when identity matters.
- [ ] Mutable state and lamport/token destinations are writable; read-only roles are not unnecessarily writable.
- [ ] Program accounts are executable and match the expected program ID.
- [ ] Token accounts and mints are owned by the explicitly accepted token program.
- [ ] System-owned, program-owned, and token-owned lifecycle transitions are validated at the correct point.

### Relationships and uniqueness

- [ ] Stored authority, parent, mint, vault, market, pool, position, oracle, and fee relationships are checked.
- [ ] Accounts that must represent different roles cannot be duplicates.
- [ ] Accounts that may alias do not break conservation, fees, state transitions, or before/after balance checks.
- [ ] Close/refund destinations cannot redirect protocol or third-party value without authorization.
- [ ] Cross-market, cross-mint, cross-user, or cross-epoch account substitution is rejected.

Anchor note: `Signer`, `Account`, `Program`, seeds, bump, `has_one`, address, owner, token, mint, ATA, close, and realloc constraints prove only what they express. Inspect custom constraints, unchecked accounts, loaders, interfaces, remaining accounts, zero-copy, and business invariants directly.

## PDAs And Signed Authority

- [ ] Each PDA family has an unambiguous domain prefix and stable seed encoding.
- [ ] Seeds bind the account to its intended parent/authority/mint/market/position/epoch.
- [ ] Variable seeds are length-bounded and normalized only by documented protocol rules.
- [ ] The derivation uses the intended program ID.
- [ ] Canonical bump derivation is required or the alternative stored-bump scheme is explicitly validated.
- [ ] Address, owner, discriminator, state relationship, and initialization status are validated together.
- [ ] `invoke_signed` or framework signer seeds exactly match the validated PDA and canonical bump.
- [ ] No seed collision permits type confusion or cross-domain authorization.
- [ ] User-supplied bump or seed data cannot select an unintended valid PDA.
- [ ] A PDA capability is scoped to the exact CPI target, asset, recipient, and action.

Attack hypotheses to test:

- non-canonical bump accepted in one path but canonical bump used elsewhere;
- same seeds reused for different account types or authority roles;
- foreign-program PDA accepted without checking the foreign program ID;
- valid vault PDA signs an arbitrary user-selected CPI or transfer;
- prefunded PDA address bypasses initialization or ownership assumptions.

## CPI And Confused Deputy

- [ ] Every CPI target program is allowlisted and its executable account identity is validated.
- [ ] Instruction data sent to the callee is constructed from validated values and intended discriminators.
- [ ] CPI account order and role mapping match the callee interface.
- [ ] Forwarded signer/writable privileges are the minimum necessary.
- [ ] User-controlled remaining accounts cannot become arbitrary CPI targets or privileged destinations.
- [ ] PDA-signed CPI binds program, instruction, asset/mint, source, destination, amount, and authority to protocol intent.
- [ ] Callee failure and return data are handled according to the current interface.
- [ ] Nested CPI depth and compute are bounded.
- [ ] The caller does not rely on pre-CPI cached balances, supply, authorities, or status after the callee may mutate them.
- [ ] Token transfer hooks and other extension-triggered CPIs are included in the CPI graph.

Confused-deputy question: if an attacker can choose one account or byte string, can they make a legitimate signer/PDA authorize a different program, mint, vault, recipient, or operation than the protocol intended?

## Remaining Accounts And Aliases

- [ ] Remaining accounts have an explicit schema, maximum count, ordering, type, owner, signer/writable policy, and relationship checks.
- [ ] Duplicate accounts are detected where roles must be unique.
- [ ] Duplicate mutable accounts cannot be counted twice, credited twice, charged once, or bypass per-account limits.
- [ ] Account list length cannot cause unbounded loops, allocations, sorting, hashing, or CPI fan-out.
- [ ] No account is selected by position alone when a key/type/relationship is required.
- [ ] Extra-account-meta resolution for transfer hooks is validated and bounded.
- [ ] Optional accounts cannot shift subsequent positional interpretation.

Adversarial tests should permute order, omit accounts, add extras, duplicate each role, use the same account for source/destination, mix owner/mint/market domains, and hit the maximum count.

## Serialization And Type Identity

- [ ] Instruction and account data lengths are checked before slicing or deserialization.
- [ ] Fixed layouts require exact length; variable layouts use explicit maximums and reject malformed trailing data unless extensions are designed.
- [ ] Owner and address/PDA checks occur before typed data is trusted.
- [ ] Discriminator/tag and version are validated; custom or shortened discriminators remain unique and non-prefix-ambiguous.
- [ ] Uninitialized/zeroed data cannot impersonate a valid type.
- [ ] Different account types with compatible field shapes cannot be substituted.
- [ ] Zero-copy layouts prove alignment, padding, initialized bytes, permitted bit patterns, aliasing, and version compatibility.
- [ ] Serialization failure returns a controlled error and cannot leave an invalid partial lifecycle state.
- [ ] IDL/client codecs match on-chain tags, fields, enums, and account ordering.

Type-cosplay tests should use correct length with wrong owner, correct owner with wrong discriminator, discriminator prefix collisions, old/new versions, zeroed bytes, truncated data, oversized vectors, and an account of another program type with similar fields.

## CPI Freshness And State Sequencing

- [ ] Identify every account that a CPI or hook may mutate.
- [ ] Reload/reborrow/re-deserialize those accounts after CPI before checking balances, supply, authority, delegate, close authority, state, extension data, or protocol fields.
- [ ] Before/after accounting reads both values from the intended temporal point.
- [ ] Effects and checks are sequenced so a callee cannot invalidate a precondition used after CPI.
- [ ] No stale cached field authorizes a second transfer, close, mint, burn, or state transition.
- [ ] Events/logs describe final state, not stale pre-CPI assumptions.

## Initialization, Realloc, Close, And Revival

### Initialization and reinitialization

- [ ] Initialization requires the exact expected pre-state: owner, length, discriminator/tag, lamports/rent, PDA/address, and absent prior state.
- [ ] `init_if_needed` or equivalent is used only with an explicit idempotency/reinitialization design.
- [ ] Prefunded or preallocated addresses cannot bypass initialization invariants.
- [ ] Reinitialization cannot reset authority, nonce, accounting, limits, or terminal state.
- [ ] Migration distinguishes old-version state from uninitialized state.

### Reallocation

- [ ] New size is checked with arithmetic and a protocol maximum.
- [ ] Payer and rent-delta behavior are authorized.
- [ ] Shrink/grow sequencing preserves serialized fields.
- [ ] Newly exposed bytes are zeroed or initialized before read.
- [ ] Shrunk stale bytes cannot later reappear as trusted data.
- [ ] References/borrows are not retained across realloc.
- [ ] Compute and transaction-size costs are bounded.

### Close and revival

- [ ] Close authority and lamport destination are validated.
- [ ] Discriminator/type state is invalidated and data cannot remain usable in the same transaction.
- [ ] A closed account cannot be revived by lamport transfer or CPI and reused by a later instruction in the transaction.
- [ ] Terminal protocol state is recorded elsewhere if the address must never be reused.
- [ ] Token-account close authority, balance, withheld fees, native wrapping, and extensions are handled.

## Arithmetic, Precision, And Accounting

- [ ] All attacker-influenced arithmetic uses checked operations and checked conversions.
- [ ] Units and scales are explicit for token amounts, decimals, prices, fees, shares, percentages, slots, and timestamps.
- [ ] Intermediate width prevents overflow before division or conversion.
- [ ] Rounding direction is intentional, bounded, and tested for repeated exploitation.
- [ ] Fee calculation has caps, correct base, correct recipient, and conservation with net/gross token movement.
- [ ] Share/debt/collateral calculations preserve solvency and cannot mint value from zero/near-zero denominators.
- [ ] Slippage uses minimum-output or maximum-input semantics with exact units and inclusive/exclusive boundary tests.
- [ ] Deadlines use a verified clock/slot source and cannot overflow or be bypassed at boundaries.
- [ ] Duplicate accounts cannot break sum/conservation checks.
- [ ] Token decimals are read from the verified mint or otherwise bound to trusted configuration.
- [ ] Precision loss, dust, interest accrual, and liquidation rounding do not accumulate an attacker advantage.

Test zero, one, max, just-under/over thresholds, decimal extremes, repeated micro-operations, source equals destination, fee equals amount, empty/full pools, and long accrual intervals.

## Oracles And Economic Security

- [ ] Oracle program/feed identity is allowlisted and related to the expected asset/market.
- [ ] Data owner, type/version, status/trading state, exponent/scale, and bounds are validated.
- [ ] Staleness uses the correct slot/time source and boundary.
- [ ] Confidence interval or dispersion is within a documented limit.
- [ ] Aggregation/fallback rules cannot mix incompatible feeds or silently accept one stale source.
- [ ] Price positivity and protocol-specific min/max bounds are enforced.
- [ ] Manipulation cost and liquidity assumptions are documented for spot/TWAP/custom sources.
- [ ] Failure mode is explicit: fail closed, pause, limit action, or use a validated fallback.
- [ ] Same-transaction or atomic composition cannot manipulate a source and consume it contrary to assumptions.
- [ ] Liquidation, auction, settlement, swap, and fee paths account for MEV, sandwiching, back-running, stale quotes, and ordering.
- [ ] Admin updates to feeds, risk limits, fees, or pause state require proper governance and delay where designed.

Economic findings must distinguish code-enforced invariants from external liquidity, keeper, governance, and oracle assumptions.

## SPL Token And Token-2022

### Common token checks

- [ ] Token program identity is explicit and accepted for each instruction.
- [ ] Mint and token accounts are owned by that token program.
- [ ] Token account mint and authority fields match protocol state.
- [ ] ATA derivation includes the correct wallet, mint, and token program.
- [ ] Mint decimals, mint authority, freeze authority, supply assumptions, and close authority are validated as required.
- [ ] Source/destination cannot alias when that breaks accounting.
- [ ] Transfer uses checked semantics when available and validates expected decimals.
- [ ] Delegate, delegated amount, frozen state, native-token state, and close authority are considered.
- [ ] PDA token authority signs only the intended asset movement.
- [ ] Balances are reloaded after transfer/mint/burn/hook CPI before further decisions.

### Token-2022 extension hazards

- [ ] Inventory mint and account extensions before accepting the asset.
- [ ] Transfer-fee config, fee authority, withheld amounts, harvest/withdraw paths, epoch changes, and net-versus-gross accounting are handled.
- [ ] Transfer-hook program ID, extra-account-meta list, hook accounts, nested CPI behavior, failure, and compute are validated.
- [ ] Permanent delegate cannot bypass ownership assumptions.
- [ ] Default account state/freeze behavior cannot lock protocol funds unexpectedly.
- [ ] Non-transferable, confidential, interest-bearing, scaled/UI amount, memo-required, CPI-guard, metadata/group pointer, and close-authority semantics are accepted or rejected explicitly.
- [ ] Extension authorities cannot be changed to violate listed-asset assumptions without governance detection.
- [ ] Unknown or newly introduced extensions fail closed until reviewed.
- [ ] The program does not parse a Token-2022 account as legacy Token or vice versa.

Test tokens with no extensions, each accepted extension alone, interacting extensions, maximum fees, active hook, failing hook, malicious extra accounts, frozen/default state, permanent delegate, unknown extension, and authority changes.

## Compute, Locks, And Denial Of Service

- [ ] Loops, recursion, account counts, instruction data, vector growth, extension parsing, and CPI count are bounded.
- [ ] Worst-case invalid input cannot consume materially more compute than bounded assumptions allow.
- [ ] Logging, hashing, PDA derivation, deserialization, sorting, and duplicate detection are measured in hot paths.
- [ ] Realloc/account growth has size and frequency caps.
- [ ] Nested CPI and transfer hooks cannot exceed compute/depth unexpectedly.
- [ ] Global writable PDAs, shared vaults, queues, and oracle/config accounts are reviewed for lock contention and griefing.
- [ ] An attacker cannot cheaply fill state, occupy a unique PDA, create dust positions, force expensive cleanup, or block progress.
- [ ] Crank/keeper paths guarantee bounded progress and cannot be permanently wedged by one malformed item.
- [ ] Failure paths do not leave economic state live but operationally unserviceable.

## Upgrades, Governance, And Supply Chain

### Upgrade and governance

- [ ] Loader and program-data account are identified with current tooling.
- [ ] Program ID, program-data address, deployed artifact hash, IDL hash, and cluster agree with the release record.
- [ ] Upgrade authority identity, multisig/timelock, signer threshold, and emergency controls are verified.
- [ ] Governance instructions cannot substitute proposal, realm, governing token, authority, or target program accounts.
- [ ] Pause, resume, migration, repair, fee, oracle, and authority-change paths obey least privilege.
- [ ] Upgrade can migrate existing state safely or blocks on an explicit migration plan.
- [ ] Rollback artifact, authority, trigger, compatibility limits, and procedure are documented and proven or marked untested.
- [ ] Making a program immutable or changing authority requires explicit Boss approval and independent review.

### Build and dependency supply chain

- [ ] Source revision and worktree state are recorded.
- [ ] Rust/Solana/Anchor/framework/container versions and Cargo.lock are pinned or explained.
- [ ] Build scripts, proc macros, git/path dependencies, duplicate versions, unsafe crates, advisories, yanked/unmaintained packages, and licenses are reviewed.
- [ ] On-chain features exclude unintended host/test dependencies.
- [ ] Verifiable/reproducible build output matches the reviewed source and deployed bytes.
- [ ] IDL and generated clients derive from the reviewed interface.
- [ ] No downloaded script, unpinned installer, MCP/plugin, or third-party skill is executed as part of the audit without separate approval.

## Audit Verification

- [ ] Every instruction and privileged path was traced.
- [ ] Every finding uses the required format and cites exact evidence.
- [ ] Confirmed findings have a safe reproduction or a clearly stated proof gap.
- [ ] Fixed findings have adversarial regression tests at the right layer.
- [ ] Signer, owner, writable, relationships, arbitrary CPI, PDA/canonical bump, remaining accounts, duplicate mutable accounts, type cosplay, stale reload, lifecycle, arithmetic, oracle, Token-2022, compute/DoS, upgrade/governance, and supply-chain categories were explicitly reviewed.
- [ ] Severity reflects demonstrated impact and reachable preconditions.
- [ ] Version-sensitive assumptions were checked against current primary sources and installed tools.
- [ ] Unrun tools/tests and residual economic, deployment, or governance risks are reported.
- [ ] The implementer did not approve their own fix; independent Claude review status is explicit.
