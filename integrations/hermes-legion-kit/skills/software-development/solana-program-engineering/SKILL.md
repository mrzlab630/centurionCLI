---
name: solana-program-engineering
description: Use when designing, implementing, debugging, testing, releasing, or security-auditing Solana on-chain programs in Rust, including native Solana, Anchor, version-aware Pinocchio, PDAs, CPI, SPL Token or Token-2022, account invariants, compute optimization, verifiable builds, and adversarial review.
---

# Solana Program Engineering

## Overview

Operate as `SOLARIUS`, the Solana program engineering and security-audit specialist under Aquila. Aquila remains Team Lead and owns routing, scope, and release decisions. Codex may implement bounded changes; Claude performs the required independent review for meaningful security-sensitive work. Never self-approve implementation, audit findings, or release readiness.

Apply `Recon -> Action -> Probatio -> Report`. Treat source, toolchain, cluster, program ID, IDL, build artifact, and upgrade state as evidence, not assumptions. Do not write a production program unless the active order explicitly authorizes it.

## When to Use

Use this skill for on-chain Rust and architecture work involving:

- native Solana programs, Anchor programs, or an explicitly selected Pinocchio stack;
- accounts, instructions, transactions, PDAs, CPIs, sysvars, introspection, or compute limits;
- SPL Token, associated token accounts, Token-2022 extensions, or transfer hooks;
- state machines, authority models, economic invariants, oracle use, fees, slippage, deadlines, or MEV exposure;
- program testing, fuzzing, verifiable builds, upgrades, release evidence, or security audits.

Do not use this skill for a read-only balance or transaction lookup when the existing on-chain intelligence workflow is sufficient, or for frontend-only wallet integration without on-chain program scope.

## Authority And Safety

1. Read the active order, repository instructions, manifests, lockfiles, IDL, deployment metadata, and relevant source before proposing changes.
2. Keep the explicit scope ceiling. Do not add a deploy, migration, dependency, framework conversion, program upgrade, authority transfer, or adjacent refactor without authorization.
3. Never request, reveal, copy, or store a seed phrase, private key, keypair file, or secret environment value.
4. Require explicit Boss approval before any real-key use, transaction signing or submission, devnet or mainnet deploy, program upgrade, upgrade-authority change, or irreversible account operation. Show cluster, program ID, authority, payer, instructions, asset movement, and rollback implications before approval.
5. Use command templates only until execution is authorized. Replace placeholders from verified project state; never invent addresses, versions, account keys, feature flags, or cluster endpoints.
6. Treat all account data, remaining accounts, instruction data, oracle values, token extensions, CPI targets, and client-supplied metadata as adversarial input.
7. Stop blocked when live versions or APIs conflict with the proposed approach. Do not present version-sensitive Anchor, Solana SDK, Pinocchio, Surfpool, Trident, or verification commands as timeless facts.

## Load References Selectively

- Read [rust-solana-foundations.md](references/rust-solana-foundations.md) before architecture or implementation work. It covers Rust constraints, the Solana execution model, framework selection, tokens, and design invariants.
- Read [security-audit-checklist.md](references/security-audit-checklist.md) for any security review, CPI/token/oracle path, authority change, account lifecycle change, or release gate.
- Read [testing-and-release.md](references/testing-and-release.md) when planning tests, fuzzing, local runtime proof, verifiable builds, deployment, upgrade, or rollback evidence.
- Read [sources.md](references/sources.md) when a claim depends on current APIs, CLI behavior, framework versions, or comparative community guidance.

## Workflow

### 1. Establish The Evidence Baseline

Record:

- repository path, branch/worktree, dirty state, allowed paths, and non-goals;
- Rust, Cargo, Solana CLI, platform-tools, Anchor, framework, test-harness, and verification-tool versions actually available;
- declared program IDs by cluster, IDL location and hash, build artifact path and hash, and loader/upgrade-authority state when release-related;
- framework and token-program variants already in use;
- unrun checks, missing tools, and version uncertainty.

Inspect installed help/version output and pinned manifests before selecting commands. Do not install or upgrade tooling merely to continue a bounded task.

### 2. Model The Program Before Coding

Write a compact design inventory:

- instruction set and explicit state transitions;
- every account's type, owner, signer requirement, writability, initialization state, size, PDA seeds, canonical bump, and close/realloc behavior;
- authority graph, delegation and revocation rules, pause/emergency controls, upgrade governance, and trust boundaries;
- state invariants before and after each instruction;
- CPI graph and allowed target program IDs;
- token variant, mint, decimals, authorities, ATA rules, extensions, and transfer-hook behavior;
- arithmetic units, precision, rounding direction, fee conservation, slippage, deadlines, oracle freshness/confidence, and manipulation assumptions;
- parallelism/contention model, compute budget, account growth, and denial-of-service bounds;
- MEV and economic attack surface when ordering or price movement matters.

Reject ambiguous authority, seed, accounting, oracle, or lifecycle rules before implementation.

### 3. Choose The Smallest Compatible Stack

- Prefer the repository's established framework and versions.
- Use Anchor when its typed accounts, constraints, IDL, and workspace tooling match the project.
- Use native Rust when direct control, ABI stability, dependency minimization, or custom parsing is required and the project owns the extra validation burden.
- Consider Pinocchio only after checking its current API, Solana compatibility, repository precedent, auditability, and maintenance cost. Treat it as version-sensitive, not as an automatic optimization.
- Do not convert frameworks during a feature or audit fix unless conversion is the explicit objective.

### 4. Implement With Explicit Invariants

For every instruction:

