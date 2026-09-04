# Testing And Release

Use this reference to select proportional proof and build a release evidence package. All commands below are templates. Replace placeholders only from verified repository state, and do not run a transaction, deploy, upgrade, authority change, validator/network mutation, or real-key operation without explicit authorization.

## Contents

- [Live availability gate](#live-availability-gate)
- [Testing ladder](#testing-ladder)
- [Adversarial test matrix](#adversarial-test-matrix)
- [Compute and state-size proof](#compute-and-state-size-proof)
- [Verifiable builds](#verifiable-builds)
- [Release evidence](#release-evidence)
- [Deployment and upgrade authorization](#deployment-and-upgrade-authorization)
- [Rollback proof](#rollback-proof)
- [Final release checklist](#final-release-checklist)

## Live Availability Gate

Before selecting a command, inspect the repository and installed tools. Record exact output and do not install missing tools during a bounded task unless installation is separately authorized.

Template inventory:

```bash
rustc --version
cargo --version
solana --version
cargo build-sbf --help
anchor --version
anchor test --help
solana-test-validator --version
solana-verify --version
surfpool --version
trident --version
cargo fuzz --help
```

Also inspect `<workspace>/rust-toolchain.toml`, Cargo manifests/lockfile, `Anchor.toml`, framework crates, test dependencies, CI configuration, declared program IDs, IDL files, and existing release scripts. Run only commands relevant to tools already present and authorized.

Record a compatibility matrix:

| Surface | Required evidence |
|---|---|
| Rust/Cargo | installed version, pinned toolchain, target/features |
| Solana | CLI/platform-tools version, active config only when relevant, build command help |
| Anchor | CLI and crate versions, `Anchor.toml`, cluster/program mapping |
| Pinocchio/native | exact crate/API versions and test/build compatibility |
| Token | SPL Token vs Token-2022 program IDs and extension support |
| Harnesses | LiteSVM/Mollusk/Surfpool/validator/Trident/fuzz versions actually available |
| Verification | Anchor and/or `solana-verify` command behavior observed live |

If versions disagree or a current command is uncertain, stop the affected step as blocked or use a repository-proven alternative. Do not silently migrate toolchains.

## Testing Ladder

Choose the lowest fast layer that proves an invariant, then add higher-fidelity layers for cross-program, runtime, and release behavior. A high layer does not replace focused low-layer assertions.

### 1. Rust unit tests

Use for pure state transitions, authorization helpers, seed construction, instruction codecs, arithmetic, fee/share logic, oracle validation, deadlines, and error mapping.

Templates:

```bash
cargo test --manifest-path <program-manifest> --all-features
cargo test --manifest-path <program-manifest> --no-default-features --features <onchain-features>
cargo clippy --manifest-path <program-manifest> --all-targets --all-features -- -D warnings
cargo fmt --manifest-path <workspace-manifest> -- --check
```

Adapt feature flags to the project. Do not invent `all-features` compatibility if host-only and on-chain features conflict; test the actual supported matrix and report omissions.

### 2. Property tests

Use property testing for arithmetic, serialization round trips, state-machine transition invariants, conservation, fee bounds, seed-domain uniqueness, oracle bounds, and repeated rounding.

Properties should include:

- no overflow/panic for bounded valid and invalid input;
- conservation of assets and shares modulo documented fees/dust;
- forbidden transitions never succeed;
- serialization either round-trips or rejects malformed data;
- slippage/deadline/oracle rules hold at exact boundaries;
- duplicate-role input cannot change the invariant;
- sequence tests preserve solvency and terminal-state rules.

Use the repository's existing property framework. Do not add one without scope authorization.

### 3. LiteSVM

Use LiteSVM for fast in-process Solana transaction/program tests when its installed version supports the program, required built-ins, sysvars, token programs, and CPI behavior.

Template:

```bash
cargo test --manifest-path <litesvm-test-manifest> <focused-test-filter>
```

Verify current LiteSVM APIs and runtime fidelity. Record any unsupported sysvar, loader, CPI, token extension, or feature as a proof gap requiring a higher layer.

### 4. Mollusk

Use Mollusk for lightweight Rust instruction-level execution, account checks, and compute measurement when compatible with the project.

Template:

```bash
cargo test --manifest-path <mollusk-test-manifest> <instruction-test-filter>
```

Assert both program result and resulting account/lamport/data state. Confirm how the pinned version configures sysvars, built-ins, programs, and compute checks.

### 5. Anchor tests

Use the repository's `anchor test` workflow for IDL/client integration, workspace configuration, account constraints, CPI, token operations, and end-to-end instruction sequences.

Templates:

```bash
anchor test --provider.cluster <local-cluster-alias>
anchor test --skip-local-validator --provider.cluster <authorized-local-endpoint>
```

Do not substitute devnet/mainnet for local proof. Inspect live help and `Anchor.toml` because runner behavior and flags change across releases.

### 6. Local validator

Use `solana-test-validator` when full validator/RPC behavior, deployed program loading, address lookup tables, transaction composition, or runtime features exceed in-process harness fidelity.

Template:

```bash
solana-test-validator --ledger <ephemeral-ledger-path> --reset --bpf-program <program-id-placeholder> <artifact-path>
```

This command mutates local runtime state and must be in scope. Use only an explicit ephemeral path. Record genesis/features, cloned accounts/programs, startup logs, program load, RPC endpoint, and cleanup/retention policy.

### 7. Surfpool

Use Surfpool when the current installed version and project support its local-network, forking, cloning, cheatcode, or scenario capabilities. It is version-sensitive and not a universal replacement for validator tests.

Templates:

```bash
surfpool --version
surfpool start <project-specific-safe-options>
```

Starting/forking is a network/runtime mutation and requires authorization. Record upstream cluster/source, cloned addresses, deterministic scenario setup, cheatcodes used, feature differences, and whether assertions were also reproduced on a higher-fidelity runtime.

### 8. Fuzzing with Trident, cargo-fuzz, or repository tooling

Use fuzzing for instruction parsers, account permutations, remaining accounts, CPI composition, token extensions, state-machine sequences, arithmetic, and serialization.

Templates:

```bash
trident <project-defined-fuzz-command> <target-placeholder>
cargo fuzz run <target-placeholder> -- <bounded-run-options>
```

Inspect live help and checked-in configuration. Bound time, corpus, memory, and artifact paths. Preserve minimal crashing inputs and convert confirmed cases into deterministic regression tests. Never treat a no-crash bounded run as proof of absence.

## Adversarial Test Matrix

For each instruction and fixed finding, cover applicable negative cases:

### Accounts and authority

- missing signer; wrong signer; signer not related to state;
- wrong owner; wrong fixed address; non-executable/wrong program;
- read-only account in mutable role; unnecessary writable privilege review;
- wrong parent/mint/vault/market/position/oracle relationship;
- duplicate accounts in every pair of roles, especially mutable source/destination and fee roles;
- wrong length, discriminator/tag, version, initialization state, or zeroed data.

### PDAs and CPI

- wrong seeds, seed domain, parent, program ID, bump, and non-canonical bump;
- valid PDA from another account family;
- arbitrary CPI target and user-chosen CPI instruction data;
- reordered/omitted/extra CPI accounts and excess signer/writable privilege;
- signed CPI to wrong mint, vault, recipient, amount, or token program;
- account mutation during CPI followed by stale caller logic;
- nested CPI/return-data/failure behavior.

### Lifecycle

- prefunded address initialization; double initialization; `init_if_needed` reinitialization;
- realloc to zero, below minimum, maximum, over maximum, shrink then grow, insufficient rent, wrong payer;
- stale bytes after shrink/grow; retained borrow across realloc;
- close to wrong destination, close then revive/fund/reuse in one transaction;
- terminal state reopened or migrated twice.

### Arithmetic and economics

- zero/maximum amounts, overflow/underflow, division by zero, narrowing conversion;
- decimal extremes, fee equals/exceeds amount, repeated dust/rounding extraction;
- source equals destination, duplicate fee recipient, empty/full pool, first/last depositor;
- exact slippage and deadline boundaries, stale/future clock values;
- oracle wrong feed, wrong scale, stale, wide confidence, invalid status, zero/negative/outlier price;
- manipulation/composition scenarios relevant to the protocol;
- pause/governance/authority changes during an economic workflow.

### Tokens

- legacy token passed to Token-2022 path and reverse;
- wrong mint, decimals, token authority, delegate, frozen state, ATA derivation, program ID;
- transfer fee at zero/max and net/gross mismatch;
- transfer hook success/failure, malicious hook/extra accounts, compute exhaustion, account mutation;
- permanent delegate, default frozen state, unknown/unaccepted extension, authority change, withheld fees;
- close authority and native-token edge cases.

### Resources

- maximum instruction data, account size, remaining-account count, vector length, extension count, and CPI depth;
- worst-case invalid input compute;
- shared writable-account contention and cheap state-spam/griefing;
- bounded-progress crank/queue behavior with malformed or adversarial entries.

## Compute And State-Size Proof

Record representative and worst-case compute at the same tool/runtime version. Assert limits in the harness when supported and retain raw output summaries.

Measure:

- each instruction success path and worst expected failure path;
- growth by remaining-account count, vector length, token extensions, CPI count, and state size;
- repeated PDA derivation, hashing, serialization, logs, sorting, and duplicate detection;
- account allocation/realloc size and rent delta;
- transaction account count/size and writable-lock hotspots.

Do not optimize away validation to meet a compute target. If a required invariant cannot fit, redesign state/account partitioning or stop blocked.

## Verifiable Builds

Verifiable build tools and image tags change. First inspect current official docs and installed help. Do not pull images or install tools without authorization.

Anchor templates, only when supported by the pinned version:

```bash
anchor build --verifiable
anchor verify -p <lib-name-placeholder> <program-id-placeholder>
```

Solana verification template, only after current `solana-verify --help` confirms syntax:

```bash
solana-verify <current-subcommand-placeholder> <program-id-placeholder> <verified-build-inputs>
```

Capture:

- source revision and worktree state;
- Cargo.lock and all toolchain/framework/container/image identifiers;
- command and environment inputs excluding secrets;
- output artifact path, size, and SHA-256;
- IDL path and SHA-256;
- verifier version, target cluster/program ID, result, and independently reproduced hash;
- any machine-specific or non-reproducible inputs.

A local reproducible artifact does not prove deployed bytes until compared against the exact on-chain program. A verifier exit code without artifact/target identity and meaningful output is insufficient.

## Release Evidence

Require one evidence package containing:

| Evidence | Required content |
|---|---|
| Scope | approved order, files/revision, reviewer, findings disposition |
| Cluster | explicit local/devnet/mainnet identity and RPC genesis/cluster proof where applicable |
| Program | expected program ID, observed executable account, loader, program-data address |
| Source/build | source revision, clean/explained tree, Cargo.lock, toolchain, framework, build inputs |
| Artifact | absolute path, size, SHA-256, verifiable/reproducible result |
| Interface | IDL/interface path, SHA-256, declared/deployed comparison when applicable |
| Authority | upgrade authority, governance/multisig/timelock evidence, approved signer set |
| Tests | exact commands, exit codes, negative/security/compute coverage, unrun checks |
| Review | independent Claude review artifact and unresolved findings |
| Transaction | approved action summary, signatures, simulation, confirmed result, post-state checks |
| Rollback | previous artifact/hash, authority, procedure, trigger, compatibility, proof status |

Hash template:

```bash
sha256sum <program-artifact> <idl-or-interface-artifact>
```

Read-only inspection templates may include current CLI account/program display commands only after live help confirms syntax and the cluster/program placeholders are resolved from approved state.

## Deployment And Upgrade Authorization

Before any transaction or deploy/upgrade action, obtain explicit Boss approval for the exact:

- cluster and RPC endpoint identity;
- program ID and program-data account;
- artifact and IDL hashes;
- payer and upgrade authority public identities, never secret material;
- transaction instructions, expected fees/rent, asset movement, and governance proposal;
- simulation output and differences between simulation and submission;
- rollback plan and conditions;
- independent-review status and accepted residual risks.

Devnet is still a real network write and requires approval. Mainnet requires a separate explicit statement; do not infer it from configuration. Authority transfer, making a program immutable, closing buffers/accounts, or destructive migrations require explicit irreversible-action confirmation.

Do not provide or run a deploy command with a real address/key until this gate is satisfied. Keep examples placeholder-only.

## Rollback Proof

A rollback plan must state:

- previous verified artifact and hash;
- compatibility of old code with any new state layout or migration;
- authority/governance path able to perform rollback;
- exact trigger and decision owner;
- expected downtime, account/state consequences, and user communication needs;
- safe template commands verified against live tool help;
- rehearsal status on a compatible local environment;
- post-rollback IDL/artifact/program-data/state checks.

If state migration is not backward compatible, redeploying old bytes is not a rollback. Require a forward-fix or migration-specific recovery plan.

## Final Release Checklist

- [ ] Live tool/framework versions and exact command syntax were observed.
- [ ] Focused Rust tests, integration tests, adversarial negatives, and fixed-finding regressions pass.
- [ ] Higher-fidelity runtime behavior was tested where in-process harnesses are insufficient.
- [ ] Fuzz/property coverage and bounded duration/corpus are reported truthfully.
- [ ] Compute, account-size, remaining-account, CPI, and lock-contention bounds are evidenced.
- [ ] Source revision, Cargo.lock, toolchain/container, artifact hash, and IDL hash are recorded.
- [ ] Verifiable/reproducible build and on-chain byte comparison pass with exact target identity.
- [ ] Cluster, program ID, loader, program-data account, and upgrade authority are verified.
- [ ] Independent Claude review is complete; unresolved findings and accepted risks are explicit.
- [ ] Boss approved exact key identities, transaction, cluster, deploy/upgrade, and authority action.
- [ ] Rollback artifact, authority, compatibility, trigger, and proof status are recorded.
- [ ] Post-action transaction confirmation and program/state smoke checks pass in the same run.
- [ ] Every unrun check and residual risk is reported. No release claim exceeds the evidence.