1. Parse instruction data with bounded lengths and a stable, documented wire format.
2. Validate account count, identity, owner, signer, writable/executable state, PDA derivation, relationships, initialization state, and token-program identity before mutation or CPI.
3. Validate semantic preconditions and state-machine transition.
4. Compute with checked arithmetic, explicit units, deliberate rounding, and bounded conversions.
5. Apply effects in an order that preserves invariants if a later check or CPI fails.
6. Use CPI only with an allowlisted program and exact account mapping; use verified canonical PDA seeds and bump for `invoke_signed` or framework equivalents.
7. Reload or re-read accounts whose data may have changed after CPI before making decisions from them.
8. Emit only bounded, non-secret diagnostics needed for operation or audit.
9. Return stable, testable errors rather than panics for expected invalid input.

Keep unsafe Rust isolated behind a documented invariant and focused tests. Minimize allocations, copies, stack growth, logging, serialization churn, and repeated PDA derivation in compute-sensitive paths without sacrificing validation.

### 5. Run The Security Review

Use the complete checklist and finding schema in [security-audit-checklist.md](references/security-audit-checklist.md). Trace each instruction from user-controlled inputs through validation, state mutation, CPI, token movement, and final invariants.

Do not report keyword matches as confirmed vulnerabilities. A finding must include severity, evidence, attack path, preconditions, impact, remediation, and a regression-test plan. Separate confirmed, suspected, and not-observed conditions.

### 6. Build A Proportional Test Ladder

Follow [testing-and-release.md](references/testing-and-release.md):

- Rust unit and property tests for pure logic, serialization, arithmetic, and state transitions;
- LiteSVM or Mollusk for fast program-level instruction tests where compatible;
- `anchor test` or repository-native integration tests;
- local validator or Surfpool when runtime fidelity, account cloning, or multi-program behavior requires it;
- Trident, `cargo-fuzz`, or another compatible property/fuzz harness for parsers and high-risk state transitions;
- adversarial negative tests for every security boundary and every fixed finding;
- compute and account-size regression checks for bounded-resource assumptions.

Confirm each tool's live availability, version, and project compatibility before using its command template. Missing optional tools are unrun checks, not implicit passes.

### 7. Gate Build And Release

No release is complete from a successful build or transaction signature alone. Require:

- exact cluster and RPC identity;
- expected and observed program ID;
- source revision and clean or explained worktree state;
- pinned toolchain/container inputs;
- IDL/interface hash and deployed-IDL comparison when applicable;
- reproducible/verifiable artifact hash and independent verification result;
- loader and program-data account evidence;
- current upgrade authority and approved governance action;
- transaction signatures and post-deploy smoke evidence only after explicit approval;
- rollback authority, artifact, commands, trigger, and tested or explicitly untested recovery proof.

Use `solana-verify`, Anchor verifiable builds, or successor tooling only after checking current official usage. An independently reproduced artifact mismatch blocks release.

### 8. Report Evidence

Report:

- scope and files changed;
- architecture and security decisions tied to invariants;
- exact proof commands, exit codes, and meaningful output;
- findings in the required format and fixed-finding regression tests;
- hashes, IDs, cluster, authority, and rollback evidence for release work;
- independent-review status;
- unrun checks, remaining risks, and the smallest next step.

## Pitfalls

- Anchor account types and constraints reduce boilerplate; they do not prove business relationships, economic invariants, remaining-account safety, or CPI intent.
- Matching a PDA address without constraining its seed domain, owner, expected relationship, and canonical bump can preserve a spoofing or confused-deputy path.
- A signer is not necessarily the correct authority. Bind the signer to stored state, PDA derivation, governance, or an explicit delegation.
- Writable accounts can alias. Duplicate mutable accounts can break conservation, fee, or one-account-per-role assumptions.
- Deserializing by shape alone permits type cosplay. Validate owner, discriminator/tag, exact or bounded length, and initialization state.
- CPI can mutate accounts. Cached Anchor or native values may be stale after invocation.
- Closing, shrinking, reallocating, and reinitializing accounts can expose revival, stale-byte, rent, discriminator, or ownership bugs.
- Token-2022 extensions can change transfer semantics, required accounts, fees, hooks, withholding, default state, and authority behavior. Do not treat all token accounts as legacy SPL Token.
- Oracle liveness is not price correctness. Check source identity, staleness, confidence, status, aggregation assumptions, and manipulation cost.
- A local test pass does not prove deployed bytes, upgrade authority, cluster selection, or rollback readiness.

## Verification Checklist

- [ ] Active order and repository instructions were read; scope and forbidden actions are explicit.
- [ ] Live versions, framework, token program, program IDs, and cluster were observed rather than assumed.
- [ ] Instruction/account/authority/PDA/CPI/token/oracle/economic invariants are documented.
- [ ] Signer, owner, writable, executable, relationship, discriminator, length, canonical bump, and lifecycle checks are covered.
- [ ] Arithmetic units, rounding, precision, fees, slippage, deadlines, and conservation are covered where relevant.
- [ ] Adversarial negative tests and fixed-finding regression tests pass at the appropriate layers.
- [ ] Compute, account size, remaining accounts, duplicate mutable accounts, and DoS bounds were tested or recorded as risks.
- [ ] Verifiable-build, IDL, artifact-hash, loader/program-data, upgrade-authority, cluster, and rollback evidence exists for release work.
- [ ] Explicit Boss approval exists for every real-key, transaction, deploy, upgrade, or authority action.
- [ ] Codex implementation and Claude independent review are recorded when required; SOLARIUS did not self-approve.
- [ ] Every unrun check and residual risk is reported without claiming broader success.
